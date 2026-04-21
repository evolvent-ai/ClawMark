"""ClawMark main entry point."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from .models import TaskResult, StageResult
from .orchestrator import Orchestrator
from .sandbox.docker import DockerSandbox
from .sandbox.dry_run import DryRunSandbox
from .state.composite import CompositeStateManager
from .task_loader import discover_task_dirs, load_task_py

logger = logging.getLogger(__name__)


async def run_task(
    *,
    task_dir: Path,
    model: str,
    api_key: str,
    api_base: str,
    api_format: str = "anthropic",
    compose_file: Path,
    dry_run: bool = False,
    results_dir: Path = Path("results"),
    openclaw_config: Path | None = None,
    model_inputs: list[str] | None = None,
) -> TaskResult:
    """Run a single task end-to-end."""
    start_time = time.time()

    task = load_task_py(task_dir)
    logger.info("Loaded task: %s (%s)", task.name, task.id)

    if dry_run:
        sandbox = DryRunSandbox(workspace_dir=results_dir / task.id / "dryrun_workspace")
    else:
        session_id = f"clawmark-{task.id}-{uuid4().hex[:8]}"
        sandbox = DockerSandbox(
            session_id=session_id,
            compose_file=compose_file,
        )

    state_manager = CompositeStateManager(
        environments=task.environments,
        env_config=task.env_config,
    )
    orchestrator = Orchestrator(
        sandbox=sandbox, state_manager=state_manager,
        openclaw_config_path=openclaw_config,
    )

    local_workspace = results_dir / task.id / "workspace"
    stage_results: list[StageResult] = []
    score = 0.0

    try:
        await sandbox.start()
        await state_manager.setup(sandbox=sandbox)
        ctx = state_manager.create_context(task_dir=task.task_dir, sandbox=sandbox)

        stage_results = await orchestrator.run(
            task=task, ctx=ctx, model=model, api_key=api_key,
            api_base=api_base, api_format=api_format,
            model_inputs=model_inputs,
        )

        # Download final workspace
        await sandbox.download_dir("/workspace", local_workspace)

        # Download agent trace
        trace_remote = f"/root/.openclaw/agents/main/sessions/{orchestrator.session_id}.jsonl"
        trace_local = results_dir / task.id / "messages.jsonl"
        try:
            await sandbox.download_file(trace_remote, trace_local)
            logger.info("Saved agent trace → %s", trace_local)
        except Exception as e:
            logger.warning("Could not download agent trace: %s", e)

    except Exception as e:
        logger.error("Task %s failed: %s", task.id, e, exc_info=True)
        stage_results.append(StageResult(stage_id="FRAMEWORK_ERROR", success=False, error=str(e)))
    finally:
        try:
            await state_manager.cleanup()
        except Exception as e:
            logger.warning("Cleanup error: %s", e)
        await sandbox.stop(delete=True)

    elapsed = time.time() - start_time

    # Calculate score from whatever stage results we have (including partial)
    all_items = [v for sr in stage_results for v in sr.verification]
    total_w = sum(r.weight for r in all_items)
    passed_w = sum(r.weight for r in all_items if r.passed)
    score = passed_w / total_w if total_w > 0 else 0.0

    result = TaskResult(
        task_id=task.id,
        stage_results=stage_results,
        rubric_results=all_items,
        score=score,
        execution_time=elapsed,
    )

    # Print results
    logger.info("=" * 60)
    logger.info("Task: %s", task.name)
    logger.info("Score: %.2f (%d/%d items passed)",
                score,
                sum(1 for r in all_items if r.passed),
                len(all_items))
    for r in all_items:
        status = "✓" if r.passed else "✗"
        logger.info("  %s %s (weight=%.1f) %s", status, r.item_id, r.weight, r.detail or "")
    for s in stage_results:
        if s.verification:
            v_passed = sum(1 for v in s.verification if v.passed)
            logger.info("  Stage %s verification: %d/%d (%.2f)",
                        s.stage_id, v_passed, len(s.verification), s.verification_score)
    logger.info("Stages completed: %d/%d", len(stage_results), len(task.stage_fns))
    logger.info("Time: %.1fs", elapsed)
    logger.info("=" * 60)

    # Save result JSON
    result_file = results_dir / task.id / "result.json"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps({
        "task_id": result.task_id,
        "score": result.score,
        "execution_time": result.execution_time,
        "stages": [{
            "id": s.stage_id, "success": s.success, "error": s.error,
            "verification_score": s.verification_score,
            "verification": [
                {"id": v.item_id, "passed": v.passed, "weight": v.weight,
                 "detail": v.detail, "method": v.method.value}
                for v in s.verification
            ],
        } for s in stage_results],
        "rubric": [
            {"id": r.item_id, "passed": r.passed, "weight": r.weight, "detail": r.detail}
            for r in all_items
        ],
    }, ensure_ascii=False, indent=2))

    return result


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    load_dotenv()

    parser = argparse.ArgumentParser(description="ClawMark — run benchmark tasks")
    parser.add_argument("--task", type=str, help="Single task directory path")
    parser.add_argument("--tasks-dir", type=str, default="tasks", help="Tasks root directory")
    parser.add_argument("--compose-file", type=str, default="docker/docker-compose.yaml")
    parser.add_argument("--results-dir", type=str, default="results")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--openclaw-config", type=str, default=None,
                        help="Path to OpenClaw YAML config (default: configs/openclaw.yaml)")
    parser.add_argument("--model-inputs", nargs="+", choices=["text", "image"],
                        default=["text", "image"],
                        help="Input modalities the model supports (default: text image)")
    args = parser.parse_args()

    args.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    args.api_base = os.environ.get("ANTHROPIC_API_BASE", "https://api.anthropic.com")
    args.model = os.environ.get("MODEL", "claude-sonnet-4-5-20250929")
    args.api_format = os.environ.get("API_FORMAT", "anthropic")

    if not args.api_key:
        parser.error("ANTHROPIC_API_KEY not set in environment or .env")
    if args.api_format not in ("anthropic", "openrouter"):
        parser.error(f"Unsupported API_FORMAT: {args.api_format!r} (expected 'anthropic' or 'openrouter')")

    openclaw_cfg = Path(args.openclaw_config) if args.openclaw_config else None

    # Use model name as subdirectory to avoid overwriting across models
    model_slug = args.model.replace("/", "_")
    results_base = Path(args.results_dir) / model_slug

    if args.task:
        result = asyncio.run(run_task(
            task_dir=Path(args.task),
            model=args.model,
            api_key=args.api_key,
            api_base=args.api_base,
            api_format=args.api_format,
            compose_file=Path(args.compose_file),
            dry_run=args.dry_run,
            results_dir=results_base,
            openclaw_config=openclaw_cfg,
            model_inputs=args.model_inputs,
        ))
        print(f"\nFinal Score: {result.score:.2f}")
    else:
        task_dirs = discover_task_dirs(Path(args.tasks_dir))
        logger.info("Discovered %d tasks", len(task_dirs))
        results = []
        for td in task_dirs:
            try:
                r = asyncio.run(run_task(
                    task_dir=td,
                    model=args.model,
                    api_key=args.api_key,
                    api_base=args.api_base,
                    api_format=args.api_format,
                    compose_file=Path(args.compose_file),
                    dry_run=args.dry_run,
                    results_dir=results_base,
                    openclaw_config=openclaw_cfg,
                    model_inputs=args.model_inputs,
                ))
                results.append(r)
            except Exception as e:
                logger.warning("Skipping task %s: %s", td.name, e)
        if results:
            avg = sum(r.score for r in results) / len(results)
            print(f"\n=== {len(results)} tasks, avg score: {avg:.2f} ===")


if __name__ == "__main__":
    main()
