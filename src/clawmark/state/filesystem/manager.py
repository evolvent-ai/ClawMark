"""Filesystem state manager — workspace file management."""
from __future__ import annotations

import logging
import shlex
from pathlib import Path

from ..base import BaseStateManager
from ...sandbox.base import BaseSandbox

logger = logging.getLogger(__name__)


@BaseStateManager.register("filesystem")
class FilesystemStateManager(BaseStateManager):

    async def setup(self, *, sandbox: BaseSandbox) -> None:
        self._sandbox = sandbox
        await sandbox.exec("mkdir -p /workspace")
        logger.info("Filesystem ready: /workspace")

    # ── public methods ──────────────────────────────────────────────

    async def upload_dir(self, local_dir: Path, remote_dir: str) -> None:
        await self._sandbox.upload_dir(local_dir, remote_dir)
        logger.info("Uploaded %s → %s", local_dir.name, remote_dir)

    async def upload_file(self, local_path: Path, remote_path: str) -> None:
        await self._sandbox.upload_file(local_path, remote_path)
        logger.info("Uploaded %s → %s", local_path.name, remote_path)

    async def delete_file(self, remote_path: str) -> None:
        await self._sandbox.exec(f"rm -rf {shlex.quote(remote_path)}")
        logger.info("Deleted %s", remote_path)

    async def exists(self, remote_path: str) -> bool:
        result = await self._sandbox.exec(
            f"test -e {shlex.quote(remote_path)} && echo yes || echo no"
        )
        return result.stdout.strip() == "yes"

    async def read_file(self, remote_path: str) -> str:
        result = await self._sandbox.exec(f"cat {shlex.quote(remote_path)}")
        return result.stdout

    # ── cleanup ─────────────────────────────────────────────────────

    async def cleanup(self) -> None:
        if self._sandbox:
            await self._sandbox.exec("rm -rf /workspace/*")
            logger.info("Cleaned up /workspace")
