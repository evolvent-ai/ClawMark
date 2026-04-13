"""Email state manager — local IMAP/SMTP lifecycle via GreenMail.

Configuration (env_config.email):
- users: dict mapping logical names to {email, password}

Global (environment variables):
- EMAIL_IMAP_SERVER/PORT, EMAIL_SMTP_SERVER/PORT, EMAIL_USE_SSL, EMAIL_USE_STARTTLS
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from ..base import BaseStateManager
from .client import EmailClient
from ...sandbox.base import BaseSandbox

logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _server_config() -> dict[str, Any]:
    return {
        "imap_server": _env("EMAIL_IMAP_SERVER", "localhost"),
        "imap_port": int(_env("EMAIL_IMAP_PORT", "3143")),
        "smtp_server": _env("EMAIL_SMTP_SERVER", "localhost"),
        "smtp_port": int(_env("EMAIL_SMTP_PORT", "3025")),
        "use_ssl": _env("EMAIL_USE_SSL", "false").lower() == "true",
        "use_starttls": _env("EMAIL_USE_STARTTLS", "false").lower() == "true",
    }


@BaseStateManager.register("email")
class EmailStateManager(BaseStateManager):
    """Manages email state for a single benchmark task via local GreenMail."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._clients: dict[str, EmailClient] = {}

    def _build_clients(self) -> None:
        users = self.config.get("users", {})
        if not users:
            raise ValueError("EmailStateManager requires 'users' in env_config.email.")
        server = _server_config()
        # Apply dynamic port overrides from sandbox
        overrides = getattr(self, "_port_overrides", {})
        if 3025 in overrides:
            server["smtp_port"] = overrides[3025]
        if 3143 in overrides:
            server["imap_port"] = overrides[3143]
        for name, user_info in users.items():
            client_config = {**server, **user_info}
            self._clients[name] = EmailClient(client_config)

    def get_client(self, name: str) -> EmailClient | None:
        return self._clients.get(name)

    # ── lifecycle ────────────────────────────────────────────────────

    async def setup(self, *, sandbox: BaseSandbox) -> None:
        self._sandbox = sandbox
        # Override server ports with dynamically assigned sandbox ports
        self._port_overrides = getattr(sandbox, "ports", {})
        self._build_clients()

    async def cleanup(self) -> None:
        for name, client in self._clients.items():
            try:
                await asyncio.to_thread(client.clear_all_folders)
                logger.info("Cleared all folders for %s", name)
            except Exception as e:
                logger.warning("Cleanup failed for %s: %s", name, e)
        self._clients.clear()

    # ── public methods ───────────────────────────────────────────────

    async def send_email(
        self,
        from_user: str,
        to: str,
        subject: str,
        body: str,
        content_type: str = "plain",
        sender_name: str | None = None,
    ) -> bool:
        client = self._clients.get(from_user)
        if not client:
            raise ValueError(f"Unknown user: {from_user}. Available: {list(self._clients)}")
        return await asyncio.to_thread(
            client.send_email, to, subject, body, content_type, sender_name,
        )

    async def clear_folder(self, user: str, folder: str = "INBOX") -> None:
        client = self._clients.get(user)
        if not client:
            raise ValueError(f"Unknown user: {user}")
        await asyncio.to_thread(client.clear_folder, folder)

    async def clear_all_folders(self, user: str) -> None:
        client = self._clients.get(user)
        if not client:
            raise ValueError(f"Unknown user: {user}")
        await asyncio.to_thread(client.clear_all_folders)

    async def import_backup(self, user: str, backup_path: Path) -> int:
        client = self._clients.get(user)
        if not client:
            raise ValueError(f"Unknown user: {user}")
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        return await asyncio.to_thread(client.import_backup, backup_data)

    async def get_emails(self, user: str, folder: str = "INBOX") -> list[dict]:
        client = self._clients.get(user)
        if not client:
            raise ValueError(f"Unknown user: {user}")
        return await asyncio.to_thread(client.get_emails, folder)

    async def find_emails(
        self, user: str, *, sender: str | None = None, subject: str | None = None,
    ) -> list[dict]:
        emails = await self.get_emails(user)
        results = []
        for e in emails:
            if sender and sender.lower() not in e.get("from", "").lower():
                continue
            if subject and subject.lower() not in e.get("subject", "").lower():
                continue
            results.append(e)
        return results
