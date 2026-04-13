"""Calendar state manager — CalDAV lifecycle via Radicale.

Configuration (env_config.calendar):
- seed_file: optional path (relative to task dir) to initial seed JSON

Global (environment variables):
- CALDAV_URL: base URL of the Radicale server (default: http://localhost:5232)
- CALDAV_USERNAME: CalDAV username (default: benchmark)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any

from ..base import BaseStateManager
from .client import CalendarClient
from ...sandbox.base import BaseSandbox

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://radicale:5232"


@BaseStateManager.register("calendar")
class CalendarStateManager(BaseStateManager):
    """Manages calendar state for a single benchmark task via Radicale CalDAV."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._client: CalendarClient | None = None

    # ── lifecycle ────────────────────────────────────────────────────

    async def setup(self, *, sandbox: BaseSandbox) -> None:
        self._sandbox = sandbox
        # Use dynamic port from sandbox if available
        port_overrides = getattr(sandbox, "ports", {})
        if 5232 in port_overrides:
            url = f"http://localhost:{port_overrides[5232]}"
        else:
            url = os.environ.get("CALDAV_URL", _DEFAULT_URL)
        username = os.environ.get("CALDAV_USERNAME", "benchmark")
        # Retry with backoff — Radicale may need a few seconds after container starts
        last_err = None
        for attempt in range(5):
            try:
                self._client = await asyncio.to_thread(CalendarClient, url, username)
                await asyncio.to_thread(self._client.reset)
                return
            except Exception as e:
                last_err = e
                wait = 2 * (attempt + 1)
                logger.warning("Calendar setup attempt %d failed (%s), retrying in %ds…", attempt + 1, e, wait)
                await asyncio.sleep(wait)
        raise RuntimeError(f"Calendar setup failed after 5 attempts: {last_err}")

    async def cleanup(self) -> None:
        if self._client:
            try:
                await asyncio.to_thread(self._client.reset)
            except Exception as e:
                logger.warning("Calendar cleanup reset failed: %s", e)
            try:
                await asyncio.to_thread(self._client.close)
            except Exception as e:
                logger.warning("Calendar client close failed: %s", e)
            self._client = None

    # ── public methods ───────────────────────────────────────────────

    def _require_client(self) -> CalendarClient:
        if self._client is None:
            raise ValueError("CalendarStateManager not set up — call setup() first")
        return self._client

    async def create_calendar(self, name: str) -> str:
        """Create a calendar. Returns its URL."""
        return await asyncio.to_thread(self._require_client().create_calendar, name)

    async def list_calendars(self) -> list[dict[str, str]]:
        """List all calendars."""
        return await asyncio.to_thread(self._require_client().list_calendars)

    async def add_event(
        self,
        calendar_name: str,
        summary: str,
        dtstart: datetime,
        dtend: datetime,
        *,
        description: str = "",
        location: str = "",
        uid: str | None = None,
    ) -> str:
        """Add an event. Returns the event UID."""
        return await asyncio.to_thread(
            self._require_client().add_event,
            calendar_name, summary, dtstart, dtend,
            description=description, location=location, uid=uid,
        )

    async def get_events(
        self,
        calendar_name: str,
        start: date | datetime | None = None,
        end: date | datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get events, optionally filtered by date range."""
        return await asyncio.to_thread(
            self._require_client().get_events, calendar_name, start, end,
        )

    async def find_events(
        self, calendar_name: str, summary_contains: str,
    ) -> list[dict[str, Any]]:
        """Search events by summary substring."""
        return await asyncio.to_thread(
            self._require_client().find_events, calendar_name, summary_contains,
        )

    async def delete_event(self, calendar_name: str, uid: str) -> None:
        """Delete an event by UID."""
        await asyncio.to_thread(
            self._require_client().delete_event, calendar_name, uid,
        )

    async def delete_calendar(self, name: str) -> None:
        """Delete a calendar by name."""
        await asyncio.to_thread(self._require_client().delete_calendar, name)

    async def seed_data(self, seed_path: Path) -> dict[str, int]:
        """Load a JSON seed file into the CalDAV server."""
        client = self._require_client()
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_path}")
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        return await asyncio.to_thread(client.seed, data)
