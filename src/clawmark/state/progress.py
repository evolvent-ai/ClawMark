"""Live progress display for parallel state manager operations using rich."""
from __future__ import annotations

import logging
import time

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text


class ProgressDisplay:
    """Fixed-line terminal display for parallel service operations."""

    def __init__(self, services: list[str], phase: str = "setup") -> None:
        self.services = services
        self.phase = phase
        self._status: dict[str, str] = {s: "pending" for s in services}
        self._messages: dict[str, str] = {s: "waiting..." for s in services}
        self._start: dict[str, float] = {}
        self._elapsed: dict[str, float] = {}
        self._handler: _ProgressLogHandler | None = None
        self._live: Live | None = None
        self._console = Console(stderr=True)
        self._suppressed_handlers: list[tuple[logging.Handler, int]] = []

    def start(self) -> None:
        # Intercept state manager logs
        state_logger = logging.getLogger("clawmark.state")
        self._handler = _ProgressLogHandler(self)
        state_logger.addHandler(self._handler)
        self._prev_propagate = state_logger.propagate
        state_logger.propagate = False

        # Suppress ALL root handler output to avoid messing up Live display
        root = logging.getLogger()
        for h in root.handlers:
            self._suppressed_handlers.append((h, h.level))
            h.setLevel(logging.CRITICAL + 1)

        self._live = Live(self._render(), console=self._console, refresh_per_second=8)
        self._live.start()

    def stop(self) -> None:
        if self._live:
            self._live.update(self._render())
            self._live.stop()
            self._live = None

        # Restore state logger
        state_logger = logging.getLogger("clawmark.state")
        if self._handler:
            state_logger.removeHandler(self._handler)
            self._handler = None
        state_logger.propagate = getattr(self, "_prev_propagate", True)

        # Restore root handlers
        for h, level in self._suppressed_handlers:
            h.setLevel(level)
        self._suppressed_handlers.clear()

    def mark_running(self, service: str) -> None:
        self._status[service] = "running"
        self._start[service] = time.monotonic()
        self._messages[service] = f"{self.phase}..."
        self._refresh()

    def mark_done(self, service: str) -> None:
        self._status[service] = "ok"
        self._elapsed[service] = time.monotonic() - self._start.get(service, time.monotonic())
        self._messages[service] = f"ok ({self._elapsed[service]:.1f}s)"
        self._refresh()

    def mark_error(self, service: str, error: str) -> None:
        self._status[service] = "error"
        self._elapsed[service] = time.monotonic() - self._start.get(service, time.monotonic())
        short = error[:60] + "..." if len(error) > 60 else error
        self._messages[service] = f"FAILED ({self._elapsed[service]:.1f}s) {short}"
        self._refresh()

    def on_log(self, service: str, message: str) -> None:
        if self._status.get(service) == "running":
            self._messages[service] = message[:80]
            self._refresh()

    def _refresh(self) -> None:
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Table:
        table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
        table.add_column(style="bold", no_wrap=True)
        table.add_column(no_wrap=True, width=2)
        table.add_column(no_wrap=True)

        for svc in self.services:
            status = self._status.get(svc, "pending")
            msg = self._messages.get(svc, "")

            if status == "ok":
                icon = Text("✓", style="bold green")
                detail = Text(msg, style="green")
            elif status == "error":
                icon = Text("✗", style="bold red")
                detail = Text(msg, style="red")
            elif status == "running":
                icon = Text("⟳", style="bold yellow")
                detail = Text(msg, style="dim")
            else:
                icon = Text("⏳", style="dim")
                detail = Text(msg, style="dim")

            table.add_row(Text(f"[{svc}]", style="bold"), icon, detail)

        return table


class _ProgressLogHandler(logging.Handler):
    """Intercepts log messages from state manager sub-packages."""

    _PREFIX = "clawmark.state."

    def __init__(self, display: ProgressDisplay) -> None:
        super().__init__()
        self.display = display

    def emit(self, record: logging.LogRecord) -> None:
        name = record.name
        if not name.startswith(self._PREFIX):
            return
        rest = name[len(self._PREFIX):]
        service = rest.split(".")[0]
        if service in self.display.services:
            self.display.on_log(service, record.getMessage())
