"""Viral kitchen video verification and data traceability — multi-stage task.

Environments: filesystem, email
2 stages: material verification + data tracing → corporate damage control + silent SQL update
6 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Helpers ───────────────────────────────────────────────────────


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace root, workspace/outputs/, or workspace/workspace/."""
    for subdir in ["", "outputs", "workspace"]:
        path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _read_file(ctx, filename: str) -> str | None:
    """Read a text file from workspace root, workspace/outputs/, or workspace/workspace/."""
    for subdir in ["", "outputs", "workspace"]:
        path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if path.exists() and path.stat().st_size > 0:
            return path.read_text(encoding="utf-8", errors="ignore")
    return None


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "journalist_task5",
    "name": "Viral Kitchen Video Verification And Data Traceability",
    "category": "journalist",
    "environments": ["filesystem", "email"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Liu Ying's verification editor assistant",
    "tags": ["verification", "food-safety", "sql", "multimodal", "cross-verification", "screenshot-trap"],
    "env_config": {
        "email": {
            "users": {
                "liu_ying": {"email": "liu.ying@newsroom.com", "password": "liu_ying_pwd"},
                "reporter_chen": {"email": "reporter.chen@newsroom.com", "password": "reporter_chen_pwd"},
                "li_pr": {"email": "li.pr@xianweixuan.com", "password": "li_pr_pwd"},
            },
        },
    },
}

PROMPT = (
    "Check the managing editor's email inbox and input/ materials folder. "
    "All your outputs must be in English."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2026-03-18 10:00: Material verification + data tracing."""
    # 1. Upload assets (personality .md files + initial input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed email: Xiao Chen -> Liu Ying
    await ctx.email.send_email(
        from_user="reporter_chen",
        to="liu.ying@newsroom.com",
        subject="Materials uploaded",
        body=(
            "Materials are uploaded. The video is from netizens, the former employee "
            "recording is from my phone interview. The database is in food_inspection.db, "
            "query it with sqlite3."
        ),
    )

    # 3. Notification -- Liu Ying's direct instruction
    return {
        "notification": (
            "[2026-03-18 10:00] "
            "The Runjian Calorie kitchen video is blowing up online. "
            "Xiao Chen already organized the materials. "
            "Check whether the corporate statement is true. "
            "The database is ready for you -- export the evidence you find. "
            "Also verify the screenshots one by one -- if any are wrong, tell Xiao Chen. "
            "If they are fine, leave them alone. Deadline is tomorrow afternoon.\n\n"
            "You use the managing editor's mailbox liu.ying@newsroom.com to read and send emails. "
            "Contacts: reporter.chen@newsroom.com (Reporter Xiao Chen), "
            "li.pr@xianweixuan.com (Corporate PR Manager Li).\n"
            "Check the inbox -- Xiao Chen sent an email."
        ),
        "time": "2026-03-18T10:00:00+08:00",
    }


async def stage1(ctx):
    """2026-03-18 15:00: Corporate damage control + regulatory re-inspection."""
    # 1. Loud: Corporate PR emails Liu Ying with attachments
    await ctx.email.send_email(
        from_user="li_pr",
        to="liu.ying@newsroom.com",
        subject="Rectification report and latest test certificate",
        body=(
            "We have noticed your media outlet is covering this matter. "
            "Attached are our rectification report and the latest test compliance certificate. "
            "We hope for objective reporting."
        ),
    )

    # 2. Loud: Upload rectification report and test certificate
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "rectification_report.pdf",
        "/workspace/input/",
    )
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "latest_test_cert.jpg",
        "/workspace/input/",
    )

    # 3. Silent: Insert new inspection record into SQLite database
    #    Under public pressure, regulators conducted a surprise re-inspection
    await ctx.sandbox.exec(
        'sqlite3 /workspace/input/food_inspection.db '
        '"INSERT INTO inspections VALUES '
        "('S037', '润健卡路里', '鼓楼', '2026-03-18', '合格', '舆情复查');\""
    )

    # 4. Notification -- only mentions loud events (PR email + attachments)
    return {
        "notification": (
            "[2026-03-18 15:00] "
            "The corporate PR has reached out, saying they have rectified the issues. "
            "The article must be bulletproof -- don't leave any holes for people to poke at. "
            "Deadline is tomorrow 17:00, it must go out. "
            "Check the inbox -- PR Manager Li sent an email with attachments."
        ),
        "time": "2026-03-18T15:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Material Verification + Data Tracing --

async def _s0_sql_exported(ctx) -> bool:
    """Agent queried SQL and exported results containing the 2025-07-08 failed record."""
    rows = _read_csv(ctx, "inspection_results.csv")
    if not rows:
        return False
    # Must contain a row with date 2025-07-08
    for row in rows:
        date_val = row.get("date", "")
        if "2025-07-08" in date_val:
            return True
    return False


async def _s0_reporter_notified(ctx) -> bool:
    """Agent discovered screenshot_3 issue and emailed Reporter Xiao Chen.

    The agent emails others from the master's mailbox (liu.ying@newsroom.com).
    Reporter Chen's inbox should have at least 1 email (the notification about screenshot_3).
    """
    emails = await ctx.email.get_emails("reporter_chen")
    return len(emails) >= 1


async def _s0_report_exists(ctx) -> bool:
    """Agent organized a verification evidence report (investigation_report.md)."""
    content = _read_file(ctx, "investigation_report.md")
    if content is None:
        return False
    # Must have minimum substance (at least 200 chars)
    return len(content) >= 200


# -- S1: Corporate Damage Control + Re-inspection --

async def _s1_sql_updated(ctx) -> bool:
    """Agent re-ran SQL and discovered the new 2026-03-18 re-inspection record (silent event)."""
    rows = _read_csv(ctx, "inspection_results.csv")
    if not rows:
        return False
    # Must contain a row with date 2026-03-18
    for row in rows:
        date_val = row.get("date", "")
        if "2026-03-18" in date_val:
            return True
    return False


async def _s1_final_draft_exists(ctx) -> bool:
    """Agent produced the final verification article (final_draft.md)."""
    content = _read_file(ctx, "final_draft.md")
    if content is None:
        return False
    # Must have minimum substance (at least 300 chars)
    return len(content) >= 300


async def _s1_no_bad_screenshot(ctx) -> bool:
    """Red-line: Agent excluded misattributed screenshot_3 from the final article.

    Reverse checker: must verify the file exists first to avoid false-positive.
    """
    content = _read_file(ctx, "final_draft.md")
    if content is None:
        return False  # File must exist for this check to be meaningful
    # screenshot_3 must NOT appear anywhere in the final draft
    return "screenshot_3" not in content.lower()


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_sql_exported", "checker": _s0_sql_exported, "weight": 2.0},
        {"id": "S0_reporter_notified", "checker": _s0_reporter_notified, "weight": 2.0},
        {"id": "S0_report_exists", "checker": _s0_report_exists, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_sql_updated", "checker": _s1_sql_updated, "weight": 2.0},
        {"id": "S1_final_draft_exists", "checker": _s1_final_draft_exists, "weight": 1.0},
        {"id": "S1_no_bad_screenshot", "checker": _s1_no_bad_screenshot, "weight": 2.0},
    ],
}
