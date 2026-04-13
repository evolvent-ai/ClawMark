"""Composite state manager — orchestrates per-service managers for a task."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from .base import BaseStateManager
from .progress import ProgressDisplay
from ..sandbox.base import BaseSandbox

logger = logging.getLogger(__name__)


class CompositeStateManager:
    """Manages state across all environments declared by a task."""

    def __init__(
        self,
        environments: list[str],
        env_config: dict[str, dict[str, Any]] | None = None,
    ):
        env_config = env_config or {}
        self.managers: dict[str, BaseStateManager] = {
            env: BaseStateManager.create(env, config=env_config.get(env))
            for env in environments
        }

    async def setup(self, *, sandbox: BaseSandbox) -> None:
        """Setup all managers in parallel with live progress display."""
        names = list(self.managers.keys())
        progress = ProgressDisplay(names, phase="setup")
        progress.start()

        async def _run(name: str) -> None:
            mgr = self.managers[name]
            progress.mark_running(name)
            try:
                await mgr.setup(sandbox=sandbox)
                progress.mark_done(name)
            except Exception as e:
                progress.mark_error(name, str(e))
                raise

        tasks = [asyncio.create_task(_run(n)) for n in names]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            progress.stop()

        for r in results:
            if isinstance(r, BaseException):
                raise r

    async def cleanup(self) -> None:
        """Cleanup all managers in parallel."""
        progress = ProgressDisplay(list(self.managers.keys()), phase="cleanup")
        progress.start()

        async def _run(name: str) -> None:
            progress.mark_running(name)
            try:
                await self.managers[name].cleanup()
                progress.mark_done(name)
            except Exception as e:
                progress.mark_error(name, str(e))

        try:
            await asyncio.gather(*[_run(n) for n in self.managers])
        finally:
            progress.stop()

    def get_manager(self, env_name: str) -> BaseStateManager | None:
        return self.managers.get(env_name)

    def create_context(self, *, task_dir: Path, sandbox: BaseSandbox):
        """Build a TaskContext from current managers."""
        from ..context import TaskContext
        return TaskContext(managers=self.managers, sandbox=sandbox, task_dir=task_dir)
