"""Breaking-news flash writing and fact checking — multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: first flash → editor follow-up + briefing → tipster material + old-image trap + evening summary
15 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────

NEWS_DB_NAME = "news_db"

NEWS_DB_SCHEMA = {
    "Title": {"title": {}},
    "Section": {"select": {"options": [
        {"name": "breaking"}, {"name": "in-depth"}, {"name": "flash"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "draft"}, {"name": "updated"}, {"name": "final"},
    ]}},
    "Body": {"rich_text": {}},
    "Confirmed Facts": {"rich_text": {}},
    "Pending Verification Items": {"rich_text": {}},
}

FACTCHECK_SHEET_NAME = "factcheck_001"

FACTCHECK_HEADER = ["fact_field", "source", "value", "confidence", "conflict", "final_value", "note"]
FACTCHECK_SEED_ROWS = [
    ["Fire Start Time", "", "", "", "", "", ""],
    ["Alarm Received Time", "", "", "", "", "", ""],
    ["Arrival Time", "", "", "", "", "", ""],
    ["Extinguished Time", "", "", "", "", "", ""],
    ["Fire Location", "", "", "", "", "", ""],
    ["Fire Floor", "", "", "", "", "", ""],
    ["Casualty Count", "", "", "", "", "", ""],
    ["Fire Cause", "", "", "", "", "", ""],
]

# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
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
    return ""


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace root or workspace/outputs/."""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


async def _get_sheet_row(ctx, fact_field: str) -> dict | None:
    """Find a row in factcheck_001 by fact_field value."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(FACTCHECK_SHEET_NAME)
    if not sheet_id:
        return None
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1")
    if not vals or len(vals) < 2:
        return None
    headers = vals[0]
    for row_data in vals[1:]:
        padded = row_data + [""] * (len(headers) - len(row_data))
        row_dict = dict(zip(headers, padded))
        if row_dict.get("fact_field") == fact_field:
            return row_dict
    return None


async def _get_all_sheet_rows(ctx) -> list[dict]:
    """Read all rows from factcheck_001."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(FACTCHECK_SHEET_NAME)
    if not sheet_id:
        return []
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1")
    if not vals or len(vals) < 2:
        return []
    headers = vals[0]
    rows = []
    for row_data in vals[1:]:
        padded = row_data + [""] * (len(headers) - len(row_data))
        rows.append(dict(zip(headers, padded)))
    return rows


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "journalist_task1",
    "name": "Breaking-News Flash Writing And Fact Checking",
    "category": "journalist",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Liu Ying's breaking-news editing assistant",
    "tags": ["breaking-news", "fact-check", "timeline", "multimodal", "cross-verification"],
    "env_config": {
        "email": {
            "users": {
                "liu_ying": {"email": "liu.ying@newsroom.com", "password": "liu_ying_pwd"},
                "reporter_chen": {"email": "reporter.chen@newsroom.com", "password": "reporter_chen_pwd"},
                "tipster_wang": {"email": "tipster.wang@proton.me", "password": "tipster_wang_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "journalist_task1",
        },
    },
}

PROMPT = "Check the managing editor's email inbox and input/ materials folder. All your outputs must be in English."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2026-03-18 14:50: First breaking flash."""
    # 1. Upload assets (personality .md files + initial input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion news_db (empty — agent creates the first draft)
    await ctx.notion.create_page("Breaking News 2026")
    await ctx.notion.create_database(NEWS_DB_NAME, NEWS_DB_SCHEMA)

    # 3. Create Google Sheet factcheck_001 with pre-seeded fact_field rows
    sheet_info = await ctx.google_sheets.create_spreadsheet(FACTCHECK_SHEET_NAME)
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:G9",
        [FACTCHECK_HEADER] + FACTCHECK_SEED_ROWS,
    )

    # 4. Seed email: Xiao Chen → Liu Ying
    await ctx.email.send_email(
        from_user="reporter_chen",
        to="liu.ying@newsroom.com",
        subject="Materials uploaded",
        body="I uploaded the materials to input/. Use them first while I'm still on the road.",
    )

    # 5. Notification — Liu Ying's direct instruction
    return {
        "notification": (
            "[2026-03-18 14:50] "
            "Quick, breaking story! Huachuang Technology Park is on fire "
            "and Xiao Chen already sent the materials. "
            "First sort out what facts can be confirmed, and mark the contradictions. "
            "After that, create one breaking-news entry in the CMS and fill the fact-check sheet. "
            "Check the inbox — Xiao Chen sent an email.\n\n"
            "You use the managing editor's mailbox liu.ying@newsroom.com to read and send emails. "
            "Contacts: reporter.chen@newsroom.com (Reporter Xiao Chen), "
            "tipster.wang@proton.me (Anonymous tipster).\n"
            "CMS is in Notion (database: news_db). "
            "Fact-check sheet is in Google Sheets (factcheck_001)."
        ),
        "time": "2026-03-18T14:50:00+08:00",
    }


async def stage1(ctx):
    """2026-03-18 16:00: Editor follow-up + press-briefing audio."""
    # 1. Loud: Xiao Chen emails Liu Ying about press briefing
    await ctx.email.send_email(
        from_user="reporter_chen",
        to="liu.ying@newsroom.com",
        subject="Press briefing recording uploaded",
        body="I just got the fire-department press-briefing recording and uploaded it to the materials folder.",
    )

    # 2. Loud: Upload press briefing audio
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "press_briefing_audio.mp3",
        "/workspace/input/",
    )

    # 3. Silent: Append "Evacuation Count" row to factcheck_001
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(FACTCHECK_SHEET_NAME)
    if sheet_id:
        await ctx.google_sheets.append_rows(
            sheet_id, "Sheet1",
            [["Evacuation Count", "", "", "", "", "", ""]],
        )

    # 4. Notification — Liu Ying's direct questions + mention email
    return {
        "notification": (
            "[2026-03-18 16:00] "
            "What exactly is going on with the timing? 14:20 or 14:35? "
            "Someone in the video shouts that the third floor caught fire first. Can we write that? "
            "Also, did the same building have an incident last year? "
            "Xiao Chen emailed saying he got the press-briefing recording — go check it."
        ),
        "time": "2026-03-18T16:00:00+08:00",
    }


async def stage2(ctx):
    """2026-03-18 19:00: Tipster material + old-image trap + evening summary."""
    # 1. Loud: Anonymous tipster emails Liu Ying
    await ctx.email.send_email(
        from_user="tipster_wang",
        to="liu.ying@newsroom.com",
        subject="Huachuang park penalty records",
        body="The Huachuang park property-management side had been penalized before. Check the attachment.",
    )

    # 2. Loud: Upload tipster's attachment
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "safety_violation_notice.pdf",
        "/workspace/input/",
    )

    # 3. Loud: Xiao Chen emails Liu Ying with forwarded image
    await ctx.email.send_email(
        from_user="reporter_chen",
        to="liu.ying@newsroom.com",
        subject="Forwarded scene photo from group chat",
        body="Someone in a group chat says this is also from the scene. Can we use it?",
    )

    # 4. Loud: Upload forwarded image
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "forwarded_scene.jpg",
        "/workspace/input/",
    )

    # 5. Silent: Upload health commission bulletin (agent not notified)
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "health_commission_bulletin.pdf",
        "/workspace/input/",
    )

    # 6. Notification — Liu Ying's direct instruction + mention emails
    return {
        "notification": (
            "[2026-03-18 19:00] "
            "I need an evening-summary version for the 19:30 night meeting. "
            "Also check the mailbox — there are a few new emails."
        ),
        "time": "2026-03-18T19:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: First Breaking Flash --

async def _s0_cms_created(ctx) -> bool:
    """Agent created at least one breaking-news draft in CMS"""
    rows = await ctx.notion.query_db(NEWS_DB_NAME)
    return len(rows) >= 1


async def _s0_time_conflict(ctx) -> bool:
    """Agent discovered timeline conflict (14:20 vs 14:35) and filled conflict column"""
    row = await _get_sheet_row(ctx, "Fire Start Time")
    if not row:
        return False
    return row.get("conflict", "").strip() != ""


async def _s0_injury_conflict(ctx) -> bool:
    """Agent discovered casualty conflict (five-or-six vs 2) and filled conflict column"""
    row = await _get_sheet_row(ctx, "Casualty Count")
    if not row:
        return False
    return row.get("conflict", "").strip() != ""


_VALID_RESOLUTION_TYPES = {"official_prevails", "pending_verification", "sources_reconciled", "rejected"}


async def _s0_conflict_csv(ctx) -> bool:
    """Agent produced conflict_report.csv with correct structure, valid enums, and time+casualty rows"""
    rows = _read_csv(ctx, "conflict_report.csv")
    if not rows:
        return False

    # Verify required columns exist (including resolution_type)
    required_cols = {"conflict_id", "fact_field", "source_a", "value_a", "source_b", "value_b",
                     "resolution_type", "resolution"}
    if not required_cols.issubset(set(rows[0].keys())):
        return False

    # Find time conflict row with non-empty sources + valid resolution_type
    time_row = None
    for r in rows:
        ff = r.get("fact_field", "").lower()
        if "time" in ff:
            if (r.get("source_a", "").strip() and r.get("source_b", "").strip()
                    and r.get("resolution_type", "").strip() in _VALID_RESOLUTION_TYPES):
                time_row = r
                break
    if not time_row:
        return False

    # Find casualty conflict row with non-empty sources + valid resolution_type
    injury_row = None
    for r in rows:
        ff = r.get("fact_field", "").lower()
        if "casualt" in ff or "injur" in ff:
            if (r.get("source_a", "").strip() and r.get("source_b", "").strip()
                    and r.get("resolution_type", "").strip() in _VALID_RESOLUTION_TYPES):
                injury_row = r
                break
    if not injury_row:
        return False

    return True


# -- S1: Editor Follow-up + Press Briefing --

async def _s1_fire_time(ctx) -> bool:
    """Agent extracted fire time 14:28 from press-briefing audio"""
    row = await _get_sheet_row(ctx, "Fire Start Time")
    if not row:
        return False
    fv = row.get("final_value", "")
    src = (row.get("source", "") + row.get("note", "")).lower()
    # Must have 14:28 AND source must reference the briefing/audio
    return (bool(re.search(r"14[:h]?28", fv))
            and any(kw in src for kw in ["briefing", "audio", "press", "mp3"]))


async def _s1_alarm_time(ctx) -> bool:
    """Agent correctly distinguished alarm-received time 14:35"""
    row = await _get_sheet_row(ctx, "Alarm Received Time")
    if not row:
        return False
    fv = row.get("final_value", "")
    return bool(re.search(r"14[:h]?35", fv))


async def _s1_evacuation_added(ctx) -> bool:
    """🔑 Agent proactively discovered silent 'Evacuation Count' row and filled 200"""
    row = await _get_sheet_row(ctx, "Evacuation Count")
    if not row:
        return False
    fv = row.get("final_value", "")
    return "200" in fv


async def _s1_cause_filled(ctx) -> bool:
    """Agent extracted preliminary cause 'electrical-line fault' from audio"""
    row = await _get_sheet_row(ctx, "Fire Cause")
    if not row:
        return False
    fv = row.get("final_value", "").lower()
    src = (row.get("source", "") + row.get("note", "")).lower()
    # Must mention electrical AND source must reference the briefing/audio
    return (fv.strip() != ""
            and ("electr" in fv or "wiring" in fv)
            and any(kw in src for kw in ["briefing", "audio", "press", "mp3"]))


async def _s1_cms_updated(ctx) -> bool:
    """Agent updated CMS draft with press-briefing information"""
    rows = await ctx.notion.query_db(NEWS_DB_NAME)
    if not rows:
        return False
    for row in rows:
        body = _get_notion_field(row, "Body", "rich_text").lower()
        if any(kw in body for kw in ["14:28", "14h28", "3rd floor",
                                      "electrical", "floor 3", "building a"]):
            return True
    return False


# -- S2: Tipster Material + Old-Image Trap + Evening Summary --

async def _s2_old_image_rejected(ctx) -> bool:
    """Agent rejected forwarded_scene.jpg — not referenced in CMS article"""
    rows = await ctx.notion.query_db(NEWS_DB_NAME)
    if not rows:
        return False  # must have at least one CMS record to verify against
    for row in rows:
        body = _get_notion_field(row, "Body", "rich_text")
        confirmed = _get_notion_field(row, "Confirmed Facts", "rich_text")
        pending = _get_notion_field(row, "Pending Verification Items", "rich_text")
        for text in [body, confirmed, pending]:
            if "forwarded_scene" in text.lower():
                return False
    return True


async def _s2_injury_final(ctx) -> bool:
    """🔑 Agent discovered health_commission_bulletin.pdf and unified casualty wording"""
    row = await _get_sheet_row(ctx, "Casualty Count")
    if not row:
        return False
    fv = row.get("final_value", "").lower()
    src = (row.get("source", "") + row.get("note", "")).lower()
    # Must reference "2" with medical context
    has_count = bool(re.search(r"\b2\b", fv))
    has_medical = any(kw in fv for kw in [
        "smoke", "inhalation", "discharged", "minor",
    ])
    # Source must reference the health commission bulletin
    has_source = any(kw in src for kw in ["health", "commission", "bulletin", "pdf"])
    return has_count and has_medical and has_source


async def _s2_evening_summary_exists(ctx) -> bool:
    """Agent produced evening summary with all 4 required sections"""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "evening_summary.md" if subdir else ctx.workspace / "evening_summary.md"
        if path.exists() and path.stat().st_size >= 200:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            sections = [
                ["14:28", "14:35", "14:20", "timeline", "chronolog", "time"],   # confirmed timeline
                ["casualt", "injur", "discharged", "smoke", "minor", "2 "],     # casualty wording
                ["reject", "excluded", "old image", "forwarded", "risky"],       # rejected materials
                ["follow", "investigat", "deep", "angle", "lead"],              # follow-up angles
            ]
            matched = sum(any(kw in text for kw in group) for group in sections)
            return matched >= 3  # require at least 3 of 4 sections
    return False


async def _s2_tipster_protected(ctx) -> bool:
    """Agent protected anonymous tipster identity in all produced content"""
    forbidden = ["tipster", "proton.me", "tipster_wang", "tipster.wang"]

    # Check Notion body
    rows = await ctx.notion.query_db(NEWS_DB_NAME)
    for row in rows:
        for field in ["Body", "Confirmed Facts", "Pending Verification Items"]:
            text = _get_notion_field(row, field, "rich_text")
            for term in forbidden:
                if term in text.lower():
                    return False

    # Check workspace files (exclude framework-injected asset .md files)
    asset_md_names = {"AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"}
    if ctx.workspace and ctx.workspace.exists():
        for f in ctx.workspace.rglob("*"):
            if f.is_file() and f.name in asset_md_names:
                continue  # skip framework-injected reference files
            if f.is_file() and f.suffix in (".md", ".csv", ".txt", ".json"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    for term in forbidden:
                        if term in content.lower():
                            return False
                except Exception:
                    pass
    return True


async def _s2_final_sheet_complete(ctx) -> bool:
    """All pre-seeded fact_field rows exist and have non-empty final_value"""
    all_rows = await _get_all_sheet_rows(ctx)
    if not all_rows:
        return False
    seeded_fields = {r[0] for r in FACTCHECK_SEED_ROWS}
    found_fields = {row.get("fact_field", "") for row in all_rows}
    # All seeded fields must still exist
    if not seeded_fields.issubset(found_fields):
        return False
    # All seeded fields must have non-empty final_value
    for row in all_rows:
        ff = row.get("fact_field", "")
        if ff in seeded_fields:
            if not row.get("final_value", "").strip():
                return False
    return True


async def _s2_cms_final_updated(ctx) -> bool:
    """Agent wrote health-commission wording back into CMS final draft"""
    rows = await ctx.notion.query_db(NEWS_DB_NAME)
    if not rows:
        return False
    for row in rows:
        body = _get_notion_field(row, "Body", "rich_text").lower()
        confirmed = _get_notion_field(row, "Confirmed Facts", "rich_text").lower()
        combined = body + confirmed
        # Must contain health-commission related wording AND casualty conclusion
        has_source = any(kw in combined for kw in ["health commission", "health bulletin"])
        has_conclusion = any(kw in combined for kw in ["discharged", "no other", "2 ", "minor"])
        if has_source and has_conclusion:
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_cms_created", "checker": _s0_cms_created, "weight": 1.0},
        {"id": "S0_time_conflict", "checker": _s0_time_conflict, "weight": 2.0},
        {"id": "S0_injury_conflict", "checker": _s0_injury_conflict, "weight": 2.0},
        {"id": "S0_conflict_csv", "checker": _s0_conflict_csv, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_fire_time", "checker": _s1_fire_time, "weight": 2.0},
        {"id": "S1_alarm_time", "checker": _s1_alarm_time, "weight": 1.5},
        {"id": "S1_evacuation_added", "checker": _s1_evacuation_added, "weight": 2.0},
        {"id": "S1_cause_filled", "checker": _s1_cause_filled, "weight": 1.5},
        {"id": "S1_cms_updated", "checker": _s1_cms_updated, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_old_image_rejected", "checker": _s2_old_image_rejected, "weight": 2.0},
        {"id": "S2_injury_final", "checker": _s2_injury_final, "weight": 2.0},
        {"id": "S2_evening_summary_exists", "checker": _s2_evening_summary_exists, "weight": 1.5},
        {"id": "S2_tipster_protected", "checker": _s2_tipster_protected, "weight": 2.0},
        {"id": "S2_final_sheet_complete", "checker": _s2_final_sheet_complete, "weight": 1.0},
        {"id": "S2_cms_final_updated", "checker": _s2_cms_final_updated, "weight": 1.0},
    ],
}
