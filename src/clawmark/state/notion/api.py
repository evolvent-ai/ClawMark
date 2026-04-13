"""Async Notion REST API client.

Provides :class:`NotionClient` for reads, writes, queries, deletions,
and rename — everything that the public REST API supports.

Page duplication and move are **not** supported by the REST API and are
handled separately by Playwright in ``playwright.py``.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

_MAX_RETRIES = 5
_BACKOFF_BASE = 2  # seconds


# ── helpers ─────────────────────────────────────────────────────────


def extract_page_id_from_url(url: str) -> str:
    """Extract a UUID-formatted page ID from a Notion URL.

    Handles URLs like:
    - ``https://www.notion.so/Page-Name-27ad10a48436805b9179fdaff2f65be2``
    - ``https://amazing-wave-b38.notion.site/Page-27ad10a...``
    """
    slug = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
    compact = "".join(c for c in slug if c.isalnum())
    if len(compact) < 32:
        raise ValueError(f"Cannot parse page ID from URL: {url}")
    compact = compact[-32:]
    return f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"


def _extract_title(rich_text_list: list[dict]) -> str:
    return "".join(
        rt.get("plain_text", "") or rt.get("text", {}).get("content", "")
        for rt in rich_text_list
    )


# ── client ──────────────────────────────────────────────────────────


class NotionClient:
    """Thin async wrapper around the Notion REST API with retry logic."""

    def __init__(self, token: str, *, timeout: float = 60):
        self._token = token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, endpoint: str, json: dict | None = None,
    ) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}/{endpoint}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(_MAX_RETRIES):
                resp = await client.request(
                    method, url, headers=self._headers(), json=json,
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "Notion API %s %s → %d, retry %d/%d in %ds",
                        method, endpoint, resp.status_code,
                        attempt + 1, _MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code >= 400:
                    body = resp.text[:500]
                    raise httpx.HTTPStatusError(
                        f"Notion API error {resp.status_code}: {body}",
                        request=resp.request,
                        response=resp,
                    )
                return resp.json()
        raise RuntimeError(
            f"Notion API failed after {_MAX_RETRIES} retries: {method} {endpoint}"
        )

    async def get(self, endpoint: str) -> dict[str, Any]:
        return await self._request("GET", endpoint)

    async def post(self, endpoint: str, body: dict | None = None) -> dict[str, Any]:
        return await self._request("POST", endpoint, json=body or {})

    async def patch(self, endpoint: str, body: dict | None = None) -> dict[str, Any]:
        return await self._request("PATCH", endpoint, json=body or {})

    async def delete(self, endpoint: str) -> dict[str, Any]:
        return await self._request("DELETE", endpoint)

    # ── page operations ─────────────────────────────────────────────

    async def get_child_pages(self, parent_id: str) -> list[dict[str, Any]]:
        """List child pages/databases under *parent_id*."""
        results: list[dict] = []
        start_cursor: str | None = None
        while True:
            url = f"blocks/{parent_id}/children?page_size=100"
            if start_cursor:
                url += f"&start_cursor={start_cursor}"
            data = await self.get(url)
            for block in data.get("results", []):
                if block.get("type") == "child_page":
                    title = block.get("child_page", {}).get("title", "")
                    results.append({"id": block["id"], "title": title, "type": "child_page"})
                elif block.get("type") == "child_database":
                    title = block.get("child_database", {}).get("title", "")
                    results.append({"id": block["id"], "title": title, "type": "child_database"})
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")
        return results

    async def find_child_page_by_title(
        self, parent_id: str, title: str,
    ) -> str | None:
        """Find a child page by exact title. Returns page ID or None."""
        children = await self.get_child_pages(parent_id)
        for child in children:
            if child["type"] == "child_page" and child["title"] == title:
                return child["id"]
        return None

    async def get_page(self, page_id: str) -> dict[str, Any]:
        return await self.get(f"pages/{page_id}")

    async def find_page_by_title(self, title: str) -> str | None:
        """Search the workspace for a top-level page by exact title.

        Returns the page ID or None.  If multiple pages match, returns
        the most recently edited one.
        """
        data = await self.post("search", {
            "query": title,
            "filter": {"property": "object", "value": "page"},
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        })
        for page in data.get("results", []):
            props = page.get("properties", {})
            for prop_val in props.values():
                if prop_val.get("type") == "title":
                    page_title = _extract_title(prop_val.get("title", []))
                    if page_title == title:
                        return page["id"]
        return None

    async def delete_page(self, page_id: str) -> bool:
        """Permanently delete a page (block)."""
        try:
            await self.delete(f"blocks/{page_id}")
            logger.info("Deleted Notion page %s", page_id)
            return True
        except Exception as e:
            logger.warning("Failed to delete page %s: %s", page_id, e)
            return False

    async def rename_page(self, page_id: str, new_title: str) -> bool:
        """Rename a page via the Pages API."""
        try:
            await self.patch(f"pages/{page_id}", {
                "properties": {
                    "title": {"title": [{"text": {"content": new_title}}]},
                },
            })
            logger.info("Renamed page %s → %s", page_id, new_title)
            return True
        except Exception as e:
            logger.warning("Failed to rename page %s: %s", page_id, e)
            return False

    # ── content reading ─────────────────────────────────────────────

    async def get_page_blocks(self, page_id: str) -> list[dict[str, Any]]:
        """Get all blocks under a page (paginated)."""
        blocks: list[dict] = []
        start_cursor: str | None = None
        while True:
            url = f"blocks/{page_id}/children?page_size=100"
            if start_cursor:
                url += f"&start_cursor={start_cursor}"
            data = await self.get(url)
            blocks.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")
        return blocks

    async def get_page_content_as_text(self, page_id: str) -> str:
        """Extract page content as markdown-ish plain text."""
        blocks = await self.get_page_blocks(page_id)
        parts: list[str] = []
        for block in blocks:
            btype = block.get("type", "")
            if btype in (
                "paragraph", "heading_1", "heading_2", "heading_3",
                "bulleted_list_item", "numbered_list_item",
            ):
                rich_text = block.get(btype, {}).get("rich_text", [])
                text = _extract_title(rich_text)
                if not text.strip():
                    continue
                prefix = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### "}.get(btype, "")
                parts.append(f"{prefix}{text}")
        return "\n\n".join(parts)

    # ── database operations ─────────────────────────────────────────

    async def find_database_in_page(
        self, page_id: str, db_title: str,
    ) -> str | None:
        """Find an inline/child database by title within a page."""
        children = await self.get_child_pages(page_id)
        for child in children:
            if child["type"] == "child_database" and db_title.lower() in child["title"].lower():
                return child["id"]
        return None

    async def query_database(
        self, database_id: str, filter: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Query all rows from a database."""
        body: dict[str, Any] = {}
        if filter:
            body["filter"] = filter
        results: list[dict] = []
        start_cursor: str | None = None
        while True:
            if start_cursor:
                body["start_cursor"] = start_cursor
            data = await self.post(f"databases/{database_id}/query", body)
            results.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")
        return results

    async def create_database_row(
        self, database_id: str, properties: dict[str, Any],
    ) -> str:
        """Create a new row in a database. Returns the new page ID."""
        result = await self.post("pages", {
            "parent": {"type": "database_id", "database_id": database_id},
            "properties": properties,
        })
        return result["id"]

    async def update_page_content(
        self, page_id: str, children: list[dict[str, Any]],
    ) -> bool:
        """Append block children to a page."""
        try:
            await self.patch(f"blocks/{page_id}/children", {"children": children})
            return True
        except Exception as e:
            logger.warning("Failed to update page content %s: %s", page_id, e)
            return False
