import asyncio
import importlib.util
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path


def _load_orchestrator_module():
    root = Path(__file__).resolve().parent.parent
    src_root = root / "src"

    clawmark_pkg = types.ModuleType("clawmark")
    clawmark_pkg.__path__ = [str(src_root / "clawmark")]
    sys.modules.setdefault("clawmark", clawmark_pkg)

    context_mod = types.ModuleType("clawmark.context")
    context_mod.TaskContext = object
    sys.modules["clawmark.context"] = context_mod

    models_mod = types.ModuleType("clawmark.models")
    for name in [
        "EvaluationResult",
        "RubricEntry",
        "RubricItemResult",
        "StageResult",
        "TaskDefinition",
    ]:
        setattr(models_mod, name, type(name, (), {}))
    sys.modules["clawmark.models"] = models_mod

    state_pkg = types.ModuleType("clawmark.state")
    state_pkg.__path__ = []
    sys.modules["clawmark.state"] = state_pkg

    state_composite_mod = types.ModuleType("clawmark.state.composite")
    state_composite_mod.CompositeStateManager = type("CompositeStateManager", (), {})
    sys.modules["clawmark.state.composite"] = state_composite_mod

    sandbox_pkg = types.ModuleType("clawmark.sandbox")
    sandbox_pkg.__path__ = [str(src_root / "clawmark" / "sandbox")]
    sys.modules["clawmark.sandbox"] = sandbox_pkg

    sandbox_base_path = src_root / "clawmark" / "sandbox" / "base.py"
    sandbox_base_spec = importlib.util.spec_from_file_location(
        "clawmark.sandbox.base", sandbox_base_path
    )
    assert sandbox_base_spec and sandbox_base_spec.loader
    sandbox_base_mod = importlib.util.module_from_spec(sandbox_base_spec)
    sys.modules["clawmark.sandbox.base"] = sandbox_base_mod
    sandbox_base_spec.loader.exec_module(sandbox_base_mod)

    orch_path = src_root / "clawmark" / "orchestrator.py"
    orch_spec = importlib.util.spec_from_file_location("clawmark.orchestrator", orch_path)
    assert orch_spec and orch_spec.loader
    orch_mod = importlib.util.module_from_spec(orch_spec)
    sys.modules["clawmark.orchestrator"] = orch_mod
    orch_spec.loader.exec_module(orch_mod)
    return orch_mod


orchestrator_mod = _load_orchestrator_module()
Orchestrator = orchestrator_mod.Orchestrator
ExecResult = sys.modules["clawmark.sandbox.base"].ExecResult


@dataclass
class _FakeSandbox:
    exec_calls: list[str] = field(default_factory=list)
    uploaded_dirs: list[tuple[Path, str]] = field(default_factory=list)

    async def start(self) -> None:
        return None

    async def stop(self, delete: bool = True) -> None:
        return None

    async def exec(self, command: str, timeout_sec: int = 300, env=None) -> ExecResult:
        self.exec_calls.append(command)
        if command == "command -v mcporter >/dev/null 2>&1":
            return ExecResult(stdout="", stderr="", return_code=0)
        return ExecResult(stdout="", stderr="", return_code=0)

    async def upload_file(self, local_path: Path, remote_path: str) -> None:
        return None

    async def upload_dir(self, local_dir: Path, remote_dir: str) -> None:
        self.uploaded_dirs.append((local_dir, remote_dir))

    async def download_file(self, remote_path: str, local_path: Path) -> None:
        return None

    async def download_dir(self, remote_dir: str, local_dir: Path) -> None:
        return None


def test_setup_skills_preconfigures_notion_mcporter_server() -> None:
    sandbox = _FakeSandbox()
    orch = Orchestrator(sandbox=sandbox, state_manager=None)

    asyncio.run(orch._setup_skills({"NOTION_AGENT_KEY": "ntn_test_token"}))

    joined = "\n".join(sandbox.exec_calls)
    assert "command -v mcporter >/dev/null 2>&1" in joined
    assert "mcporter config add notion --scope home" in joined
    assert "@notionhq/notion-mcp-server" in joined
    assert "ntn_test_token" in joined
