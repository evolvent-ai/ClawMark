"""Docker Compose sandbox — sleep infinity + docker compose exec."""
from __future__ import annotations

import asyncio
import logging
import shlex
from pathlib import Path

from .base import BaseSandbox, ExecResult

logger = logging.getLogger(__name__)


async def _async_run(cmd: str, timeout: int = 300) -> ExecResult:
    """Run a shell command asynchronously."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return ExecResult(stdout="", stderr=f"Timeout after {timeout}s", return_code=-1)
    return ExecResult(
        stdout=stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
        return_code=proc.returncode or 0,
    )


class DockerSandbox(BaseSandbox):
    """Docker Compose sandbox using sleep infinity + exec pattern."""

    def __init__(self, session_id: str, compose_file: Path):
        self.session_id = session_id
        self.compose_file = compose_file

    def _compose_cmd(self, subcmd: str) -> str:
        return f"docker compose -p {self.session_id} -f {self.compose_file} {subcmd}"

    def _container_name(self) -> str:
        return f"{self.session_id}-main-1"

    async def start(self) -> None:
        logger.info("Starting sandbox %s", self.session_id)
        result = await _async_run(self._compose_cmd("up -d --wait --build"), timeout=300)
        if result.return_code != 0:
            raise RuntimeError(f"Failed to start sandbox: {result.stderr}")

        # Read dynamically assigned host ports
        self.ports = {}
        for service, container_port in [
            ("greenmail", 3025), ("greenmail", 3143),
            ("greenmail", 8080), ("radicale", 5232),
        ]:
            port_result = await _async_run(
                self._compose_cmd(f"port {service} {container_port}"),
            )
            if port_result.return_code == 0 and port_result.stdout.strip():
                try:
                    host_port = int(port_result.stdout.strip().split(":")[-1])
                    self.ports[container_port] = host_port
                except (ValueError, IndexError):
                    logger.warning("Could not parse port for %s:%d", service, container_port)

        logger.info("Sandbox started: %s (ports: %s)", self.session_id, self.ports)

    async def stop(self, delete: bool = True) -> None:
        logger.info("Stopping sandbox %s", self.session_id)
        cmd = self._compose_cmd("down" + (" -v --remove-orphans" if delete else ""))
        await _async_run(cmd, timeout=60)

    async def exec(self, command: str, timeout_sec: int = 300, env: dict[str, str] | None = None) -> ExecResult:
        env_flags = ""
        if env:
            env_flags = " ".join(f"-e {k}={shlex.quote(v)}" for k, v in env.items()) + " "
        cmd = self._compose_cmd(f"exec -T {env_flags}main bash -c {shlex.quote(command)}")
        result = await _async_run(cmd, timeout=timeout_sec)
        if result.return_code != 0 and result.stderr:
            logger.debug("exec stderr: %s", result.stderr[:500])
        return result

    async def upload_file(self, local_path: Path, remote_path: str) -> None:
        await _async_run(f"docker cp {local_path} {self._container_name()}:{remote_path}")

    async def upload_dir(self, local_dir: Path, remote_dir: str) -> None:
        # Ensure remote dir exists, then copy contents
        await self.exec(f"mkdir -p {remote_dir}")
        await _async_run(f"docker cp {local_dir}/. {self._container_name()}:{remote_dir}")

    async def download_file(self, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        await _async_run(f"docker cp {self._container_name()}:{remote_path} {local_path}")

    async def download_dir(self, remote_dir: str, local_dir: Path) -> None:
        local_dir.mkdir(parents=True, exist_ok=True)
        await _async_run(f"docker cp {self._container_name()}:{remote_dir}/. {local_dir}")
