"""Notion state manager — duplicate-from-template lifecycle.

Configuration (environment variables):
- NOTION_ADMIN_KEY, NOTION_AGENT_KEY, NOTION_SOURCE_PAGE, NOTION_EVAL_PAGE
- NOTION_STATE_FILE (optional, default notion_state.json)
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from ..base import BaseStateManager
from .api import NotionClient
from .playwright import NotionPlaywrightSession
from ...sandbox.base import BaseSandbox

logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Environment variable {name} is required for NotionStateManager.")
    return value


@BaseStateManager.register("notion")
class NotionStateManager(BaseStateManager):
    """Manages Notion page lifecycle for benchmark tasks."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._created_pages: list[str] = []
        self._duplicated_page_id: str | None = None
        self._admin_client: NotionClient | None = None
        self._agent_client: NotionClient | None = None
        self._source_parent_id: str | None = None
        self._eval_parent_id: str | None = None

    # ── lifecycle ───────────────────────────────────────────────────

    async def setup(self, *, sandbox: BaseSandbox) -> None:
        self._sandbox = sandbox
        await self._init_clients()

    async def cleanup(self) -> None:
        if self._agent_client:
            for page_id in self._created_pages:
                try:
                    await self._agent_client.patch(
                        f"pages/{page_id}", {"archived": True},
                    )
                    logger.info("Archived eval page %s", page_id)
                except Exception as e:
                    logger.warning("Cleanup failed for %s: %s", page_id, e)
        self._created_pages.clear()
        self._duplicated_page_id = None

    # ── public methods ──────────────────────────────────────────────

    async def copy_page(self, template: str) -> dict[str, str]:
        """Duplicate a template page into the eval hub via Playwright.

        Returns {"page_id": str, "page_url": str}.
        """
        assert self._admin_client and self._agent_client
        assert self._source_parent_id and self._eval_parent_id

        # Clean up old copies in eval hub
        await self._cleanup_eval_hub()

        # Find template page URL
        template_id = await self._admin_client.find_child_page_by_title(
            self._source_parent_id, template,
        )
        if not template_id:
            raise RuntimeError(f"Template '{template}' not found under source hub.")

        page_obj = await self._admin_client.get_page(template_id)
        template_url = page_obj.get("url", "")
        if not template_url:
            template_url = f"https://www.notion.so/{template_id.replace('-', '')}"

        # Duplicate + Move via Playwright
        eval_page_title = _require_env("NOTION_EVAL_PAGE")
        state_file = os.environ.get("NOTION_STATE_FILE", "notion_state.json")
        headless = os.environ.get("NOTION_PLAYWRIGHT_HEADLESS", "true").lower() == "true"

        def _pw_duplicate() -> str:
            with NotionPlaywrightSession(state_file=state_file, headless=headless) as pw:
                return pw.duplicate_and_move(
                    source_page_url=template_url,
                    target_parent_title=eval_page_title,
                )

        logger.info("Duplicating '%s' via Playwright...", template)
        new_page_id = await asyncio.to_thread(_pw_duplicate)

        # Wait for page to be accessible via API
        await self._wait_for_page(new_page_id)

        # Rename (strip "(1)" suffix)
        await self._agent_client.rename_page(new_page_id, template)

        # Clean up orphan duplicates in source hub
        await self._cleanup_source_orphans(template, exclude={template_id})

        self._duplicated_page_id = new_page_id
        self._created_pages.append(new_page_id)
        page_url = f"https://www.notion.so/{new_page_id.replace('-', '')}"
        logger.info("Copied page: %s → %s", template, page_url)

        return {"page_id": new_page_id, "page_url": page_url}

    async def add_database_row(self, db_title: str, properties: dict) -> str:
        """Add a row to a database within the current page."""
        if not self._duplicated_page_id or not self._agent_client:
            raise RuntimeError("No active page — call copy_page() first")
        db_id = await self._agent_client.find_database_in_page(
            self._duplicated_page_id, db_title,
        )
        if not db_id:
            raise RuntimeError(f"Database '{db_title}' not found in page")
        return await self._agent_client.create_database_row(db_id, properties)

    async def append_blocks(self, blocks: list[dict]) -> None:
        """Append blocks to the current page."""
        if not self._duplicated_page_id or not self._agent_client:
            raise RuntimeError("No active page — call copy_page() first")
        await self._agent_client.update_page_content(self._duplicated_page_id, blocks)

    async def update_property(self, properties: dict) -> None:
        """Update properties on the current page."""
        if not self._duplicated_page_id or not self._agent_client:
            raise RuntimeError("No active page — call copy_page() first")
        await self._agent_client.patch(
            f"pages/{self._duplicated_page_id}", {"properties": properties},
        )

    async def read_page(self) -> str:
        """Read the current page content as text."""
        if not self._duplicated_page_id or not self._agent_client:
            return ""
        return await self._agent_client.get_page_content_as_text(self._duplicated_page_id)

    async def query_db(self, db_title: str) -> list[dict]:
        """Query all rows from a database within the current page."""
        if not self._duplicated_page_id or not self._agent_client:
            return []
        db_id = await self._agent_client.find_database_in_page(
            self._duplicated_page_id, db_title,
        )
        if not db_id:
            return []
        return await self._agent_client.query_database(db_id)

    async def create_page(self, title: str) -> dict[str, str]:
        """Create a new page under eval hub (no template/Playwright needed).

        Returns {"page_id": str, "page_url": str}.
        """
        if not self._agent_client or not self._eval_parent_id:
            raise RuntimeError("No active client — call setup() first")
        result = await self._agent_client.post("pages", {
            "parent": {"page_id": self._eval_parent_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
        })
        self._duplicated_page_id = result["id"]
        self._created_pages.append(result["id"])
        page_url = result.get("url", f"https://www.notion.so/{result['id'].replace('-', '')}")
        logger.info("Created page: %s → %s", title, page_url)
        return {"page_id": result["id"], "page_url": page_url}

    async def create_database(self, title: str, properties_schema: dict) -> str:
        """Create an inline database in the current page. Returns database ID."""
        if not self._duplicated_page_id or not self._agent_client:
            raise RuntimeError("No active page — call create_page() or copy_page() first")
        result = await self._agent_client.post("databases", {
            "parent": {"type": "page_id", "page_id": self._duplicated_page_id},
            "title": [{"text": {"content": title}}],
            "properties": properties_schema,
        })
        logger.info("Created database: %s (id=%s)", title, result["id"])
        return result["id"]

    async def update_db_row(self, page_id: str, properties: dict) -> None:
        """Update properties on a specific database row (page)."""
        if not self._agent_client:
            raise RuntimeError("No active client — call setup() first")
        await self._agent_client.patch(f"pages/{page_id}", {"properties": properties})

    # ── private helpers (unchanged from PR branch) ──────────────────

    async def _init_clients(self) -> None:
        """Initialize REST API clients and resolve hub page names to IDs."""
        admin_key = _require_env("NOTION_ADMIN_KEY")
        agent_key = _require_env("NOTION_AGENT_KEY")
        source_name = _require_env("NOTION_SOURCE_PAGE")
        eval_name = _require_env("NOTION_EVAL_PAGE")

        self._admin_client = NotionClient(admin_key)
        self._agent_client = NotionClient(agent_key)

        self._source_parent_id = await self._admin_client.find_page_by_title(source_name)
        if not self._source_parent_id:
            raise RuntimeError(f"Source page '{source_name}' not found.")

        self._eval_parent_id = await self._admin_client.find_page_by_title(eval_name)
        if not self._eval_parent_id:
            raise RuntimeError(f"Eval page '{eval_name}' not found.")

        logger.info("Resolved: source=%s, eval=%s", self._source_parent_id, self._eval_parent_id)

    async def _cleanup_eval_hub(self) -> None:
        """Archive child pages in eval hub, preserving pages we created this session."""
        assert self._agent_client and self._eval_parent_id
        keep = set(self._created_pages)
        children = await self._agent_client.get_child_pages(self._eval_parent_id)
        for child in children:
            if child["type"] == "child_page" and child["id"] not in keep:
                try:
                    await self._agent_client.patch(
                        f"pages/{child['id']}", {"archived": True},
                    )
                    logger.info("Archived old eval page: %s (%s)", child["title"], child["id"])
                except Exception as e:
                    logger.warning("Failed to archive %s: %s", child["id"], e)

    async def _cleanup_source_orphans(
        self, template_name: str, exclude: set[str],
    ) -> None:
        """Archive 'Title (n)' orphan pages left by Notion's Duplicate in source hub."""
        assert self._admin_client and self._source_parent_id
        import re
        pattern = re.compile(rf"^{re.escape(template_name)}\s*\(\d+\)$")
        children = await self._admin_client.get_child_pages(self._source_parent_id)
        for child in children:
            if child["type"] != "child_page" or child["id"] in exclude:
                continue
            if pattern.match(child["title"]):
                try:
                    await self._admin_client.patch(
                        f"pages/{child['id']}", {"archived": True},
                    )
                    logger.info("Archived source orphan: %s", child["title"])
                except Exception as e:
                    logger.warning("Failed to archive orphan %s: %s", child["id"], e)

    async def _wait_for_page(self, page_id: str, timeout: int = 60) -> None:
        """Poll until a page is accessible via the agent key."""
        assert self._agent_client
        for _ in range(timeout // 2):
            try:
                await self._agent_client.get_page(page_id)
                return
            except Exception:
                await asyncio.sleep(2)
        raise RuntimeError(f"Page {page_id} not accessible after {timeout}s")
