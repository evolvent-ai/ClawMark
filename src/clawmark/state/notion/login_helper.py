"""Notion login helper — authenticate and save browser session state.

Generates ``notion_state.json`` which is required by
:class:`NotionPlaywrightSession` to perform UI automation (duplicate + move)
without re-authenticating every time.

Usage::

    # Interactive (opens browser window, you log in manually):
    uv run python -m clawmark.state.notion.login_helper

    # Headless (prompts for email + verification code in terminal):
    uv run python -m clawmark.state.notion.login_helper --headless

    # Choose browser engine:
    uv run python -m clawmark.state.notion.login_helper --browser chromium

Adapted from MCPMark's NotionLoginHelper.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from playwright.sync_api import (
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

logger = logging.getLogger(__name__)


class NotionLoginHelper:
    """Launch a browser, log into Notion, and save the session state."""

    def __init__(
        self,
        *,
        headless: bool = False,
        browser: str = "chromium",
        state_path: str | Path = "notion_state.json",
    ):
        self._headless = headless
        self._browser_name = browser
        self._state_path = Path(state_path).expanduser().resolve()
        self._pw = None
        self._browser = None
        self._context: BrowserContext | None = None

    def login(self) -> None:
        """Run the login flow and save state to disk."""
        # Remove stale state
        if self._state_path.exists():
            self._state_path.unlink()

        self._pw = sync_playwright().start()
        browser_type = getattr(self._pw, self._browser_name)
        self._browser = browser_type.launch(headless=self._headless)
        self._context = self._browser.new_context()
        page = self._context.new_page()

        login_url = "https://www.notion.so/login"
        page.goto(login_url, wait_until="load")

        if self._headless:
            self._headless_login(page, login_url)
        else:
            print("\n" + "=" * 60)
            print("A browser window has been opened.")
            print("Please log into Notion in that window.")
            print("Once you see your workspace, come back here and press ENTER.")
            print("=" * 60 + "\n")
            input()
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5_000)
            except PlaywrightTimeoutError:
                pass

        self._context.storage_state(path=str(self._state_path))
        print(f"\nLogin state saved to {self._state_path}")

    def _headless_login(self, page: Page, login_url: str) -> None:
        email = input("Enter your Notion email: ").strip()
        try:
            inp = page.locator('input[placeholder="Enter your email address..."]')
            inp.wait_for(state="visible", timeout=120_000)
            inp.fill(email)
            inp.press("Enter")
        except PlaywrightTimeoutError:
            raise RuntimeError("Timed out waiting for email input field.")

        try:
            code_inp = page.locator('input[placeholder="Enter code"]')
            code_inp.wait_for(state="visible", timeout=120_000)
            code = input("Enter the verification code from your email: ").strip()
            code_inp.fill(code)
            code_inp.press("Enter")
        except PlaywrightTimeoutError:
            raise RuntimeError("Timed out waiting for verification code input.")

        try:
            page.wait_for_url(lambda url: url != login_url, timeout=180_000)
        except PlaywrightTimeoutError:
            logger.warning("Login redirect timed out, saving state anyway.")

    def close(self) -> None:
        if self._context:
            try:
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

    def __enter__(self) -> "NotionLoginHelper":
        self.login()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Log into Notion and save browser session state.",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Headless mode (prompts for email + code in terminal).",
    )
    parser.add_argument(
        "--browser", default="chromium", choices=["chromium", "firefox"],
        help="Browser engine (default: chromium).",
    )
    parser.add_argument(
        "--state-path", default="notion_state.json",
        help="Output path for session state file.",
    )
    args = parser.parse_args()

    with NotionLoginHelper(
        headless=args.headless,
        browser=args.browser,
        state_path=args.state_path,
    ):
        print("Done.")


if __name__ == "__main__":
    main()
