"""Base state manager interface.

Each state manager handles one external service (filesystem, notion, email, etc.)
and provides two lifecycle methods:

- setup:   initialize client connections, store sandbox reference
- cleanup: tear down all created resources
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..sandbox.base import BaseSandbox


class BaseStateManager(ABC):
    """Unified state management interface for all environment types."""

    _registry: dict[str, type[BaseStateManager]] = {}

    def __init__(self, config: dict[str, Any] | None = None):
        self.config: dict[str, Any] = config or {}
        self._sandbox: BaseSandbox | None = None

    # ── registry ────────────────────────────────────────────────────

    @classmethod
    def register(cls, name: str):
        """Decorator to register a state manager by environment name."""
        def decorator(subclass: type[BaseStateManager]) -> type[BaseStateManager]:
            cls._registry[name] = subclass
            return subclass
        return decorator

    @classmethod
    def create(cls, name: str, config: dict[str, Any] | None = None) -> BaseStateManager:
        """Instantiate a registered state manager by name."""
        if name not in cls._registry:
            raise ValueError(f"Unknown environment: '{name}'. Registered: {list(cls._registry)}")
        return cls._registry[name](config=config)

    # ── lifecycle methods ───────────────────────────────────────────

    @abstractmethod
    async def setup(self, *, sandbox: BaseSandbox) -> None:
        """Initialize client connections. Called once before any stage runs."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up all resources created during the task."""
