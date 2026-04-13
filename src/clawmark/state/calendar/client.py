"""Synchronous CalDAV client for Radicale server.

All methods are plain synchronous — the async boundary lives in
``CalendarStateManager`` which wraps calls with ``asyncio.to_thread``.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, date
from typing import Any

import caldav

logger = logging.getLogger(__name__)


class CalendarClient:
    """CalDAV client for a single user on a Radicale server."""

    def __init__(self, url: str, username: str = "benchmark") -> None:
        self._url = url
        self._username = username
        self._client = caldav.DAVClient(url=url, username=username, password="")
        self._principal = self._client.principal()

    # ── calendar operations ───────────────────────────────────────────

    def create_calendar(self, name: str) -> str:
        """Create a calendar and return its URL path."""
        cal = self._principal.make_calendar(name=name)
        logger.info("Created calendar: %s at %s", name, cal.url)
        return str(cal.url)

    def list_calendars(self) -> list[dict[str, str]]:
        """List all calendars for this user."""
        calendars = self._principal.calendars()
        return [{"name": c.name, "url": str(c.url)} for c in calendars]

    def get_calendar(self, name: str) -> caldav.Calendar:
        """Find a calendar by name."""
        for cal in self._principal.calendars():
            if cal.name == name:
                return cal
        raise ValueError(f"Calendar not found: {name}")

    def delete_calendar(self, name: str) -> None:
        """Delete a calendar by name."""
        cal = self.get_calendar(name)
        cal.delete()
        logger.info("Deleted calendar: %s", name)

    # ── event operations ──────────────────────────────────────────────

    def add_event(
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
        """Add an event to a calendar. Returns the event UID."""
        cal = self.get_calendar(calendar_name)
        event_uid = uid or f"clawmark-{uuid.uuid4().hex[:12]}"
        cal.save_event(
            dtstart=dtstart,
            dtend=dtend,
            summary=summary,
            uid=event_uid,
            description=description,
            location=location,
        )
        logger.info("Added event '%s' (uid=%s) to %s", summary, event_uid, calendar_name)
        return event_uid

    def get_events(
        self,
        calendar_name: str,
        start: date | datetime | None = None,
        end: date | datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get events from a calendar, optionally filtered by date range."""
        cal = self.get_calendar(calendar_name)
        if start and end:
            events = cal.search(event=True, start=start, end=end, expand=True)
        else:
            events = cal.events()
        return [_event_to_dict(e) for e in events]

    def find_events(
        self,
        calendar_name: str,
        summary_contains: str,
    ) -> list[dict[str, Any]]:
        """Search events by summary substring."""
        all_events = self.get_events(calendar_name)
        return [
            e for e in all_events
            if summary_contains.lower() in e.get("summary", "").lower()
        ]

    def delete_event(self, calendar_name: str, uid: str) -> None:
        """Delete an event by UID."""
        cal = self.get_calendar(calendar_name)
        event = cal.event_by_uid(uid)
        event.delete()
        logger.info("Deleted event uid=%s from %s", uid, calendar_name)

    # ── lifecycle ─────────────────────────────────────────────────────

    def reset(self) -> None:
        """Delete all calendars (clean slate)."""
        for cal in self._principal.calendars():
            try:
                cal.delete()
            except Exception as e:
                logger.warning("Failed to delete calendar %s: %s", cal.name, e)
        logger.info("Reset: all calendars deleted")

    def seed(self, data: dict[str, Any]) -> dict[str, int]:
        """Seed calendars and events from a dict.

        Expected format::

            {
                "calendars": [
                    {
                        "name": "Work",
                        "events": [
                            {
                                "summary": "Meeting",
                                "dtstart": "2026-03-25T09:00:00",
                                "dtend": "2026-03-25T10:00:00",
                                "description": "...",
                                "location": "..."
                            }
                        ]
                    }
                ]
            }
        """
        cal_count = 0
        event_count = 0
        for cal_data in data.get("calendars", []):
            name = cal_data["name"]
            self.create_calendar(name)
            cal_count += 1
            for ev in cal_data.get("events", []):
                self.add_event(
                    calendar_name=name,
                    summary=ev["summary"],
                    dtstart=datetime.fromisoformat(ev["dtstart"]),
                    dtend=datetime.fromisoformat(ev["dtend"]),
                    description=ev.get("description", ""),
                    location=ev.get("location", ""),
                    uid=ev.get("uid"),
                )
                event_count += 1
        return {"calendars": cal_count, "events": event_count}

    def close(self) -> None:
        """Close the DAV client connection."""
        try:
            self._client.close()
        except Exception:
            pass


def _event_to_dict(event: caldav.Event) -> dict[str, Any]:
    """Convert a caldav Event to a plain dict."""
    comp = event.icalendar_component
    result: dict[str, Any] = {
        "uid": str(comp.get("uid", "")),
        "summary": str(comp.get("summary", "")),
    }
    dtstart = comp.get("dtstart")
    if dtstart:
        result["dtstart"] = dtstart.dt.isoformat() if hasattr(dtstart, "dt") else str(dtstart)
    dtend = comp.get("dtend")
    if dtend:
        result["dtend"] = dtend.dt.isoformat() if hasattr(dtend, "dt") else str(dtend)
    description = comp.get("description")
    if description:
        result["description"] = str(description)
    location = comp.get("location")
    if location:
        result["location"] = str(location)
    return result
