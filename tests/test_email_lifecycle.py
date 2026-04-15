"""Smoke test for EmailStateManager lifecycle.

Usage:
    # 1. Start GreenMail
    docker compose -f docker/docker-compose.yaml up -d greenmail

    # 2. Run test
    EMAIL_IMAP_SERVER=localhost EMAIL_IMAP_PORT=3143 \
    EMAIL_SMTP_SERVER=localhost EMAIL_SMTP_PORT=3025 \
    uv run python tests/test_email_lifecycle.py
"""
import asyncio
import logging
import os
import subprocess
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


os.environ.setdefault("EMAIL_IMAP_SERVER", "localhost")
os.environ.setdefault("EMAIL_SMTP_SERVER", "localhost")
if "EMAIL_IMAP_PORT" not in os.environ:
    os.environ["EMAIL_IMAP_PORT"] = _docker_host_port("greenmail", 3143) or "3143"
if "EMAIL_SMTP_PORT" not in os.environ:
    os.environ["EMAIL_SMTP_PORT"] = _docker_host_port("greenmail", 3025) or "3025"

from clawmark.state.email import EmailStateManager

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

    config = {
        "users": {
            "sender": {"email": "sender@test.com", "password": "sender_pwd"},
            "receiver": {"email": "receiver@test.com", "password": "receiver_pwd"},
        },
    }

    mgr = EmailStateManager(config=config)

    # ── SETUP ──
    _section("SETUP: initialize clients")
    await mgr.setup(sandbox=sandbox)
    print("  OK")

    # ── SEND ──
    _section("SEND: sender sends email to receiver")
    ok = await mgr.send_email(
        from_user="sender",
        to="receiver@test.com",
        subject="Test: Meeting at 3pm",
        body="Hi, the meeting is at 3pm today.",
    )
    assert ok, "Send failed"
    print("  Sent OK")

    # ── READ ──
    _section("READ: check receiver inbox")
    await asyncio.sleep(1)
    emails = await mgr.get_emails("receiver")
    print(f"  Inbox: {len(emails)} emails")
    assert len(emails) >= 1, f"Expected >= 1 email, got {len(emails)}"
    print(f"  Subject: {emails[0].get('subject')}")
    print(f"  From: {emails[0].get('from')}")

    # ── FIND ──
    _section("FIND: search by subject")
    found = await mgr.find_emails("receiver", subject="Meeting")
    assert len(found) == 1, f"Expected 1 match, got {len(found)}"
    print(f"  Found {len(found)} match")

    # ── SEND ANOTHER ──
    _section("SEND: sender sends second email")
    ok2 = await mgr.send_email(
        from_user="sender",
        to="receiver@test.com",
        subject="Test: Lunch tomorrow",
        body="Want to grab lunch tomorrow?",
    )
    assert ok2
    await asyncio.sleep(1)
    emails2 = await mgr.get_emails("receiver")
    assert len(emails2) >= 2, f"Expected >= 2 emails, got {len(emails2)}"
    print(f"  Inbox now: {len(emails2)} emails")

    # ── FIND BY SENDER ──
    _section("FIND: search by sender")
    found2 = await mgr.find_emails("receiver", sender="sender@test.com")
    assert len(found2) >= 2, f"Expected >= 2 from sender, got {len(found2)}"
    print(f"  Found {len(found2)} from sender")

    # ── CLEANUP ──
    _section("CLEANUP: clear all mailboxes")
    await mgr.cleanup()
    print("  Done")

    _section("ALL STEPS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
