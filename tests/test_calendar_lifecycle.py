"""Smoke test for CalendarStateManager lifecycle.

Usage:
    # 1. Start Radicale
    docker compose -f docker/docker-compose.yaml up -d radicale

    # 2. Run test
    uv run python tests/test_calendar_lifecycle.py
"""
import asyncio
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_COMPOSE = Path(__file__).resolve().parent.parent / "docker" / "docker-compose.yaml"


def _docker_host_port(service: str, container_port: int) -> str | None:
    """Resolve the host port docker-compose assigned to a service's container port."""
    try:
        out = subprocess.check_output(
            ["docker", "compose", "-f", str(_COMPOSE), "port", service, str(container_port)],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.rsplit(":", 1)[1] if ":" in out else None


if "CALDAV_URL" not in os.environ:
    _port = _docker_host_port("radicale", 5232) or "5232"
    os.environ["CALDAV_URL"] = f"http://localhost:{_port}"

from clawmark.state.calendar import CalendarStateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class _NoopSandbox:
    async def exec(self, *a, **kw): pass
    async def upload_dir(self, *a, **kw): pass
    async def download_dir(self, *a, **kw): pass
    async def upload_file(self, *a, **kw): pass
    async def download_file(self, *a, **kw): pass


def _section(title: str):
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)


async def main():
    sandbox = _NoopSandbox()
    mgr = CalendarStateManager()

    # ── SETUP ──
    _section("SETUP: connect to Radicale + reset")
    await mgr.setup(sandbox=sandbox)
    cals = await mgr.list_calendars()
    assert len(cals) == 0, f"Expected 0 calendars after reset, got {len(cals)}"
    print("  Reset complete, 0 calendars")

    # ── CREATE CALENDAR ──
    _section("CREATE: create calendar '工作日程'")
    url = await mgr.create_calendar("工作日程")
    print(f"  Created: {url}")
    cals = await mgr.list_calendars()
    assert len(cals) == 1, f"Expected 1 calendar, got {len(cals)}"
    print(f"  Calendars: {[c['name'] for c in cals]}")

    # ── ADD EVENTS ──
    _section("ADD: add 3 events")
    now = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    uid1 = await mgr.add_event(
        "工作日程", "团队周会",
        dtstart=now, dtend=now + timedelta(hours=1),
        description="每周一团队同步会议", location="会议室A",
    )
    print(f"  [1] 团队周会 uid={uid1}")

    uid2 = await mgr.add_event(
        "工作日程", "项目评审",
        dtstart=now + timedelta(hours=2), dtend=now + timedelta(hours=3),
        description="Q1项目进度评审",
    )
    print(f"  [2] 项目评审 uid={uid2}")

    uid3 = await mgr.add_event(
        "工作日程", "1-on-1 with Manager",
        dtstart=now + timedelta(days=1), dtend=now + timedelta(days=1, hours=1),
    )
    print(f"  [3] 1-on-1 uid={uid3}")

    # ── LIST EVENTS ──
    _section("LIST: get all events")
    events = await mgr.get_events("工作日程")
    print(f"  Found {len(events)} events:")
    for e in events:
        print(f"    - {e['summary']} ({e.get('dtstart', '?')})")
    assert len(events) == 3, f"Expected 3 events, got {len(events)}"

    # ── SEARCH BY DATE ──
    _section("SEARCH: events for today only")
    today_start = now.replace(hour=0, minute=0)
    today_end = today_start + timedelta(days=1)
    today_events = await mgr.get_events("工作日程", start=today_start, end=today_end)
    print(f"  Today: {len(today_events)} events")
    for e in today_events:
        print(f"    - {e['summary']}")
    assert len(today_events) == 2, f"Expected 2 events today, got {len(today_events)}"

    # ── FIND BY KEYWORD ──
    _section("FIND: search for '评审'")
    found = await mgr.find_events("工作日程", "评审")
    print(f"  Found {len(found)} matching events")
    assert len(found) == 1, f"Expected 1 match, got {len(found)}"
    assert found[0]["summary"] == "项目评审"
    print(f"  Match: {found[0]['summary']}")

    # ── DELETE EVENT ──
    _section("DELETE: remove '项目评审'")
    await mgr.delete_event("工作日程", uid2)
    events_after = await mgr.get_events("工作日程")
    print(f"  Remaining: {len(events_after)} events")
    assert len(events_after) == 2, f"Expected 2 events after delete, got {len(events_after)}"
    remaining_summaries = {e["summary"] for e in events_after}
    assert "项目评审" not in remaining_summaries, "Deleted event still present!"
    print(f"  Events: {remaining_summaries}")

    # ── CLEANUP ──
    _section("CLEANUP: delete all calendars")
    await mgr.cleanup()
    # Re-init to verify cleanup worked
    mgr2 = CalendarStateManager()
    await mgr2.setup(sandbox=sandbox)
    cals = await mgr2.list_calendars()
    assert len(cals) == 0, f"Expected 0 calendars after cleanup, got {len(cals)}"
    print("  All calendars deleted, state is clean")
    await mgr2.cleanup()

    _section("ALL STEPS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
