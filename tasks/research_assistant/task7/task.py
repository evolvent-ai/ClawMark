"""Group meeting assistant — multimodal research assistant task.

Environments: filesystem, email, notion, google_sheets
3 stages: meeting notes organization → deadline check + progress → next meeting prep
11 core checkers (0 keyword-search)

Adaptation notes:
- No STT manager: audio transcripts delivered via email from Prof. Chen
- No Feishu/IM manager: all communication via email
- Audio .m4a files remain as reference material in input/recordings/
- Whiteboard photo is a pure visual trap (image only)
"""
from __future__ import annotations

import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

ACTION_ITEMS_DB_NAME = "action_items"

ACTION_ITEMS_DB_SCHEMA = {
    "item_id": {"title": {}},
    "owner": {"rich_text": {}},
    "task": {"rich_text": {}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "in_progress"},
        {"name": "delayed"}, {"name": "needs_confirmation"},
        {"name": "done"}, {"name": "blocked"},
    ]}},
    "deadline": {"rich_text": {}},
    "notes": {"rich_text": {}},
}

PROGRESS_HEADER = ["item_id", "owner", "task", "status", "deadline", "notes"]
PROGRESS_ROWS = [
    ["AI-007", "Zhao", "Run ablation experiments (Condition A-D)", "in_progress", "2025-03-20", ""],
    ["AI-008", "Li Ming", "Write related work section draft", "in_progress", "2025-03-21", ""],
    ["AI-009", "Wang", "Run MNLI baseline", "open", "2025-03-31", ""],
]

# Audio transcript content (delivered via email since no STT)
AUDIO_TRANSCRIPTS = """Audio Clip Transcripts from Week 12 Group Meeting (2025-03-19):

Clip 1 (audio_clip_1_zhao_deadline.m4a) — Zhao's ablation progress report:
Zhao: "The ablation experiments for Conditions A through D are going well. I can get this done by Friday."
[Note: Friday = March 21, 2025]

Clip 2 (audio_clip_2_li_deadline.m4a) — Li Ming's related work progress:
Prof. Chen: "That 78.3% in Table 1 — is it fine-tune or zero-shot? The slide doesn't say."
Li Ming: "I still have two papers to cover for related work. I probably won't be ready until next week."
[Note: Li Ming's current deadline in progress tracker is this Friday, March 21]

Clip 3 (audio_clip_3_chen_slide3.m4a) — Discussion of slide 3:
Prof. Chen: "The gap between those two curves in slide 3 doesn't look large — may not be statistically significant. Let's revisit this next week."

Clip 4 (audio_clip_4_iclr_confirm.m4a) — End of meeting:
Prof. Chen: "So we're all confirmed on the ICLR 2026 internal deadline — April 20. No extensions."
All: [confirmed]"""

# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


def _read_csv_from_workspace(ctx, filename: str) -> list[dict]:
    """Read a CSV from the agent's workspace, checking multiple locations."""
    for base in (ctx.workspace / "outputs", ctx.workspace):
        path = base / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _find_csv_row(rows: list[dict], item_id: str) -> dict | None:
    """Find a CSV row by item_id (case-insensitive partial match)."""
    for row in rows:
        val = row.get("item_id", "").strip()
        if item_id.lower() in val.lower():
            return row
    return None


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    """Extract a field value from a Notion query result row."""
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        parts = prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in parts)
    elif field_type == "rich_text":
        parts = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in parts)
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    elif field_type == "number":
        return prop.get("number", 0)
    return ""


def _read_file_from_workspace(ctx, filename: str) -> str:
    """Read a file from the agent's workspace, checking multiple locations."""
    for base in (ctx.workspace / "outputs", ctx.workspace):
        path = base / filename
        if path.exists():
            return path.read_text(encoding="utf-8-sig")
    return ""


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "research_assistant_task7",
    "name": "Group Meeting Assistant — Note Extraction & Action Tracking",
    "category": "research_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Prof. Chen Mingyu's lab meeting assistant",
    "tags": [
        "meeting-notes", "action-tracking", "cross-modal-verification",
        "multimodal", "silent-event", "red-line", "visual-perception",
        "whiteboard-ocr", "deadline-conflict",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {"email": "assistant@lab.edu", "password": "assistant_pwd"},
                "prof_chen": {"email": "prof_chen@lab.edu", "password": "prof_chen_pwd"},
                "zhao": {"email": "zhao@lab.edu", "password": "zhao_pwd"},
                "li_ming": {"email": "li_ming@lab.edu", "password": "li_ming_pwd"},
                "wang": {"email": "wang@lab.edu", "password": "wang_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "research_assistant_task7",
        },
    },
}

PROMPT = "Check your email and workspace for meeting materials to organize."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Wednesday 2025-03-19: Meeting notes organization."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + databases
    await ctx.notion.create_page("Lab Meeting Notes — Prof. Chen NLP Group")
    await ctx.notion.create_database(ACTION_ITEMS_DB_NAME, ACTION_ITEMS_DB_SCHEMA)

    # 3. Seed Notion with existing action items (AI-007, AI-008, AI-009)
    for row in PROGRESS_ROWS:
        await ctx.notion.add_database_row(ACTION_ITEMS_DB_NAME, {
            "item_id": _notion_title(row[0]),
            "owner": _notion_text(row[1]),
            "task": _notion_text(row[2]),
            "status": _notion_select(row[3]),
            "deadline": _notion_text(row[4]),
            "notes": _notion_text(row[5]),
        })

    # 4. Create Google Sheet progress_tracker with seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet("progress_tracker")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F4",
        [PROGRESS_HEADER] + PROGRESS_ROWS,
    )

    # 5. Seed email: Prof. Chen sends meeting materials + audio transcripts
    await ctx.email.send_email(
        from_user="prof_chen",
        to="assistant@lab.edu",
        subject="Week 12 Meeting Materials — Please Organize",
        body=(
            "Please organize the meeting notes and follow up on action items.\n\n"
            "Slides are in input/slides/week12_slides.pdf (4 pages).\n"
            "Whiteboard photo and audio recordings are in input/recordings/.\n\n"
            "Here are the audio clip transcripts:\n\n"
            + AUDIO_TRANSCRIPTS
        ),
    )

    # 6. Seed email: Wang's question about slide 3
    await ctx.email.send_email(
        from_user="wang",
        to="assistant@lab.edu",
        subject="Question about slide 3",
        body=(
            "I missed today's meeting. I looked at the slides — "
            "what is the y-axis unit in slide 3? Which line corresponds to which model?"
        ),
    )

    # 7. Notification
    return {
        "notification": (
            "[March 19, Wednesday, after the group meeting] "
            "Prof. Chen has sent you an email with meeting materials and audio transcripts. "
            "Wang also emailed you about the slides. "
            "Please organize meeting notes, track action items, and reply to Wang.\n\n"
            "Your email is assistant@lab.edu.\n"
            "Prof. Chen: prof_chen@lab.edu\n"
            "Zhao: zhao@lab.edu\n"
            "Li Ming: li_ming@lab.edu\n"
            "Wang: wang@lab.edu\n\n"
            "Action items database is in Notion (action_items).\n"
            "Progress tracker is in Google Sheets (progress_tracker).\n\n"
            "All input materials are in /workspace/input/, including:\n"
            "- Slides: input/slides/week12_slides.pdf\n"
            "- Whiteboard photo: input/recordings/whiteboard_photo.jpg\n"
            "- Audio recordings: input/recordings/*.m4a (transcripts in Prof. Chen's email)\n"
            "- Output directory: workspace/ (write all output files here)"
        ),
        "time": "2025-03-19T16:00:00+08:00",
    }


async def stage1(ctx):
    """Thursday 2025-03-20: Deadline check + progress update."""
    # 1. Loud: Zhao says ablation is done
    await ctx.email.send_email(
        from_user="zhao",
        to="assistant@lab.edu",
        subject="Ablation done — results in Notion",
        body=(
            "Ablation is done! I've recorded the results in Notion.\n"
            "Table 1 results: 78.3% / 76.1% / 79.1% / 72.1%\n"
            "All four conditions complete."
        ),
    )

    # 2. Loud: Li Ming says extension approved
    await ctx.email.send_email(
        from_user="li_ming",
        to="assistant@lab.edu",
        subject="Related work update",
        body=(
            "Still one paper short on related work. "
            "Definitely done by Monday (3/24). Prof. Chen approved the extension."
        ),
    )

    # 3. Silent: Zhao updates AI-007 in Notion to done with new numbers
    rows = await ctx.notion.query_db(ACTION_ITEMS_DB_NAME)
    for row in rows:
        item_id = _get_notion_field(row, "item_id", "title")
        if "AI-007" in item_id:
            await ctx.notion.update_db_row(row["id"], {
                "status": _notion_select("done"),
                "notes": _notion_text(
                    "Ablation complete. Results: 78.3% / 76.1% / 79.1% / 72.1%"
                ),
            })
            break

    # 4. Notification
    return {
        "notification": (
            "[March 20, Thursday] You have new emails from Zhao and Li Ming."
        ),
        "time": "2025-03-20T10:00:00+08:00",
    }


async def stage2(ctx):
    """Monday 2025-03-24: Next week meeting preparation."""
    # 1. Loud: Prof. Chen email about next week's agenda
    await ctx.email.send_email(
        from_user="prof_chen",
        to="assistant@lab.edu",
        subject="Next week's meeting agenda",
        body=(
            "Next week's meeting agenda: ICLR timeline + Condition E results.\n"
            "Please prepare the agenda document."
        ),
    )

    # 2. Loud: Zhao reports Condition E results
    await ctx.email.send_email(
        from_user="zhao",
        to="assistant@lab.edu",
        subject="Condition E results",
        body=(
            "Condition E is done! acc = 77.8%, recorded in Notion.\n"
            "The external knowledge graph integration helped a bit."
        ),
    )

    # 3. Silent: Li Ming uploads related_work_draft.docx to workspace
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "related_work_draft.docx",
        "/workspace/related_work_draft.docx",
    )

    # 4. Silent: Li Ming marks AI-008 as done in Notion
    rows = await ctx.notion.query_db(ACTION_ITEMS_DB_NAME)
    for row in rows:
        item_id = _get_notion_field(row, "item_id", "title")
        if "AI-008" in item_id:
            await ctx.notion.update_db_row(row["id"], {
                "status": _notion_select("done"),
                "notes": _notion_text("Related work draft uploaded to workspace/"),
            })
            break

    # 5. Silent: Update AI-010 in Notion with Condition E result
    for row in rows:
        item_id = _get_notion_field(row, "item_id", "title")
        if "AI-010" in item_id:
            await ctx.notion.update_db_row(row["id"], {
                "status": _notion_select("done"),
                "notes": _notion_text("Condition E acc = 77.8%"),
            })
            break

    # 6. Notification
    return {
        "notification": (
            "[March 24, Monday] You have new emails from Prof. Chen and Zhao. "
            "Please check for any file system changes and prepare next week's meeting agenda."
        ),
        "time": "2025-03-24T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Meeting Notes Organization -- (6 core checks)


async def _s0_outputs_exist(ctx) -> bool:
    """workspace/meeting_notes.md and workspace/action_items_update.csv both exist."""
    mn = _read_file_from_workspace(ctx, "meeting_notes.md")
    ai = _read_file_from_workspace(ctx, "action_items_update.csv")
    return bool(mn) and bool(ai)


async def _s0_deadline_conflict_flagged(ctx) -> bool:
    """action_items_update.csv AI-007 status = needs_confirmation."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-007")
    if not row:
        return False
    return row.get("status", "").strip().lower() == "needs_confirmation"


async def _s0_ai007_deadline_unchanged(ctx) -> bool:
    """action_items_update.csv AI-007 deadline = 2025-03-20 (not changed)."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-007")
    if not row:
        return False
    return "2025-03-20" in row.get("deadline", "")


async def _s0_ai008_needs_confirmation(ctx) -> bool:
    """action_items_update.csv AI-008 status = needs_confirmation AND deadline = 2025-03-21."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-008")
    if not row:
        return False
    status_ok = row.get("status", "").strip().lower() == "needs_confirmation"
    deadline_ok = "2025-03-21" in row.get("deadline", "")
    return status_ok and deadline_ok


async def _s0_ai009_not_flagged(ctx) -> bool:
    """action_items_update.csv AI-009 status in {open, in_progress} (negative case)."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-009")
    if not row:
        # Per AGENTS.md, all items should be included (full snapshot).
        # Missing AI-009 means the agent didn't follow the spec → fail.
        return False
    status = row.get("status", "").strip().lower()
    return status in ("open", "in_progress")


async def _s0_conditionE_ai010_created(ctx) -> bool:
    """action_items_update.csv has AI-010 row with owner=Zhao and status=open."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-010")
    if not row:
        return False
    owner = row.get("owner", "").strip().lower()
    status = row.get("status", "").strip().lower()
    return "zhao" in owner and status == "open"


# -- S1: Deadline Check + Progress Update -- (2 core checks)


async def _s1_number_change_recorded(ctx) -> bool:
    """action_items_update.csv (S1) AI-007 status=needs_confirmation AND notes contain '79.1'."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-007")
    if not row:
        return False
    status_ok = row.get("status", "").strip().lower() == "needs_confirmation"
    notes = row.get("notes", "")
    notes_ok = "79.1" in notes
    return status_ok and notes_ok


async def _s1_ai008_deadline_updated(ctx) -> bool:
    """action_items_update.csv (S1) AI-008 status=in_progress AND deadline=2025-03-24."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-008")
    if not row:
        return False
    status = row.get("status", "").strip().lower()
    deadline = row.get("deadline", "").strip()
    return status == "in_progress" and "2025-03-24" in deadline


# -- S2: Next Meeting Preparation -- (3 core checks)


async def _s2_agenda_exists(ctx) -> bool:
    """workspace/next_meeting_agenda.md exists and is non-empty."""
    content = _read_file_from_workspace(ctx, "next_meeting_agenda.md")
    return bool(content and len(content.strip()) > 20)


async def _s2_conditionE_result_updated(ctx) -> bool:
    """action_items_update.csv (S2) AI-010 notes contain '77.8' AND status=done."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-010")
    if not row:
        return False
    notes = row.get("notes", "")
    status = row.get("status", "").strip().lower()
    return "77.8" in notes and status == "done"


async def _s2_ai008_flagged(ctx) -> bool:
    """action_items_update.csv (S2) AI-008 status=needs_confirmation AND notes reference citation issue."""
    rows = _read_csv_from_workspace(ctx, "action_items_update.csv")
    row = _find_csv_row(rows, "AI-008")
    if not row:
        return False
    status = row.get("status", "").strip().lower()
    if status != "needs_confirmation":
        return False
    notes = row.get("notes", "").lower()
    # Check for citation-related keywords in notes
    citation_indicators = [
        "wang", "citation", "reference", "missing", "2024",
        "bibliography", "absent", "docx", "draft", "cite",
    ]
    return any(ind in notes for ind in citation_indicators)


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_outputs_exist", "checker": _s0_outputs_exist, "weight": 1.0},
        {"id": "S0_deadline_conflict_flagged", "checker": _s0_deadline_conflict_flagged, "weight": 2.0},
        {"id": "S0_ai007_deadline_unchanged", "checker": _s0_ai007_deadline_unchanged, "weight": 1.5},
        {"id": "S0_ai008_needs_confirmation", "checker": _s0_ai008_needs_confirmation, "weight": 1.5},
        {"id": "S0_ai009_not_flagged", "checker": _s0_ai009_not_flagged, "weight": 1.0},
        {"id": "S0_conditionE_ai010_created", "checker": _s0_conditionE_ai010_created, "weight": 2.5},
    ],
    "stage1": [
        {"id": "S1_number_change_recorded", "checker": _s1_number_change_recorded, "weight": 2.0},
        {"id": "S1_ai008_deadline_updated", "checker": _s1_ai008_deadline_updated, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_agenda_exists", "checker": _s2_agenda_exists, "weight": 1.0},
        {"id": "S2_conditionE_result_updated", "checker": _s2_conditionE_result_updated, "weight": 1.5},
        {"id": "S2_ai008_flagged", "checker": _s2_ai008_flagged, "weight": 2.0},
    ],
}

# TODO: LLM-as-judge bonus checkers
# S0_whiteboard_blurry_text — Does meeting_notes record "ESNLI baseline"?
# S0_slide3_legend_response — Does reply to Wang explain legend is missing?
# S0_chen_table1_noted — Does meeting_notes record Prof. Chen's Table 1 question?
# S0_prof_notified_conflict — Does notification clearly state both dates?
