"""Synchronous IMAP/SMTP client for local GreenMail.

Adapted from Toolathlon's ``LocalEmailManager``.  All methods are plain
synchronous — the async boundary lives in ``EmailStateManager`` which
wraps calls with ``asyncio.to_thread``.
"""
from __future__ import annotations

import email as email_mod
import imaplib
import logging
import smtplib
import time
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

logger = logging.getLogger(__name__)


class EmailClient:
    """IMAP/SMTP client for a single email account on a local GreenMail server."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.email_addr: str = config["email"]
        self.password: str = config.get("password", "")
        self.name: str = config.get("name", self.email_addr)
        self.imap_server: str = config["imap_server"]
        self.imap_port: int = int(config["imap_port"])
        self.smtp_server: str = config["smtp_server"]
        self.smtp_port: int = int(config["smtp_port"])
        self.use_ssl: bool = bool(config.get("use_ssl", False))
        self.use_starttls: bool = bool(config.get("use_starttls", False))

    # ── IMAP helpers ─────────────────────────────────────────────────

    def _connect_imap(self) -> imaplib.IMAP4:
        if self.use_ssl:
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, timeout=10)
        else:
            imap = imaplib.IMAP4(self.imap_server, self.imap_port, timeout=10)
            if self.use_starttls:
                imap.starttls()
        imap.login(self.email_addr, self.password)
        return imap

    @staticmethod
    def _close_imap(imap: imaplib.IMAP4 | None) -> None:
        if imap is None:
            return
        try:
            imap.close()
        except Exception:
            pass
        try:
            imap.logout()
        except Exception:
            pass

    # ── IMAP operations ──────────────────────────────────────────────

    def list_mailboxes(self) -> list[str]:
        imap = self._connect_imap()
        try:
            status, data = imap.list()
            if status != "OK":
                return ["INBOX"]
            names: set[str] = set()
            for item in data:
                line = item.decode() if isinstance(item, bytes) else str(item)
                # Parse IMAP LIST response: (\flags) "sep" "name"
                parts = line.rsplit('"', 2)
                if len(parts) >= 2:
                    name = parts[-1].strip().strip('"')
                    if name:
                        names.add(name)
            if "INBOX" not in names:
                names.add("INBOX")
            return sorted(names)
        finally:
            self._close_imap(imap)

    def get_emails(self, folder: str = "INBOX") -> list[dict[str, Any]]:
        imap = self._connect_imap()
        results: list[dict[str, Any]] = []
        try:
            status, _ = imap.select(folder)
            if status != "OK":
                return []
            status, data = imap.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []
            for num in data[0].split():
                status, msg_data = imap.fetch(num, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email_mod.message_from_bytes(msg_data[0][1])
                results.append({
                    "subject": _decode_mime(msg.get("Subject", "")),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "cc": msg.get("Cc", ""),
                    "date": msg.get("Date", ""),
                    "body": _extract_body(msg),
                })
            return results
        finally:
            self._close_imap(imap)

    def find_emails(
        self,
        *,
        sender: str | None = None,
        subject: str | None = None,
        folder: str = "INBOX",
    ) -> list[dict[str, Any]]:
        imap = self._connect_imap()
        results: list[dict[str, Any]] = []
        try:
            status, _ = imap.select(folder)
            if status != "OK":
                return []

            # Build IMAP search criteria
            criteria: list[str] = []
            if sender:
                criteria.append(f'(FROM "{sender}")')
            if subject:
                criteria.append(f'(SUBJECT "{subject}")')
            search_str = " ".join(criteria) if criteria else "ALL"

            status, data = imap.search(None, search_str)
            if status != "OK" or not data or not data[0]:
                return []

            for num in data[0].split():
                status, msg_data = imap.fetch(num, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email_mod.message_from_bytes(msg_data[0][1])
                results.append({
                    "subject": _decode_mime(msg.get("Subject", "")),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "cc": msg.get("Cc", ""),
                    "date": msg.get("Date", ""),
                    "body": _extract_body(msg),
                })
            return results
        finally:
            self._close_imap(imap)

    def clear_folder(self, folder: str = "INBOX") -> int:
        imap = self._connect_imap()
        try:
            status, _ = imap.select(folder)
            if status != "OK":
                return 0
            status, data = imap.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return 0
            ids = data[0].split()
            if not ids:
                return 0
            # Bulk delete with store 1:*
            imap.store("1:*", "+FLAGS.SILENT", r"(\Deleted)")
            imap.expunge()
            return len(ids)
        finally:
            self._close_imap(imap)

    def clear_all_folders(self) -> None:
        folders = self.list_mailboxes()
        for folder in folders:
            try:
                self.clear_folder(folder)
            except Exception as e:
                logger.warning("Failed to clear folder %s for %s: %s", folder, self.email_addr, e)

    # ── SMTP operations ──────────────────────────────────────────────

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        content_type: str = "plain",
        sender_name: str | None = None,
    ) -> bool:
        try:
            msg = MIMEMultipart()
            display_name = sender_name or self.name
            msg["From"] = formataddr((display_name, self.email_addr))
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, _subtype=content_type, _charset="utf-8"))

            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
                server.ehlo()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                server.ehlo_or_helo_if_needed()
                if self.use_starttls:
                    esmtp = getattr(server, "esmtp_features", {})
                    if "starttls" in esmtp:
                        server.starttls()
                        server.ehlo()

            # Login only if server supports AUTH and we have a password
            esmtp = getattr(server, "esmtp_features", {})
            if "auth" in esmtp and self.password:
                try:
                    server.login(self.email_addr, self.password)
                except smtplib.SMTPNotSupportedError:
                    pass

            server.send_message(msg, from_addr=self.email_addr)
            server.quit()
            return True
        except Exception as e:
            logger.error("Failed to send email from %s to %s: %s", self.email_addr, to, e)
            return False

    def import_backup(self, backup_data: dict[str, Any]) -> int:
        """Import emails from a Toolathlon-format backup JSON via SMTP."""
        emails = backup_data.get("emails", [])
        if not emails:
            return 0

        imported = 0
        for entry in emails:
            from_addr = entry.get("from_addr", self.email_addr)
            to_addr = entry.get("to_addr", self.email_addr)
            subject_str = entry.get("subject", "(no subject)")
            body_html = entry.get("body_html", "")
            body_text = entry.get("body_text", "")

            # Prefer HTML body, fall back to text
            if body_html:
                content_type = "html"
                body = body_html
            else:
                content_type = "plain"
                body = body_text

            # Extract sender display name from "Name <addr>" format
            sender_name = None
            if "<" in from_addr and ">" in from_addr:
                sender_name = from_addr.split("<")[0].strip().strip('"')
                from_email = from_addr.split("<")[1].rstrip(">")
            else:
                from_email = from_addr

            try:
                msg = MIMEMultipart()
                if sender_name:
                    msg["From"] = formataddr((sender_name, from_email))
                else:
                    msg["From"] = from_email
                msg["To"] = to_addr
                msg["Subject"] = subject_str

                if entry.get("date"):
                    msg["Date"] = entry["date"]

                msg.attach(MIMEText(body, _subtype=content_type, _charset="utf-8"))

                if self.use_ssl:
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
                else:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                    server.ehlo_or_helo_if_needed()

                esmtp = getattr(server, "esmtp_features", {})
                if "auth" in esmtp and self.password:
                    try:
                        server.login(self.email_addr, self.password)
                    except smtplib.SMTPNotSupportedError:
                        pass

                server.send_message(msg, from_addr=from_email)
                server.quit()
                imported += 1
            except Exception as e:
                logger.warning("Failed to import email '%s': %s", subject_str, e)

            # Small delay to avoid overwhelming the server
            time.sleep(0.3)

        return imported


# ── Module-level helpers ─────────────────────────────────────────────


def _decode_mime(value: str) -> str:
    """Decode a MIME-encoded header value to plain text."""
    if not value:
        return ""
    try:
        parts = decode_header(value)
        result = ""
        for part, charset in parts:
            if isinstance(part, bytes):
                result += part.decode(charset or "utf-8", errors="replace")
            else:
                result += part
        return result
    except Exception:
        return value


def _extract_body(msg: email_mod.message.Message) -> str:
    """Extract body text, preferring text/plain over text/html."""
    if msg.is_multipart():
        plain = None
        html = None
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", "")).lower()
            if "attachment" in disp:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ctype == "text/plain" and plain is None:
                plain = text
            elif ctype == "text/html" and html is None:
                html = text
        return plain if plain is not None else (html or "")
    else:
        payload = msg.get_payload(decode=True)
        if payload is None:
            return ""
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
