"""Load task definitions from task.py modules."""
from __future__ import annotations

import asyncio
import importlib.util
import logging
from pathlib import Path

from .models import RubricEntry, TaskDefinition

logger = logging.getLogger(__name__)

_REQUIRED_METADATA = ("id", "name", "category", "environments")


def load_task_py(task_dir: Path) -> TaskDefinition:
    """Load a complete task from its task.py module."""
    task_dir = Path(task_dir)
    task_py = task_dir / "task.py"
    if not task_py.exists():
        raise FileNotFoundError(f"task.py not found in {task_dir}")

    # Load module with unique name to avoid collisions
    module_name = f"clawmark_task_{task_dir.name}_{id(task_dir)}"
    spec = importlib.util.spec_from_file_location(module_name, task_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Validate METADATA
    metadata = getattr(module, "METADATA", None)
    if not isinstance(metadata, dict):
        raise ValueError(f"METADATA dict required in {task_py}")
    for field in _REQUIRED_METADATA:
        if field not in metadata:
            raise ValueError(f"Missing required METADATA field '{field}' in {task_py}")

    # Validate PROMPT
    prompt = getattr(module, "PROMPT", None)
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"PROMPT string required in {task_py}")

    # Discover stage functions (stage0, stage1, ... — must be contiguous)
    stage_fns = []
    i = 0
    while True:
        fn = getattr(module, f"stage{i}", None)
        if fn is None:
            break
        if not asyncio.iscoroutinefunction(fn):
            raise TypeError(f"stage{i} must be async def in {task_py}")
        stage_fns.append(fn)
        i += 1

    if not stage_fns:
        raise ValueError(f"No stage functions (stage0, stage1, ...) found in {task_py}")

    # Check for gaps (e.g., stage0 + stage2 but no stage1)
    j = i
    while j < i + 10:
        if getattr(module, f"stage{j}", None) is not None:
            raise ValueError(
                f"stage{j} found but stage{i} missing — stage numbers must be contiguous in {task_py}"
            )
        j += 1

    # Parse RUBRIC
    raw_rubric = getattr(module, "RUBRIC", None)
    if not isinstance(raw_rubric, dict):
        raise ValueError(f"RUBRIC dict required in {task_py}")

    stage_ids = {f"stage{k}" for k in range(len(stage_fns))}
    rubric: dict[str, list[RubricEntry]] = {}
    for key, entries in raw_rubric.items():
        if key != "final" and key not in stage_ids:
            raise ValueError(
                f"RUBRIC key '{key}' doesn't match any stage function. "
                f"Available: {stage_ids | {'final'}}"
            )
        parsed = []
        for e in entries:
            checker = e["checker"]
            if not asyncio.iscoroutinefunction(checker):
                raise TypeError(
                    f"RUBRIC checker '{e['id']}' must be async def in {task_py}"
                )
            parsed.append(RubricEntry(
                id=e["id"],
                checker=checker,
                weight=float(e.get("weight", 1.0)),
                description=e.get("description", "") or (checker.__doc__ or "").strip(),
            ))
        rubric[key] = parsed

    return TaskDefinition(
        id=metadata["id"],
        name=metadata["name"],
        category=metadata["category"],
        environments=metadata["environments"],
        prompt=prompt,
        stage_fns=stage_fns,
        rubric=rubric,
        env_config=metadata.get("env_config", {}),
        task_dir=task_dir,
        timeout_seconds=7200,
        difficulty=metadata.get("difficulty", "medium"),
        mm_level=metadata.get("mm_level", "L2"),
        role=metadata.get("role", ""),
        tags=metadata.get("tags", []),
    )


def discover_task_dirs(tasks_root: Path) -> list[Path]:
    """Discover all task directories (containing task.py) under a root."""
    dirs = []
    for task_dir in sorted(tasks_root.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith("."):
            continue
        if (task_dir / "task.py").exists():
            dirs.append(task_dir)
    return dirs
