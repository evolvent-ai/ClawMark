"""Dry-run sandbox — no Docker, for testing the framework pipeline."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .base import BaseSandbox, ExecResult

logger = logging.getLogger(__name__)


class DryRunSandbox(BaseSandbox):
    """No-op sandbox that uses a local directory instead of Docker."""

    def __init__(self, workspace_dir: Path | None = None):
        self.workspace_dir = workspace_dir or Path("/tmp/clawmark-dryrun")

    async def start(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        logger.info("[dry_run] Sandbox started at %s", self.workspace_dir)

    async def stop(self, delete: bool = True) -> None:
        if delete and self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir, ignore_errors=True)
        logger.info("[dry_run] Sandbox stopped")

    async def exec(self, command: str, timeout_sec: int = 300, env: dict[str, str] | None = None) -> ExecResult:
        logger.info("[dry_run] exec: %s", command[:200])
        return ExecResult(stdout="", stderr="", return_code=0)

    async def upload_file(self, local_path: Path, remote_path: str) -> None:
        dst = self.workspace_dir / remote_path.lstrip("/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dst)

    async def upload_dir(self, local_dir: Path, remote_dir: str) -> None:
        dst = self.workspace_dir / remote_dir.lstrip("/")
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(local_dir, dst, dirs_exist_ok=True)

    async def download_file(self, remote_path: str, local_path: Path) -> None:
        src = self.workspace_dir / remote_path.lstrip("/")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, local_path)

    async def download_dir(self, remote_dir: str, local_dir: Path) -> None:
        src = self.workspace_dir / remote_dir.lstrip("/")
        local_dir.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copytree(src, local_dir, dirs_exist_ok=True)
