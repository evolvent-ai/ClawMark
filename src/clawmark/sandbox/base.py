"""Base sandbox interface — borrowed from Harbor's BaseEnvironment pattern."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    return_code: int


class BaseSandbox(ABC):
    """Unified sandbox interface for executing commands in an isolated environment."""

    # Map from container port → dynamically assigned host port.
    # Populated by DockerSandbox.start(); DryRunSandbox uses defaults.
    ports: dict[int, int] = {}

    @abstractmethod
    async def start(self) -> None:
        """Start the sandbox environment."""

    @abstractmethod
    async def stop(self, delete: bool = True) -> None:
        """Stop the sandbox. If delete=True, remove all resources."""

    @abstractmethod
    async def exec(self, command: str, timeout_sec: int = 300, env: dict[str, str] | None = None) -> ExecResult:
        """Execute a command inside the sandbox."""

    @abstractmethod
    async def upload_file(self, local_path: Path, remote_path: str) -> None:
        """Copy a file from host into the sandbox."""

    @abstractmethod
    async def upload_dir(self, local_dir: Path, remote_dir: str) -> None:
        """Copy a directory from host into the sandbox."""

    @abstractmethod
    async def download_file(self, remote_path: str, local_path: Path) -> None:
        """Copy a file from sandbox to host."""

    @abstractmethod
    async def download_dir(self, remote_dir: str, local_dir: Path) -> None:
        """Copy a directory from sandbox to host."""
