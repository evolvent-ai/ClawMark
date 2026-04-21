"""Multi-stage orchestrator — drives agent through stages with checker evaluation."""
from __future__ import annotations

import json
import logging
import shlex
import shutil
import uuid
from pathlib import Path
from typing import Any

import yaml

from .context import TaskContext
from .models import (
    EvaluationResult,
    RubricEntry,
    RubricItemResult,
    StageResult,
    TaskDefinition,
)
from .sandbox.base import BaseSandbox, ExecResult
from .state.composite import CompositeStateManager

logger = logging.getLogger(__name__)

_DEFAULT_OPENCLAW_CONFIG = Path(__file__).resolve().parent.parent.parent / "configs" / "openclaw.yaml"


def _load_openclaw_template(path: Path | None = None) -> dict[str, Any]:
    """Load the OpenClaw config template from YAML."""
    config_path = path or _DEFAULT_OPENCLAW_CONFIG
    if config_path.exists():
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return {}


class Orchestrator:
    def __init__(
        self,
        sandbox: BaseSandbox,
        state_manager: CompositeStateManager,
        openclaw_config_path: Path | None = None,
    ):
        self.sandbox = sandbox
        self.state = state_manager
        self.session_id = f"clawmark-{uuid.uuid4().hex[:8]}"
        self._openclaw_config_path = openclaw_config_path

    async def run(
        self,
        *,
        task: TaskDefinition,
        ctx: TaskContext,
        model: str,
        api_key: str,
        api_base: str,
        api_format: str = "anthropic",
        model_inputs: list[str] | None = None,
    ) -> list[StageResult]:
        results: list[StageResult] = []
        temp_dirs: list[Path] = []

        await self._setup_openclaw_config(
            model=model, api_key=api_key, api_base=api_base, api_format=api_format,
            model_inputs=model_inputs,
        )
        await self._setup_skills()

        try:
            for i, stage_fn in enumerate(task.stage_fns):
                stage_id = f"stage{i}"

                try:
                    ret = await stage_fn(ctx)
                    notification = self._parse_notification(ret)

                    if i == 0:
                        notification = task.prompt + "\n\n" + notification

                    agent_result = await self._send_to_agent(
                        message=notification, timeout_sec=task.timeout_seconds,
                    )

                    # Download workspace snapshot
                    ws_snapshot = Path(f"/tmp/clawmark-ws-{stage_id}-{uuid.uuid4().hex[:6]}")
                    await self.sandbox.download_dir("/workspace", ws_snapshot)
                    temp_dirs.append(ws_snapshot)
                    ctx.workspace = ws_snapshot
                    ctx.snapshots[stage_id] = ws_snapshot

                    # Run stage checkers
                    stage_entries = task.rubric.get(stage_id, [])
                    verification = await self._run_checkers(stage_entries, ctx)

                    results.append(StageResult(
                        stage_id=stage_id,
                        agent_output=agent_result.stdout,
                        success=agent_result.return_code == 0,
                        error=agent_result.stderr if agent_result.return_code != 0 else "",
                        verification=verification.results,
                        verification_score=verification.score,
                    ))
                except Exception as e:
                    logger.error("Stage %s failed: %s", stage_id, e, exc_info=True)
                    results.append(StageResult(stage_id=stage_id, success=False, error=str(e)))
                    break

            # Run final checkers (even if a stage failed)
            final_entries = task.rubric.get("final", [])
            if final_entries:
                final_verification = await self._run_checkers(final_entries, ctx)
                results.append(StageResult(
                    stage_id="final",
                    verification=final_verification.results,
                    verification_score=final_verification.score,
                ))
        finally:
            for d in temp_dirs:
                shutil.rmtree(d, ignore_errors=True)

        return results

    async def _run_checkers(
        self, entries: list[RubricEntry], ctx: TaskContext,
    ) -> EvaluationResult:
        """Run checker functions and compute weighted score."""
        results: list[RubricItemResult] = []
        for entry in entries:
            try:
                passed = bool(await entry.checker(ctx))
            except Exception as e:
                logger.error("Checker '%s' raised: %s", entry.id, e)
                passed = False
            results.append(RubricItemResult(
                item_id=entry.id,
                passed=passed,
                weight=entry.weight,
            ))

        total = sum(r.weight for r in results)
        passed_w = sum(r.weight for r in results if r.passed)
        score = passed_w / total if total > 0 else 0.0
        return EvaluationResult(results=results, score=score)

    @staticmethod
    def _parse_notification(ret) -> str:
        """Extract notification string from stage function return value."""
        if isinstance(ret, str):
            return ret
        if isinstance(ret, dict):
            msg = ret.get("notification", "")
            time_str = ret.get("time", "")
            if time_str:
                msg += f"\n（当前时间：{time_str}）"
            return msg
        return str(ret)

    # ── OpenClaw setup ──────────────────────────────────────────────

    async def _setup_openclaw_config(
        self, *, model: str, api_key: str, api_base: str, api_format: str = "anthropic",
        model_inputs: list[str] | None = None,
    ) -> None:
        """Build OpenClaw config from YAML template + runtime values, write into container."""
        inputs = model_inputs or ["text", "image"]
        config = _load_openclaw_template(self._openclaw_config_path)

        # Build provider block from runtime args
        if api_format == "openrouter":
            api_type = "openai-completions"
            provider_config = {
                "baseUrl": api_base,
                "apiKey": api_key,
                "api": api_type,
                "models": [{
                    "id": model,
                    "name": "Bench Model",
                    "api": api_type,
                    "reasoning": True,
                    "input": inputs,
                    "contextWindow": 200000,
                    "maxTokens": 16384,
                }],
            }
        else:
            api_type = "anthropic-messages"
            provider_config = {
                "baseUrl": api_base,
                "apiKey": api_key,
                "auth": "api-key",
                "api": api_type,
                "models": [{
                    "id": model,
                    "name": "Bench Model",
                    "api": api_type,
                    "reasoning": True,
                    "input": inputs,
                    "contextWindow": 200000,
                    "maxTokens": 16384,
                }],
            }

        # Merge provider into config
        config.setdefault("models", {}).setdefault("providers", {})["bench"] = provider_config

        # Set model reference in agent defaults
        config.setdefault("agents", {}).setdefault("defaults", {})["model"] = {
            "primary": f"bench/{model}",
        }

        config_json = json.dumps(config, indent=2)
        await self.sandbox.exec("mkdir -p /root/.openclaw")
        await self.sandbox.exec(
            f"cat > /root/.openclaw/openclaw.json << 'CLAWEOF'\n{config_json}\nCLAWEOF"
        )
        logger.info("Configured OpenClaw: model=%s api_format=%s", model, api_format)

        # Patch OpenClaw to disable tool call ID sanitization for openai-completions.
        # Some models (e.g. Kimi) generate tool_call_ids that their API server expects
        # verbatim; OpenClaw's strict sanitization rewrites them and causes mismatches.
        if api_format == "openrouter":
            target = "/usr/lib/node_modules/openclaw/dist/pi-embedded-iRgRpYxO.js"
            await self.sandbox.exec(
                f"sed -i 's/const requiresOpenAiCompatibleToolIdSanitization = params\\.modelApi/const requiresOpenAiCompatibleToolIdSanitization = false \\&\\& params.modelApi/' {target}"
            )
            logger.info("Patched OpenClaw: disabled tool call ID sanitization")

    async def _setup_skills(self, env_vars: dict[str, str] | None = None) -> None:
        """Copy all skills into the container, replacing $VAR placeholders with real values."""
        skills_dir = Path(__file__).resolve().parent.parent.parent / "skills"
        if not skills_dir.is_dir():
            return

        # Collect env values for substitution (from os.environ + explicit overrides)
        import os
        import tempfile
        subs = dict(os.environ)
        if env_vars:
            subs.update(env_vars)

        await self.sandbox.exec("mkdir -p /root/.openclaw/skills")
        for skill_path in skills_dir.iterdir():
            if not skill_path.is_dir() or not (skill_path / "SKILL.md").exists():
                continue

            # Copy skill to a temp dir, replace placeholders in SKILL.md
            with tempfile.TemporaryDirectory() as tmp:
                tmp_skill = Path(tmp) / skill_path.name
                shutil.copytree(skill_path, tmp_skill)

                skill_md = tmp_skill / "SKILL.md"
                content = skill_md.read_text(encoding="utf-8")
                for key, val in subs.items():
                    content = content.replace(f"${key}", val)
                    content = content.replace(f"${{{key}}}", val)
                skill_md.write_text(content, encoding="utf-8")

                await self.sandbox.upload_dir(tmp_skill, f"/root/.openclaw/skills/{skill_path.name}")
            logger.info("Injected skill: %s", skill_path.name)

    async def _send_to_agent(self, *, message: str, timeout_sec: int) -> ExecResult:
        msg_escaped = shlex.quote(message)
        cmd = (
            f"openclaw agent --local"
            f" --session-id {self.session_id}"
            f" --message {msg_escaped}"
            f" --json"
            f" --timeout {timeout_sec}"
        )
        logger.info("Sending to agent session=%s (%d chars)", self.session_id, len(message))
        return await self.sandbox.exec(cmd, timeout_sec=timeout_sec + 60)
