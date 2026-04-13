"""Synchronous Google Sheets / Drive client with retry and token refresh.

All methods are blocking — the manager wraps them with ``asyncio.to_thread``.
"""
from __future__ import annotations

import json
import logging
import re
import ssl
import time
from http.client import HTTPException
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_BACKOFF_BASE = 2  # seconds
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_TRANSPORT_ERRORS = (ssl.SSLError, ConnectionError, ConnectionResetError, OSError, HTTPException)
_SHEET_ID_RE = re.compile(r"^[\w-]{20,}$")


def _escape_drive_query(value: str) -> str:
    """Escape a string for use in a Drive API query literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _extract_sheet_id(url_or_id: str) -> str:
    """Extract spreadsheet ID from a URL or return a raw ID."""
    # Strip query string and fragment before parsing
    clean = url_or_id.split("?")[0].split("#")[0]
    if "/d/" in clean:
        try:
            return clean.split("/d/")[1].split("/")[0]
        except IndexError:
            raise ValueError(f"Cannot parse spreadsheet ID from URL: {url_or_id}")
    if _SHEET_ID_RE.match(clean):
        return clean
    raise ValueError(f"Invalid spreadsheet URL or ID: {url_or_id}")


class GoogleSheetsClient:
    """Sync Google Sheets / Drive client with retry + auto token refresh."""

    def __init__(self, credentials_path: str) -> None:
        with open(credentials_path) as f:
            cred_data = json.load(f)

        self._creds = Credentials(
            token=cred_data.get("token"),
            refresh_token=cred_data["refresh_token"],
            token_uri=cred_data["token_uri"],
            client_id=cred_data["client_id"],
            client_secret=cred_data["client_secret"],
            scopes=cred_data.get("scopes"),
        )
        self._creds.refresh(Request())

        self._drive = build("drive", "v3", credentials=self._creds)
        self._sheets = build("sheets", "v4", credentials=self._creds)

    def _rebuild_services(self) -> None:
        """Rebuild API service objects with fresh HTTP connections."""
        self._creds.refresh(Request())
        self._drive = build("drive", "v3", credentials=self._creds)
        self._sheets = build("sheets", "v4", credentials=self._creds)

    # ── retry helper ─────────────────────────────────────────────────

    def _retry(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        for attempt in range(_MAX_RETRIES):
            try:
                if not self._creds.valid:
                    self._creds.refresh(Request())
                return fn(*args, **kwargs)
            except HttpError as exc:
                code = exc.resp.status
                if code in _RETRYABLE_CODES and attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "Google API %d, retry %d/%d in %ds",
                        code, attempt + 1, _MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    continue
                raise
            except _TRANSPORT_ERRORS as exc:
                if attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_BASE ** (attempt + 1)
                    logger.warning(
                        "Google transport error (%s), retry %d/%d in %ds",
                        exc, attempt + 1, _MAX_RETRIES, wait,
                    )
                    self._rebuild_services()
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"Google API failed after {_MAX_RETRIES} retries")

    # ── Drive operations ─────────────────────────────────────────────

    def create_folder(self, name: str) -> str:
        """Create a Drive folder and return its ID."""
        body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        folder = self._retry(
            self._drive.files().create(body=body, fields="id").execute,
        )
        logger.info("Created Drive folder %s (%s)", name, folder["id"])
        return folder["id"]

    def find_folder(self, name: str) -> str | None:
        """Find a Drive folder by exact name. Returns folder ID or None."""
        safe_name = _escape_drive_query(name)
        resp = self._retry(
            self._drive.files()
            .list(
                q=f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id)",
            )
            .execute,
        )
        files = resp.get("files", [])
        return files[0]["id"] if files else None

    def clear_folder(self, folder_id: str) -> None:
        """Delete all files inside a folder (handles pagination)."""
        page_token = None
        while True:
            resp = self._retry(
                self._drive.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="files(id),nextPageToken",
                    pageToken=page_token,
                )
                .execute,
            )
            for f in resp.get("files", []):
                self._retry(self._drive.files().delete(fileId=f["id"]).execute)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    def delete_folder(self, folder_id: str) -> None:
        """Delete a folder and all its contents."""
        self.clear_folder(folder_id)
        self._retry(self._drive.files().delete(fileId=folder_id).execute)

    def copy_sheet_to_folder(self, sheet_url: str, folder_id: str) -> str:
        """Copy a spreadsheet (by URL or ID) into *folder_id*. Returns new sheet ID."""
        source_id = _extract_sheet_id(sheet_url)

        original = self._retry(
            self._drive.files().get(fileId=source_id, fields="name").execute,
        )

        copied = self._retry(
            self._drive.files()
            .copy(fileId=source_id, body={"parents": [folder_id]})
            .execute,
        )
        new_id = copied["id"]

        # Restore original name
        self._retry(
            self._drive.files()
            .update(fileId=new_id, body={"name": original["name"]})
            .execute,
        )

        # Make writable by anyone so the sandbox agent can access without
        # additional OAuth.  These are ephemeral copies deleted during cleanup.
        self._retry(
            self._drive.permissions()
            .create(fileId=new_id, body={"role": "writer", "type": "anyone"})
            .execute,
        )

        logger.info("Copied sheet %s → %s in folder %s", source_id, new_id, folder_id)
        return new_id

    def create_spreadsheet(self, title: str, folder_id: str) -> str:
        """Create a blank spreadsheet in *folder_id*. Returns spreadsheet ID."""
        body = {"properties": {"title": title}}
        sheet = self._retry(
            self._sheets.spreadsheets().create(body=body, fields="spreadsheetId").execute,
        )
        sheet_id = sheet["spreadsheetId"]

        # Move into isolation folder
        self._retry(
            self._drive.files()
            .update(fileId=sheet_id, addParents=folder_id, removeParents="root", fields="id")
            .execute,
        )

        # Make writable by anyone (same as copy_sheet_to_folder)
        self._retry(
            self._drive.permissions()
            .create(fileId=sheet_id, body={"role": "writer", "type": "anyone"})
            .execute,
        )

        logger.info("Created sheet '%s' (%s) in folder %s", title, sheet_id, folder_id)
        return sheet_id

    def find_spreadsheet(self, folder_id: str, name: str) -> str | None:
        """Find a spreadsheet by name within a folder."""
        safe_name = _escape_drive_query(name)
        q = (
            f"'{folder_id}' in parents and name='{safe_name}' "
            f"and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        )
        resp = self._retry(
            self._drive.files().list(q=q, fields="files(id)").execute,
        )
        files = resp.get("files", [])
        return files[0]["id"] if files else None

    # ── Sheets operations ────────────────────────────────────────────

    def read_values(self, spreadsheet_id: str, range_: str) -> list[list[str]]:
        """Read cell values from a range (e.g. ``Sheet1!A1:C10``)."""
        resp = self._retry(
            self._sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_)
            .execute,
        )
        return resp.get("values", [])

    def update_values(
        self, spreadsheet_id: str, range_: str, values: list[list],
    ) -> None:
        """Write *values* to *range_*."""
        self._retry(
            self._sheets.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="RAW",
                body={"values": values},
            )
            .execute,
        )

    def append_rows(
        self, spreadsheet_id: str, range_: str, rows: list[list],
    ) -> None:
        """Append *rows* after the last row in *range_*."""
        self._retry(
            self._sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": rows},
            )
            .execute,
        )

    def find_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        col_index: int,
        value: str,
    ) -> dict | None:
        """Scan *col_index* in *sheet_name* for *value*. Returns row as dict or None."""
        all_values = self.read_values(spreadsheet_id, sheet_name)
        if len(all_values) < 2:
            return None
        headers = all_values[0]
        for row in all_values[1:]:
            if col_index < len(row) and row[col_index] == value:
                return dict(zip(headers, row))
        return None
