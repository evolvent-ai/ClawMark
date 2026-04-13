"""Google Sheets state manager — spreadsheet lifecycle via real Google API.

Configuration (env_config.google_sheets):
- task_id:           logical task name (used in folder naming)
- credentials_path:  path to OAuth credentials JSON (optional override)

Global (environment variables):
- GOOGLE_CREDENTIALS_PATH: default path to OAuth credentials JSON
"""
from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4
from typing import Any

from ..base import BaseStateManager
from .api import GoogleSheetsClient
from ...sandbox.base import BaseSandbox

logger = logging.getLogger(__name__)

_DEFAULT_CREDS = "configs/google_credentials.json"


@BaseStateManager.register("google_sheets")
class GoogleSheetsStateManager(BaseStateManager):
    """Manages Google Sheets state for a single benchmark task."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client: GoogleSheetsClient | None = None
        self._folder_id: str | None = None
        self._folder_name: str | None = None
        self._creds_path: str | None = None
        self._copied_sheets: dict[str, str] = {}  # template_url → spreadsheet_id

    # ── lifecycle ────────────────────────────────────────────────────

    async def setup(self, *, sandbox: BaseSandbox) -> None:
        self._sandbox = sandbox

        # Resolve credentials path
        self._creds_path = (
            self.config.get("credentials_path")
            or os.environ.get("GOOGLE_CREDENTIALS_PATH")
            or _DEFAULT_CREDS
        )

        # Init client (sync I/O: file read + token refresh)
        self._client = await asyncio.to_thread(GoogleSheetsClient, self._creds_path)

        # Create isolation folder
        task_id = self.config.get("task_id", "unknown")
        self._folder_name = f"clawmark-{task_id}-{uuid4().hex[:8]}"
        self._folder_id = await asyncio.to_thread(
            self._client.create_folder, self._folder_name,
        )
        logger.info("Google Sheets setup: folder=%s (%s)", self._folder_name, self._folder_id)

        # Upload credentials to sandbox at a deterministic path
        result = await sandbox.exec("mkdir -p /root/.google")
        if hasattr(result, "return_code") and result.return_code != 0:
            raise RuntimeError(f"Failed to create /root/.google: {result.stderr}")
        await sandbox.upload_file(self._creds_path, "/root/.google/credentials.json")

    async def cleanup(self) -> None:
        if self._client and self._folder_id:
            try:
                await asyncio.to_thread(self._client.delete_folder, self._folder_id)
                logger.info("Deleted Drive folder %s", self._folder_name)
            except Exception as e:
                logger.warning("Cleanup failed for folder %s: %s", self._folder_name, e)
        self._folder_id = None
        self._folder_name = None
        self._copied_sheets.clear()
        self._client = None

    # ── stage helpers ────────────────────────────────────────────────

    async def create_spreadsheet(self, title: str) -> dict[str, str]:
        """Create a blank spreadsheet in the isolation folder.

        Returns ``{"sheet_id": str, "sheet_url": str}``.
        """
        self._require_ready()
        sheet_id = await asyncio.to_thread(
            self._client.create_spreadsheet, title, self._folder_id,
        )
        self._copied_sheets[title] = sheet_id
        return {
            "sheet_id": sheet_id,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
        }

    async def copy_template(self, template_url: str) -> dict[str, str]:
        """Copy a template sheet into the isolation folder.

        Returns ``{"sheet_id": str, "sheet_url": str}``.
        """
        self._require_ready()
        sheet_id = await asyncio.to_thread(
            self._client.copy_sheet_to_folder, template_url, self._folder_id,
        )
        self._copied_sheets[template_url] = sheet_id
        return {
            "sheet_id": sheet_id,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
        }

    async def read_values(self, sheet_id: str, range_: str) -> list[list[str]]:
        self._require_ready()
        return await asyncio.to_thread(self._client.read_values, sheet_id, range_)

    async def update_values(
        self, sheet_id: str, range_: str, values: list[list],
    ) -> None:
        self._require_ready()
        await asyncio.to_thread(self._client.update_values, sheet_id, range_, values)

    async def append_rows(
        self, sheet_id: str, range_: str, rows: list[list],
    ) -> None:
        self._require_ready()
        await asyncio.to_thread(self._client.append_rows, sheet_id, range_, rows)

    async def get_spreadsheet_id(self, name: str) -> str | None:
        """Find a spreadsheet by name within the current isolation folder."""
        self._require_ready()
        return await asyncio.to_thread(
            self._client.find_spreadsheet, self._folder_id, name,
        )

    # ── checker helpers ──────────────────────────────────────────────

    async def find_row(
        self, sheet_id: str, sheet_name: str, col_index: int, value: str,
    ) -> dict | None:
        self._require_ready()
        return await asyncio.to_thread(
            self._client.find_row, sheet_id, sheet_name, col_index, value,
        )

    # ── private ──────────────────────────────────────────────────────

    def _require_ready(self) -> None:
        if not self._client or not self._folder_id:
            raise RuntimeError("GoogleSheetsStateManager.setup() has not completed")

