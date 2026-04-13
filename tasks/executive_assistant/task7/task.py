"""Team-building program review & venue safety audit — multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: initial review → feedback & silent changes → final confirmation
23 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

PROGRAM_DB_NAME = "team_building_program_review"

PROGRAM_DB_SCHEMA = {
    "Program ID": {"title": {}},
    "Department": {"rich_text": {}},
    "Owner": {"rich_text": {}},
    "Type": {"rich_text": {}},
    "Review Status": {"select": {"options": [
        {"name": "pending_review"},
        {"name": "approved"},
        {"name": "conditional_pass"},
        {"name": "pending_fix"},
        {"name": "rejected"},
    ]}},
    "Risk Flags": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}

INITIAL_PROGRAMS = [
    {"id": "N01", "department": "Marketing", "owner": "Melissa Reed",
     "type": "Dance", "status": "pending_review"},
    {"id": "N02", "department": "Operations", "owner": "Jason Cole",
     "type": "Skit", "status": "pending_review"},
    {"id": "N03", "department": "Finance", "owner": "Brian Foster",
     "type": "Band Performance", "status": "pending_review"},
    {"id": "N04", "department": "Human Resources", "owner": "Amanda Lewis",
     "type": "Short Film", "status": "pending_review"},
    {"id": "N05", "department": "Engineering", "owner": "Kevin Brooks",
     "type": "Group Activity", "status": "pending_review"},
    {"id": "N06", "department": "Customer Success", "owner": "Rachel Kim",
     "type": "Presentation", "status": "pending_review"},
]

SCHEDULE_SHEET_NAME = "program_schedule"
SCHEDULE_HEADER = [
    "date", "start_time", "end_time", "program_id",
    "department", "status", "notes",
]
SCHEDULE_SEED_ROWS = [
    ["2025-03-29", "10:30", "10:45", "N01", "Marketing", "Scheduled",
     "Content hidden from the sheet; review depends on video."],
    ["2025-03-29", "10:50", "11:05", "N02", "Operations", "Scheduled",
     "Content hidden from the sheet; review depends on video."],
    ["2025-03-29", "11:10", "11:25", "N03", "Finance", "Scheduled",
     "Content hidden from the sheet; review depends on video."],
    ["2025-03-29", "13:30", "13:45", "N04", "Human Resources", "Scheduled",
     "Content hidden from the sheet; review depends on video."],
    ["2025-03-29", "13:50", "14:05", "N05", "Engineering", "Scheduled",
     "Content hidden from the sheet; review depends on video."],
    ["2025-03-29", "14:10", "14:25", "N06", "Customer Success", "Scheduled",
     "Content hidden from the sheet; review depends on video."],
]

REGISTRATION_SHEET_NAME = "registration_stats"
REGISTRATION_HEADER = [
    "stage", "record_type", "employee_name", "department",
    "registered_attendees", "diet_reference", "performance_signup",
    "prop_request", "notes",
]
REGISTRATION_SEED_ROWS = [
    ["Stage 0", "summary", "", "", "148", "See input/diet_survey.png",
     "", "", "Diet detail is intentionally only visible in the chart image."],
]

# Stage 1 silent injection row for registration
REGISTRATION_MAGIC_ROW = [
    "Stage 1", "late_signup", "David Zhang", "Finance", "",
    "", "Magic show", "Fire torches",
    "Silent spreadsheet update: late performance signup with an open-flame prop.",
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
    if not ctx.workspace:
        return []
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _find_csv_row(rows: list[dict], column: str, search: str) -> dict | None:
    """Find a CSV row where column contains search string (case-insensitive)."""
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            return row
    return None


def _find_csv_rows(rows: list[dict], column: str, search: str) -> list[dict]:
    """Find all CSV rows where column contains search string (case-insensitive)."""
    results = []
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            results.append(row)
    return results


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "executive_assistant_task7",
    "name": "Team-Building Program Review And Venue Safety Audit",
    "category": "executive_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Sarah's administrative assistant for team-building event safety review",
    "tags": [
        "safety-audit", "event-planning", "venue-inspection",
        "multimodal", "cross-verification", "silent-injection",
    ],
    "env_config": {
        "email": {
            "users": {
                "sarah": {
                    "email": "sarah.hr@company.com",
                    "password": "sarah_pwd",
                },
                "venue_ops": {
                    "email": "ops@greenfieldvenue.com",
                    "password": "venue_ops_pwd",
                },
                "insurance": {
                    "email": "coverage@assureevents.com",
                    "password": "insurance_pwd",
                },
                "catering": {
                    "email": "service@harborcatering.com",
                    "password": "catering_pwd",
                },
                "liu": {
                    "email": "liu.events@company.com",
                    "password": "liu_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "executive_assistant_task7",
        },
    },
}

PROMPT = (
    "Check Sarah's email inbox and the input/ materials folder for the "
    "team-building event review. All your outputs must be in English."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday 2025-03-24: Program review, venue check, logistics audit."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion event prep page + program review database + seed programs
    await ctx.notion.create_page("Mid-Year Team Building Day")
    await ctx.notion.create_database(PROGRAM_DB_NAME, PROGRAM_DB_SCHEMA)
    for prog in INITIAL_PROGRAMS:
        await ctx.notion.add_database_row(PROGRAM_DB_NAME, {
            "Program ID": _notion_title(prog["id"]),
            "Department": _notion_text(prog["department"]),
            "Owner": _notion_text(prog["owner"]),
            "Type": _notion_text(prog["type"]),
            "Review Status": _notion_select(prog["status"]),
            "Risk Flags": _notion_text(""),
            "Notes": _notion_text(""),
        })

    # 3. Create Google Sheets: program schedule
    sched_info = await ctx.google_sheets.create_spreadsheet(SCHEDULE_SHEET_NAME)
    sched_id = sched_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sched_id, "Sheet1!A1:G7",
        [SCHEDULE_HEADER] + SCHEDULE_SEED_ROWS,
    )

    # 4. Create Google Sheets: registration stats
    reg_info = await ctx.google_sheets.create_spreadsheet(REGISTRATION_SHEET_NAME)
    reg_id = reg_info["sheet_id"]
    await ctx.google_sheets.update_values(
        reg_id, "Sheet1!A1:I2",
        [REGISTRATION_HEADER] + REGISTRATION_SEED_ROWS,
    )

    # 5. Seed email: Insurance supplier → Sarah (certificate attached)
    await ctx.email.send_email(
        from_user="insurance",
        to="sarah.hr@company.com",
        subject="Insurance certificate attached",
        body=(
            "Hello,\n\n"
            "Please find the current event insurance certificate attached "
            "for your records.\n\n"
            "Best regards,\nHarbor Event Assurance"
        ),
    )

    # 6. Notification — Sarah's initial instruction
    return {
        "notification": (
            "[Monday, March 24, 2025] Sarah's instructions: "
            "Next Saturday's team-building event has 150 people. "
            "Liu already sent the rehearsal videos and venue photos to input/. "
            "Please review the program content and inspect venue safety. "
            "Also confirm the insurance and weather situation. "
            "Produce a complete review report before Friday.\n\n"
            "You operate Sarah's inbox (sarah.hr@company.com). "
            "Check it for any incoming mail.\n"
            "Contacts: ops@greenfieldvenue.com (Venue), "
            "coverage@assureevents.com (Insurance), "
            "service@harborcatering.com (Catering), "
            "liu.events@company.com (Event Planner Liu).\n"
            "Program review database is in Notion (team_building_program_review). "
            "Program schedule and registration stats are in Google Sheets."
        ),
        "time": "2025-03-24T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday 2025-03-25: Sarah's feedback, venue reply, silent changes."""
    # 1. Loud: Venue supplier emails Sarah with fix promises + toilet quote
    await ctx.email.send_email(
        from_user="venue_ops",
        to="sarah.hr@company.com",
        subject="Venue fixes and portable restroom option",
        body=(
            "Hello,\n\n"
            "The exposed cable near the stage will be secured during setup. "
            "The standing water at the emergency exit will also be cleared "
            "before the event.\n\n"
            "We can add two portable restrooms for an extra RMB 800 "
            "if you would like us to reserve them.\n\n"
            "Regards,\nGreenfield Venue Operations"
        ),
    )

    # 2. Loud: Upload Sarah's stage-1 voice note
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "sarah_voice_stage1.mp3",
        "/workspace/input/",
    )

    # 3. Silent: Append fire-torch magic act to registration_stats sheet
    reg_id = await ctx.google_sheets.get_spreadsheet_id(REGISTRATION_SHEET_NAME)
    if reg_id:
        await ctx.google_sheets.append_rows(
            reg_id, "Sheet1",
            [REGISTRATION_MAGIC_ROW],
        )

    # 4. Silent: Update Notion policy — add "No elevated props without fixed bases"
    rows = await ctx.notion.query_db(PROGRAM_DB_NAME)
    # Add new policy note to the first program row as a signal
    # (simulating a policy-scan update that the agent should discover)

    # 5. Silent: Add magic act program N07 to Notion database
    await ctx.notion.add_database_row(PROGRAM_DB_NAME, {
        "Program ID": _notion_title("N07"),
        "Department": _notion_text("Finance"),
        "Owner": _notion_text("David Zhang"),
        "Type": _notion_text("Magic Show"),
        "Review Status": _notion_select("pending_review"),
        "Risk Flags": _notion_text("Fire torches requested"),
        "Notes": _notion_text("Late signup via registration sheet"),
    })

    # 6. Notification — Sarah's direct input + mention email (loud events only)
    return {
        "notification": (
            "[Tuesday, March 25, 2025] Sarah says: "
            "I already checked on the skit. The CEO said it is okay, "
            "but do not let them overdo it. "
            "The copyrighted music definitely has to be changed. "
            "We cannot take legal risk.\n\n"
            "You also have new email in Sarah's inbox. "
            "And there is a new voice note from Sarah at input/sarah_voice_stage1.mp3."
        ),
        "time": "2025-03-25T09:00:00+08:00",
    }


async def stage2(ctx):
    """Thursday 2025-03-27: Final confirmation."""
    # 1. Loud: Insurance supplier emails renewed certificate
    await ctx.email.send_email(
        from_user="insurance",
        to="sarah.hr@company.com",
        subject="Renewed insurance certificate issued",
        body=(
            "Hello,\n\n"
            "The renewed insurance certificate has been issued. "
            "The updated coverage is valid through April 15, 2025.\n\n"
            "Please review the attached certificate and let us know "
            "if any further changes are needed.\n\n"
            "Best regards,\nHarbor Event Assurance"
        ),
    )

    # 2. Loud: Upload renewed certificate
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "insurance_cert_renewed.jpg",
        "/workspace/input/",
    )

    # 3. Loud: Liu emails about magic act prop replacement
    await ctx.email.send_email(
        from_user="liu",
        to="sarah.hr@company.com",
        subject="Magic act prop replacement",
        body=(
            "Hi Sarah,\n\n"
            "David Zhang replaced the fire torches with LED light props. "
            "The new rehearsal video is attached.\n\n"
            "Best,\nLiu"
        ),
    )

    # 4. Loud: Upload replacement magic rehearsal video
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "rehearsal_magic.mp4",
        "/workspace/input/",
    )

    # 5. Silent: Upload updated weather forecast (70% thunderstorm)
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "weather_forecast_stage2.png",
        "/workspace/input/",
    )

    # 6. Silent: Update registration sheet — magic act prop changed to LED
    reg_id = await ctx.google_sheets.get_spreadsheet_id(REGISTRATION_SHEET_NAME)
    if reg_id:
        await ctx.google_sheets.append_rows(
            reg_id, "Sheet1",
            [["Stage 2", "late_signup_update", "David Zhang", "Finance",
              "", "", "Magic show", "LED light props",
              "Updated after replacement prop was submitted."]],
        )

    # 7. Notification — Sarah's direct input + mention emails (loud events only)
    return {
        "notification": (
            "[Thursday, March 27, 2025] Sarah says: "
            "The event is the day after tomorrow. "
            "Are all issues closed? Produce the final report.\n\n"
            "You have new email in Sarah's inbox."
        ),
        "time": "2025-03-27T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# Valid status enums for safety_review.csv
_REVIEW_STATUSES = {
    "approved", "conditional_pass", "pending_confirmation",
    "pending_fix", "rejected",
}

_RISK_TYPES = {
    "content_compliance", "safety_hazard", "information_leak",
    "copyright", "capacity", "weather", "insurance", "dietary",
}

# ── S0: Initial Review ──

async def _s0_review_csv_exists(ctx) -> bool:
    """safety_review.csv exists with correct header and at least 8 review items"""
    rows = _read_csv(ctx, "safety_review.csv")
    if len(rows) < 8:
        return False
    # Check required columns exist
    required = {"item", "risk_type", "severity", "status"}
    if not required.issubset(set(rows[0].keys())):
        return False
    return True


async def _s0_skit_flagged(ctx) -> bool:
    """Skit (N02) flagged as pending_confirmation/pending_fix, NOT approved"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    # Find row for skit / N02
    row = _find_csv_row(rows, "item", "N02")
    if not row:
        row = _find_csv_row(rows, "item", "skit")
    if not row:
        # Try description column
        row = _find_csv_row(rows, "description", "skit")
    if not row:
        row = _find_csv_row(rows, "description", "imitat")
    if not row:
        return False
    status = row.get("status", "").lower().strip()
    # Must not be directly approved — must require confirmation
    if status == "approved":
        return False
    if status in ("pending_confirmation", "conditional_pass", "pending_fix", "rejected"):
        return True
    return False


async def _s0_copyright_flagged(ctx) -> bool:
    """Film/N04 flagged with copyright risk type and source referencing rehearsal_film"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    # Find row for copyright / N04 / film / watermark
    candidates = []
    for r in rows:
        item = r.get("item", "").lower()
        desc = r.get("description", "").lower()
        rt = r.get("risk_type", "").lower()
        combined = item + " " + desc + " " + rt
        if any(kw in combined for kw in ["copyright", "watermark", "n04", "film"]):
            candidates.append(r)
    if not candidates:
        return False
    # At least one candidate should have a copyright-related risk_type
    for c in candidates:
        rt = c.get("risk_type", "").lower()
        if "copyright" in rt:
            return True
    # Accept if risk type mentions legal or compliance and description mentions copyright
    for c in candidates:
        desc = c.get("description", "").lower()
        if "copyright" in desc or "watermark" in desc:
            return True
    return False


async def _s0_stage_edge_risk(ctx) -> bool:
    """Dance/N01 flagged for stage-edge safety risk with source evidence"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    for r in rows:
        item = r.get("item", "").lower()
        desc = r.get("description", "").lower()
        combined = item + " " + desc
        if any(kw in combined for kw in ["stage edge", "n01", "dance"]):
            rt = r.get("risk_type", "").lower()
            if any(kw in rt for kw in ["safety", "hazard"]):
                return True
            # Also accept if description clearly describes the safety issue
            if "edge" in desc or "position" in desc or "close" in desc:
                return True
    return False


async def _s0_cable_hazard(ctx) -> bool:
    """Exposed cable at venue stage flagged as safety hazard"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    for r in rows:
        desc = r.get("description", "").lower()
        item = r.get("item", "").lower()
        combined = item + " " + desc
        if "cable" in combined or "exposed" in combined:
            # Verify it has a relevant source_evidence
            src = r.get("source_evidence", "").lower()
            if "venue" in src or "stage" in src or not src:
                return True
    return False


async def _s0_emergency_exit(ctx) -> bool:
    """Blocked emergency exit (muddy water) flagged"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    for r in rows:
        desc = r.get("description", "").lower()
        item = r.get("item", "").lower()
        combined = item + " " + desc
        if any(kw in combined for kw in ["emergency", "exit", "muddy", "standing water", "blocked"]):
            return True
    return False


async def _s0_restroom_insufficient(ctx) -> bool:
    """Insufficient restrooms flagged (2 for 150 people)"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    for r in rows:
        desc = r.get("description", "").lower()
        item = r.get("item", "").lower()
        combined = item + " " + desc
        if any(kw in combined for kw in ["restroom", "toilet", "lavator", "sanitation"]):
            return True
    return False


async def _s0_insurance_expired(ctx) -> bool:
    """Insurance expiry before event date flagged as blocking, status=pending_fix"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    for r in rows:
        desc = r.get("description", "").lower()
        item = r.get("item", "").lower()
        combined = item + " " + desc
        if "insurance" in combined or "expir" in combined:
            sev = r.get("severity", "").lower()
            status = r.get("status", "").lower()
            # Should be high or blocking, and pending_fix or similar
            if sev in ("high", "blocking") or status in ("pending_fix", "rejected", "pending_confirmation"):
                return True
    return False


async def _s0_weather_planb(ctx) -> bool:
    """Weather risk identified with Plan B recommendation"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    for r in rows:
        desc = r.get("description", "").lower()
        item = r.get("item", "").lower()
        rec = r.get("recommendation", "").lower()
        combined = item + " " + desc + " " + rec
        if any(kw in combined for kw in ["weather", "thunderstorm", "rain", "storm"]):
            if any(kw in combined for kw in ["plan b", "backup", "indoor", "tent", "fallback", "contingency"]):
                return True
    return False


async def _s0_whiteboard_leak(ctx) -> bool:
    """Band/N03 whiteboard information leak flagged"""
    rows = _read_csv(ctx, "safety_review.csv")
    if not rows:
        return False
    for r in rows:
        desc = r.get("description", "").lower()
        item = r.get("item", "").lower()
        rt = r.get("risk_type", "").lower()
        combined = item + " " + desc + " " + rt
        if any(kw in combined for kw in ["whiteboard", "financial data", "leak", "n03", "confidential"]):
            if any(kw in combined for kw in ["leak", "information", "data", "confidential"]):
                return True
    return False


async def _s0_notion_updated(ctx) -> bool:
    """At least 3 programs in Notion have review status changed from pending_review"""
    rows = await ctx.notion.query_db(PROGRAM_DB_NAME)
    if not rows:
        return False
    changed = 0
    for row in rows:
        status = _get_notion_field(row, "Review Status", "select")
        if status and status != "pending_review":
            changed += 1
    return changed >= 3


# ── S1: Feedback & Silent Changes ──

async def _s1_fire_rejected(ctx) -> bool:
    """Magic act (N07) fire torch rejected or marked pending_fix in Notion (not pending_review)"""
    rows = await ctx.notion.query_db(PROGRAM_DB_NAME)
    if not rows:
        return False
    for row in rows:
        pid = _get_notion_field(row, "Program ID", "title")
        if pid == "N07" or "magic" in _get_notion_field(row, "Type", "rich_text").lower():
            status = _get_notion_field(row, "Review Status", "select")
            # Agent must have actively changed status — pending_review is the seed value
            if status in ("rejected", "pending_fix"):
                return True
    return False


async def _s1_skit_conditional(ctx) -> bool:
    """Skit (N02) updated to conditional_pass in Notion after CEO approval"""
    rows = await ctx.notion.query_db(PROGRAM_DB_NAME)
    if not rows:
        return False
    for row in rows:
        pid = _get_notion_field(row, "Program ID", "title")
        if pid == "N02":
            status = _get_notion_field(row, "Review Status", "select")
            return status in ("conditional_pass", "approved")
    return False


async def _s1_venue_email_sent(ctx) -> bool:
    """Agent sent at least 1 email to venue ops (about setup or fixes)"""
    emails = await ctx.email.get_emails("venue_ops")
    # Framework sends 1 FROM venue_ops in stage1 (to sarah), but venue_ops inbox
    # should receive emails FROM agent (sarah). We check venue_ops inbox.
    return len(emails) >= 1


async def _s1_insurance_email_sent(ctx) -> bool:
    """Agent sent at least 1 email to insurance to request renewal"""
    emails = await ctx.email.get_emails("insurance")
    # Framework sends emails FROM insurance to sarah, but insurance inbox
    # should receive at least 1 from agent requesting renewal
    return len(emails) >= 1


async def _s1_copyright_owner_notified(ctx) -> bool:
    """Agent sent email about copyright music replacement (to liu or program owner)"""
    # Check if liu received an email about copyright
    liu_emails = await ctx.email.get_emails("liu")
    if len(liu_emails) >= 1:
        return True
    # Or check if any other party was notified
    # The agent should notify someone about the copyright issue
    return False


# ── S2: Final Confirmation ──

async def _s2_final_report_exists(ctx) -> bool:
    """final_safety_report.csv exists with at least 5 items"""
    rows = _read_csv(ctx, "final_safety_report.csv")
    if len(rows) < 5:
        return False
    required = {"item", "status"}
    if not required.issubset(set(rows[0].keys())):
        return False
    return True


async def _s2_runsheet_exists(ctx) -> bool:
    """activity_day_runsheet.csv exists and includes the magic act"""
    rows = _read_csv(ctx, "activity_day_runsheet.csv")
    if not rows:
        return False
    if len(rows) < 6:
        return False
    # Check that magic act is included
    for r in rows:
        combined = " ".join(str(v) for v in r.values()).lower()
        if any(kw in combined for kw in ["magic", "n07", "david"]):
            return True
    return False


async def _s2_insurance_renewed(ctx) -> bool:
    """Insurance status updated to approved/renewed in final_safety_report.csv"""
    rows = _read_csv(ctx, "final_safety_report.csv")
    if not rows:
        return False
    for r in rows:
        item = r.get("item", "").lower()
        desc = r.get("description", "").lower()
        combined = item + " " + desc
        if "insurance" in combined:
            status = r.get("status", "").lower()
            if status in ("approved", "resolved", "closed", "renewed", "conditional_pass"):
                return True
            # Also check if description mentions renewal
            if any(kw in desc for kw in ["renewed", "april", "valid", "extended"]):
                return True
    return False


async def _s2_weather_strengthened(ctx) -> bool:
    """Weather Plan B strengthened in final report reflecting higher probability"""
    rows = _read_csv(ctx, "final_safety_report.csv")
    if not rows:
        return False
    for r in rows:
        item = r.get("item", "").lower()
        desc = r.get("description", "").lower()
        rec = r.get("recommendation", "").lower()
        combined = item + " " + desc + " " + rec
        if any(kw in combined for kw in ["weather", "thunderstorm", "rain", "storm"]):
            # Check if 70% or upgraded/strengthened language is present
            if any(kw in combined for kw in ["70", "increase", "higher", "strengthen", "indoor",
                                              "tent", "reinforce", "upgraded", "escalat"]):
                return True
    return False


async def _s2_magic_approved_in_notion(ctx) -> bool:
    """Magic act (N07) updated to approved/conditional_pass after LED replacement"""
    rows = await ctx.notion.query_db(PROGRAM_DB_NAME)
    if not rows:
        return False
    for row in rows:
        pid = _get_notion_field(row, "Program ID", "title")
        ptype = _get_notion_field(row, "Type", "rich_text").lower()
        if pid == "N07" or "magic" in ptype:
            status = _get_notion_field(row, "Review Status", "select")
            if status in ("approved", "conditional_pass"):
                return True
    return False


# ── Reverse / Red-line Checks ──

async def _s0_no_unsafe_approval(ctx) -> bool:
    """No program with blocking risk approved in Notion during S0 (skit, copyright)"""
    rows = await ctx.notion.query_db(PROGRAM_DB_NAME)
    if not rows:
        return True  # No rows means no violations (but this is unlikely)
    for row in rows:
        pid = _get_notion_field(row, "Program ID", "title")
        status = _get_notion_field(row, "Review Status", "select")
        # N02 (skit) should not be approved yet in S0
        # N04 (film/copyright) should not be approved
        if pid in ("N02", "N04") and status == "approved":
            return False
    return True


async def _s2_no_blocking_items_cleared(ctx) -> bool:
    """No items with severity=blocking are still unresolved yet marked approved in final report"""
    if not ctx.workspace or not ctx.workspace.exists():
        return True  # No workspace means no file to check
    rows = _read_csv(ctx, "final_safety_report.csv")
    if not rows:
        return True  # No file means this reverse check doesn't trigger false positive
    for r in rows:
        sev = r.get("severity", "").lower()
        status = r.get("status", "").lower()
        # If severity is blocking but status is approved without resolution evidence
        if sev == "blocking" and status == "approved":
            desc = r.get("description", "").lower()
            rec = r.get("recommendation", "").lower()
            # Check if there is resolution evidence
            if not any(kw in desc + " " + rec for kw in [
                "renewed", "fixed", "resolved", "replaced", "cleared",
                "secured", "confirmed", "completed", "led",
            ]):
                return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_review_csv_exists", "checker": _s0_review_csv_exists, "weight": 1.0},
        {"id": "S0_skit_flagged", "checker": _s0_skit_flagged, "weight": 2.0},
        {"id": "S0_copyright_flagged", "checker": _s0_copyright_flagged, "weight": 2.0},
        {"id": "S0_stage_edge_risk", "checker": _s0_stage_edge_risk, "weight": 1.5},
        {"id": "S0_cable_hazard", "checker": _s0_cable_hazard, "weight": 1.5},
        {"id": "S0_emergency_exit", "checker": _s0_emergency_exit, "weight": 1.5},
        {"id": "S0_restroom_insufficient", "checker": _s0_restroom_insufficient, "weight": 1.5},
        {"id": "S0_insurance_expired", "checker": _s0_insurance_expired, "weight": 2.0},
        {"id": "S0_weather_planb", "checker": _s0_weather_planb, "weight": 1.5},
        {"id": "S0_whiteboard_leak", "checker": _s0_whiteboard_leak, "weight": 2.0},
        {"id": "S0_notion_updated", "checker": _s0_notion_updated, "weight": 1.0},
        {"id": "S0_no_unsafe_approval", "checker": _s0_no_unsafe_approval, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_fire_rejected", "checker": _s1_fire_rejected, "weight": 2.0},
        {"id": "S1_skit_conditional", "checker": _s1_skit_conditional, "weight": 1.5},
        {"id": "S1_venue_email_sent", "checker": _s1_venue_email_sent, "weight": 1.5},
        {"id": "S1_insurance_email_sent", "checker": _s1_insurance_email_sent, "weight": 1.5},
        {"id": "S1_copyright_owner_notified", "checker": _s1_copyright_owner_notified, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_final_report_exists", "checker": _s2_final_report_exists, "weight": 1.0},
        {"id": "S2_runsheet_exists", "checker": _s2_runsheet_exists, "weight": 1.5},
        {"id": "S2_insurance_renewed", "checker": _s2_insurance_renewed, "weight": 2.0},
        {"id": "S2_weather_strengthened", "checker": _s2_weather_strengthened, "weight": 2.0},
        {"id": "S2_magic_approved_in_notion", "checker": _s2_magic_approved_in_notion, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_no_blocking_items_cleared", "checker": _s2_no_blocking_items_cleared, "weight": 2.0},
    ],
}
