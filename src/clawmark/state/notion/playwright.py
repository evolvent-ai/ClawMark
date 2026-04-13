"""Playwright-based Notion page duplication and move.

The Notion REST API does not support duplicating pages or changing a
page's parent.  This module uses browser automation to perform these
operations through the Notion UI, which triggers Notion's internal
deep-copy logic (including inline databases, views, relations, etc.).

Adapted from MCPMark's NotionStateManager.

Prerequisites
~~~~~~~~~~~~~
1. ``playwright`` must be installed: ``pip install playwright && playwright install chromium``
2. A browser login state file (``notion_state.json``) must exist.
   Generate it by running the login helper once::

       uv run python -m clawmark.state.notion.login_helper
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

logger = logging.getLogger(__name__)

# UI selectors
_MORE_BUTTON = '[data-testid="more-button"], div.notion-topbar-more-button, [aria-label="More"], button[aria-label="More"]'
_DUPLICATE_ITEM = 'text="Duplicate"'
_MOVE_TO_ITEM = 'text="Move to"'
_MOVE_TO_INPUT = 'input[placeholder*="Move page to"], textarea[placeholder*="Move page to"]'

# Matches "Title (1)", "Title (2)", etc.
_ORPHAN_RE = re.compile(r".+\s+\(\d+\)$")


def _extract_page_id_from_url(url: str) -> str:
    slug = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
    compact = "".join(c for c in slug if c.isalnum())
    if len(compact) < 32:
        raise ValueError(f"Cannot parse page ID from URL: {url}")
    compact = compact[-32:]
    return f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"


def _slug_base(url: str) -> str:
    """Return the URL slug without its trailing 32-char hex ID."""
    slug = url.split("?", 1)[0].split("#", 1)[0].rstrip("/").split("/")[-1]
    m = re.match(r"^(.*)-([0-9a-fA-F]{32})$", slug)
    return m.group(1) if m else slug


def _is_valid_duplicate_url(original_url: str, dup_url: str) -> bool:
    """Check that *dup_url* looks like a Notion duplicate of *original_url*."""
    orig = _slug_base(original_url)
    dup = _slug_base(dup_url)
    if not dup.startswith(orig + "-"):
        return False
    return dup[len(orig) + 1:].isdigit()


class NotionPlaywrightSession:
    """Manages a Playwright browser session for Notion UI automation.

    Usage::

        with NotionPlaywrightSession(state_file="notion_state.json") as session:
            new_page_id = session.duplicate_and_move(
                source_page_url="https://www.notion.so/...",
                target_parent_title="ClawMark Eval Hub",
            )
    """

    def __init__(
        self,
        state_file: str | Path = "notion_state.json",
        headless: bool = True,
        browser: str = "chromium",
    ):
        self._state_file = Path(state_file)
        if not self._state_file.exists():
            raise FileNotFoundError(
                f"Notion login state '{self._state_file}' not found. "
                f"Run: uv run python -m clawmark.state.notion.login_helper"
            )
        self._headless = headless
        self._browser_name = browser
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def __enter__(self) -> "NotionPlaywrightSession":
        self._pw = sync_playwright().start()
        browser_type = getattr(self._pw, self._browser_name)
        self._browser = browser_type.launch(headless=self._headless)
        self._context = self._browser.new_context(
            storage_state=str(self._state_file),
            locale="en-US",
        )
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._context:
            try:
                self._context.storage_state(path=str(self._state_file))
                self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._pw:
            try:
                self._pw.stop()
            except Exception:
                pass

    def duplicate_and_move(
        self,
        source_page_url: str,
        target_parent_title: str,
        *,
        timeout_ms: int = 180_000,
    ) -> str:
        """Duplicate a page via UI and move it to the target parent.

        Args:
            source_page_url: Full Notion URL of the template page.
            target_parent_title: Title of the destination parent page.
            timeout_ms: Max wait for Notion UI operations.

        Returns:
            The page ID of the newly duplicated (and moved) page.
        """
        assert self._context is not None
        page = self._context.new_page()
        try:
            return self._do_duplicate_and_move(
                page, source_page_url, target_parent_title, timeout_ms,
            )
        finally:
            try:
                self._context.storage_state(path=str(self._state_file))
            except Exception:
                pass
            page.close()

    def _do_duplicate_and_move(
        self,
        page: Page,
        source_page_url: str,
        target_parent_title: str,
        timeout_ms: int,
    ) -> str:
        # Navigate to source page
        logger.info("Navigating to template: %s", source_page_url)
        page.goto(source_page_url, wait_until="domcontentloaded", timeout=120_000)
        time.sleep(3)

        # ── Step 1: Duplicate ──
        logger.info("Clicking Duplicate...")
        page.wait_for_selector(_MORE_BUTTON, state="visible", timeout=30_000)
        page.click(_MORE_BUTTON)
        page.hover(_DUPLICATE_ITEM)
        page.click(_DUPLICATE_ITEM)

        original_url = page.url
        logger.info("Waiting for duplicate to load (up to %ds)...", timeout_ms // 1000)
        try:
            page.wait_for_url(lambda url: url != original_url, timeout=timeout_ms)
        except PlaywrightTimeoutError:
            raise RuntimeError("Timeout waiting for page duplication")

        time.sleep(5)  # Let Notion settle
        duplicated_url = page.url

        # Validate URL pattern
        if not _is_valid_duplicate_url(original_url, duplicated_url):
            logger.warning(
                "Duplicate URL mismatch: expected pattern of %s, got %s",
                original_url, duplicated_url,
            )
            # Still proceed — the URL might just be formatted differently

        duplicated_page_id = _extract_page_id_from_url(duplicated_url)
        logger.info("Duplicated → %s (%s)", duplicated_page_id, duplicated_url)

        # ── Step 2: Move to eval parent ──
        logger.info("Moving to '%s'...", target_parent_title)
        page.wait_for_selector(_MORE_BUTTON, state="visible", timeout=30_000)
        page.click(_MORE_BUTTON)
        page.hover(_MOVE_TO_ITEM)
        page.click(_MOVE_TO_ITEM)

        page.wait_for_selector(_MOVE_TO_INPUT, state="visible", timeout=15_000)
        search = page.locator(_MOVE_TO_INPUT).first
        search.click()
        search.fill("")
        search.type(target_parent_title, delay=50)

        result_sel = f'div[role="menuitem"]:has-text("{target_parent_title}")'
        page.wait_for_selector(result_sel, state="visible", timeout=60_000)
        page.locator(result_sel).first.click(force=True)

        # Wait for move dialog to disappear
        page.wait_for_selector(_MOVE_TO_INPUT, state="detached", timeout=60_000)
        time.sleep(3)

        logger.info("Duplicate + Move complete: %s", duplicated_page_id)
        return duplicated_page_id
