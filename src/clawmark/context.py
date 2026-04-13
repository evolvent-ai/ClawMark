"""Task context — passed to stage and checker functions in task.py."""
from __future__ import annotations

from pathlib import Path
from typing import Any


class TaskContext:
    """Provides stage/checker functions access to managers, sandbox, and workspace snapshots."""

    def __init__(
        self,
        managers: dict[str, Any],
        sandbox: Any,
        task_dir: Path,
    ) -> None:
        self.sandbox = sandbox
        self.task_dir = task_dir
        self.workspace: Path | None = None          # current stage workspace snapshot
        self.snapshots: dict[str, Path] = {}        # stage_id → snapshot path
        self._managers = managers
        # Expose each manager as a named attribute
        for name, mgr in managers.items():
            setattr(self, name, mgr)
        # Convenience alias: ctx.fs = ctx.filesystem
        if "filesystem" in managers:
            self.fs = managers["filesystem"]
