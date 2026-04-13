"""Core data models for ClawMark."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class GradingMethod(str, Enum):
    RULE = "rule"
    LLM_AS_JUDGE = "llm_as_judge"


@dataclass
class RubricEntry:
    """One checker entry in RUBRIC dict, converted by loader from task.py."""
    id: str
    checker: Callable       # async def check(ctx) -> bool
    weight: float = 1.0
    description: str = ""   # auto-filled from checker.__doc__


@dataclass
class TaskDefinition:
    """Complete task loaded from a task.py module."""
    id: str
    name: str
    category: str
    environments: list[str]
    prompt: str
    stage_fns: list[Callable]                    # [stage0, stage1, ...]
    rubric: dict[str, list[RubricEntry]]         # "stage0" → entries, "final" → entries
    env_config: dict[str, dict[str, Any]]
    task_dir: Path
    timeout_seconds: int = 600
    difficulty: str = "medium"
    mm_level: str = "L2"
    role: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class StageResult:
    """Result of one stage execution."""
    stage_id: str
    agent_output: str = ""
    success: bool = True
    error: str = ""
    verification: list[RubricItemResult] = field(default_factory=list)
    verification_score: float = -1.0


@dataclass
class RubricItemResult:
    """Result of evaluating one rubric item."""
    item_id: str
    passed: bool
    weight: float
    method: GradingMethod = GradingMethod.RULE
    detail: str = ""


@dataclass
class EvaluationResult:
    """Aggregated evaluation result."""
    results: list[RubricItemResult] = field(default_factory=list)
    score: float = 0.0


@dataclass
class TaskResult:
    """Complete result of running + evaluating one task."""
    task_id: str
    stage_results: list[StageResult] = field(default_factory=list)
    rubric_results: list[RubricItemResult] = field(default_factory=list)
    score: float = 0.0
    execution_time: float = 0.0
    error: str = ""
