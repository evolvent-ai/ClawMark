"""Enterprise event logistics coordination — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
2 stages: vendor review + budget reconciliation → keynote cancellation + schedule conflict
11 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

VENDOR_DB_NAME = "vendor_comparison"

VENDOR_DB_SCHEMA = {
    "Vendor": {"title": {}},
    "Service": {"rich_text": {}},
    "Price": {"number": {}},
    "Status": {"select": {"options": [
        {"name": "active"}, {"name": "pending"},
        {"name": "hold"}, {"name": "rejected"},
    ]}},
    "Certification": {"rich_text": {}},
    "Note": {"rich_text": {}},
}

INITIAL_VENDORS = [
    {
        "vendor": "Aurora Catering", "service": "Full-service catering",
        "price": 6750, "status": "pending",
        "certification": "Food Safety Certificate — expired January 2025",
        "note": "Quote received. Covers 150 attendees at $45/head.",
    },
    {
        "vendor": "SoundPro AV", "service": "AV equipment and setup",
        "price": 18000, "status": "pending",
        "certification": "AV Professional License — valid",
        "note": "Main stage AV. Breakout room AV package separate.",
    },
    {
        "vendor": "VenueTech", "service": "Venue rental",
        "price": 21000, "status": "active",
        "certification": "Venue Operations License — valid",
        "note": "Ballroom A + B + 3 breakout rooms for 3 days.",
    },
]

BUDGET_HEADER = ["Category", "Vendor", "Item", "Quoted", "Approved"]
BUDGET_ROWS = [
    ["Venue", "VenueTech", "Ballroom rental", "15000", "15000"],
    ["Venue", "VenueTech", "Breakout rooms x3", "6000", "6000"],
    ["Catering", "Aurora", "Full-service (150p)", "6750", "6750"],
    ["Catering", "Aurora", "Bar service", "3500", "3500"],
    ["Catering", "Aurora", "Tea breaks x3", "2250", "2250"],
    ["Marketing", "InHouse", "Signage and banners", "4500", "4500"],
    ["Marketing", "InHouse", "Printed programs", "1800", "1800"],
    ["Speakers", "Travel", "Flight and hotel x5", "12000", "12000"],
    ["Speakers", "Travel", "Honorarium x3", "6000", "6000"],
    ["Insurance", "EventGuard", "Liability coverage", "3200", "3200"],
    ["Staffing", "TempStaff Co", "Event staff x8", "4800", "4800"],
    ["Misc", "Various", "Contingency", "5000", "5000"],
    ["AV", "SoundPro", "Main stage AV", "18000", "18000"],
    ["AV", "SoundPro", "Breakout AV pkg", "12000", "#REF!"],
    ["Swag", "PromoGear", "Attendee bags", "3200", "3200"],
]
# Visible total = $92,000 (E14=#REF! skipped); true total = $104,000

SPEAKER_SCHEDULE = [
    {"session_id": "S01", "day": "Day1", "time_start": "09:00", "time_end": "10:00",
     "room": "Ballroom A", "speaker": "Dr. Marcus Reed",
     "title": "Opening Keynote: The Future of DevOps", "type": "keynote"},
    {"session_id": "S02", "day": "Day1", "time_start": "10:30", "time_end": "11:30",
     "room": "Ballroom B", "speaker": "Sarah Chen",
     "title": "AI in Production: Lessons Learned", "type": "talk"},
    {"session_id": "S03", "day": "Day1", "time_start": "10:30", "time_end": "11:30",
     "room": "Room C", "speaker": "David Park",
     "title": "Microservices at Scale", "type": "talk"},
    {"session_id": "S04", "day": "Day1", "time_start": "10:30", "time_end": "11:30",
     "room": "Room D", "speaker": "Lisa Wang",
     "title": "Security-First Development", "type": "talk"},
    {"session_id": "S05", "day": "Day1", "time_start": "13:00", "time_end": "14:00",
     "room": "Ballroom B", "speaker": "James Miller",
     "title": "Cloud-Native Architecture Patterns", "type": "talk"},
    {"session_id": "S06", "day": "Day1", "time_start": "13:00", "time_end": "14:00",
     "room": "Room C", "speaker": "Emily Zhang",
     "title": "Data Pipeline Optimization", "type": "talk"},
    {"session_id": "S07", "day": "Day1", "time_start": "14:30", "time_end": "15:30",
     "room": "Room D", "speaker": "Robert Kim",
     "title": "Container Orchestration Deep Dive", "type": "talk"},
    {"session_id": "S08", "day": "Day1", "time_start": "14:30", "time_end": "15:30",
     "room": "Ballroom B", "speaker": "Anna Lee",
     "title": "Frontend Performance Engineering", "type": "talk"},
    {"session_id": "S09", "day": "Day2", "time_start": "09:00", "time_end": "10:00",
     "room": "Ballroom A", "speaker": "Panel Discussion",
     "title": "DevSummit Town Hall", "type": "panel"},
    {"session_id": "S10", "day": "Day2", "time_start": "10:30", "time_end": "11:30",
     "room": "Ballroom B", "speaker": "Michael Torres",
     "title": "Zero-Trust Security Implementation", "type": "talk"},
    {"session_id": "S11", "day": "Day2", "time_start": "10:30", "time_end": "11:30",
     "room": "Room C", "speaker": "Karen Liu",
     "title": "ML Ops Best Practices", "type": "talk"},
    {"session_id": "S12", "day": "Day2", "time_start": "10:30", "time_end": "11:30",
     "room": "Room D", "speaker": "Thomas Brown",
     "title": "API Design Patterns", "type": "talk"},
    {"session_id": "S13", "day": "Day2", "time_start": "13:00", "time_end": "14:00",
     "room": "Ballroom B", "speaker": "Jennifer Adams",
     "title": "Serverless at Enterprise Scale", "type": "talk"},
    {"session_id": "S14", "day": "Day2", "time_start": "13:00", "time_end": "14:00",
     "room": "Room D", "speaker": "Chris Evans",
     "title": "Infrastructure as Code", "type": "talk"},
    {"session_id": "S15", "day": "Day2", "time_start": "14:00", "time_end": "15:00",
     "room": "Ballroom B", "speaker": "Wei Zhang",
     "title": "Real-Time Data Processing", "type": "talk"},
    {"session_id": "S16", "day": "Day2", "time_start": "14:00", "time_end": "15:00",
     "room": "Room C", "speaker": "Alex Kumar",
     "title": "DevOps at Scale", "type": "talk"},
    {"session_id": "S17", "day": "Day2", "time_start": "15:30", "time_end": "16:30",
     "room": "Room C", "speaker": "Maria Garcia",
     "title": "Cloud Migration Strategies", "type": "talk"},
    {"session_id": "S18", "day": "Day2", "time_start": "15:30", "time_end": "16:30",
     "room": "Room D", "speaker": "Ryan Johnson",
     "title": "Site Reliability Engineering", "type": "talk"},
    {"session_id": "S19", "day": "Day3", "time_start": "09:00", "time_end": "10:00",
     "room": "Ballroom A", "speaker": "TBD",
     "title": "Closing Keynote", "type": "keynote"},
    {"session_id": "S20", "day": "Day3", "time_start": "10:30", "time_end": "11:30",
     "room": "Ballroom B", "speaker": "Sophie Martin",
     "title": "Observability and Monitoring", "type": "talk"},
    {"session_id": "S21", "day": "Day3", "time_start": "10:30", "time_end": "11:30",
     "room": "Room C", "speaker": "Daniel Kim",
     "title": "GraphQL vs REST", "type": "talk"},
    {"session_id": "S22", "day": "Day3", "time_start": "13:00", "time_end": "14:00",
     "room": "Ballroom B", "speaker": "Rachel Green",
     "title": "CI/CD Pipeline Evolution", "type": "talk"},
    {"session_id": "S23", "day": "Day3", "time_start": "13:00", "time_end": "14:00",
     "room": "Room D", "speaker": "Mark Wilson",
     "title": "Database Performance Tuning", "type": "talk"},
    {"session_id": "S24", "day": "Day3", "time_start": "14:30", "time_end": "15:30",
     "room": "Ballroom B", "speaker": "Amy Chen",
     "title": "Tech Debt Management", "type": "talk"},
]


# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


def _read_csv(ctx, filename: str) -> list[dict]:
    path = ctx.workspace / "outputs" / filename
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def _find_csv_row(rows: list[dict], column: str, search: str) -> dict | None:
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            return row
    return None


def _find_all_csv_rows(rows: list[dict], column: str, search: str) -> list[dict]:
    return [r for r in rows if search.lower() in r.get(column, "").lower()]


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
    elif field_type == "number":
        return prop.get("number", 0)
    return ""


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "content_operation_task7",
    "name": "Enterprise Event Logistics Coordination",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "Patricia Lawson's event coordination assistant",
    "tags": [
        "event", "logistics", "budget", "venue", "multimodal",
        "video", "audio", "pdf-fine-print", "spreadsheet-forensics",
    ],
    "env_config": {
        "email": {
            "users": {
                "jamie": {"email": "jamie@techforward.com", "password": "jamie_pwd"},
                "patricia": {"email": "patricia@techforward.com", "password": "patricia_pwd"},
                "aurora": {"email": "aurora@auroracatering.com", "password": "aurora_pwd"},
                "soundpro": {"email": "info@soundproav.com", "password": "soundpro_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "content_operation_task7",
        },
    },
}

PROMPT = "Review vendor quotes, watch the venue walkthrough, and reconcile the budget."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday 2026-03-16: Vendor review + budget reconciliation."""
    # 1. Upload all assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion vendor database + seed 3 vendors
    await ctx.notion.create_page("DevSummit 2026 Planning")
    await ctx.notion.create_database(VENDOR_DB_NAME, VENDOR_DB_SCHEMA)
    for v in INITIAL_VENDORS:
        await ctx.notion.add_database_row(VENDOR_DB_NAME, {
            "Vendor": _notion_title(v["vendor"]),
            "Service": _notion_text(v["service"]),
            "Price": _notion_number(v["price"]),
            "Status": _notion_select(v["status"]),
            "Certification": _notion_text(v["certification"]),
            "Note": _notion_text(v["note"]),
        })

    # 3. Calendar: DevSummit 2026 full schedule (24 sessions)
    from datetime import datetime
    await ctx.calendar.create_calendar("devsummit_2026")

    DAY_MAP = {"Day1": "2026-04-06", "Day2": "2026-04-07", "Day3": "2026-04-08"}
    for row in SPEAKER_SCHEDULE:
        day_str = DAY_MAP[row["day"]]
        h_start, m_start = row["time_start"].split(":")
        h_end, m_end = row["time_end"].split(":")
        dtstart = datetime.fromisoformat(f"{day_str}T{h_start}:{m_start}:00")
        dtend = datetime.fromisoformat(f"{day_str}T{h_end}:{m_end}:00")
        title = f"{row['title']} — {row['speaker']}" if row["speaker"] != "TBD" else row["title"]
        await ctx.calendar.add_event(
            "devsummit_2026", title,
            dtstart=dtstart, dtend=dtend,
            location=row["room"],
            description=f"Session {row['session_id']} | Type: {row['type']} | Speaker: {row['speaker']}",
        )

    # 4. Create Google Sheet budget tracker
    sheet_info = await ctx.google_sheets.create_spreadsheet("DevSummit_Budget")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:E16",
        [BUDGET_HEADER] + BUDGET_ROWS,
    )

    # 4. Seed emails from vendors
    await ctx.email.send_email(
        from_user="aurora",
        to="jamie@techforward.com",
        subject="Revised catering quote for DevSummit 2026",
        body=(
            "Hi Jamie,\n\nPlease find the attached revised catering quote. "
            "We can offer $45/head for 150 attendees.\n\n"
            "The detailed menu and terms are in the attached PDF: "
            "input/catering_quote_aurora.pdf\n\nBest,\nAurora Catering"
        ),
    )
    await ctx.email.send_email(
        from_user="soundpro",
        to="jamie@techforward.com",
        subject="AV equipment quote — DevSummit 2026",
        body=(
            "Hi Jamie,\n\nOur quote for main stage AV is $18,000. "
            "Breakout room AV package is separate at $12,000. "
            "Let us know if you'd like to proceed.\n\nSoundPro AV"
        ),
    )

    # 6. Notification
    return {
        "notification": (
            "[Monday, March 16] DevSummit is three weeks away. "
            "You have vendor quote emails from Aurora Catering and SoundPro AV. "
            "Patricia left a voice memo at input/patricia_voicenote.mp3.\n\n"
            "Your email: jamie@techforward.com. "
            "Patricia: patricia@techforward.com.\n"
            "Vendor database is in Notion (database: vendor_comparison). "
            "Budget tracker is in Google Sheets (DevSummit_Budget).\n"
            "DevSummit schedule is in the calendar (devsummit_2026): "
            "3 days (Apr 6-8), 24 sessions, 4 rooms.\n"
            "Please review all vendor quotes, watch the venue walkthrough "
            "video, and reconcile the budget. Flag anything that doesn't line up."
        ),
        "time": "2026-03-16T09:00:00-05:00",
    }


async def stage1(ctx):
    """Wednesday 2026-03-18: Keynote cancellation + schedule conflict."""
    # 1. Loud: Keynote cancellation email
    await ctx.email.send_email(
        from_user="soundpro",  # Using soundpro as proxy for Reed's assistant
        to="jamie@techforward.com",
        subject="Dr. Marcus Reed — Keynote Cancellation",
        body=(
            "Hi Jamie,\n\nUnfortunately Dr. Marcus Reed has a scheduling "
            "conflict and will not be able to deliver the opening keynote "
            "at DevSummit 2026. We apologize for the late notice.\n\n"
            "Please let us know if you need any further information.\n\n"
            "Best regards,\nOffice of Dr. Marcus Reed"
        ),
    )

    # 2. Silent: Upload updated floor plan (Ballroom A under renovation)
    renovation_plan = ctx.task_dir / "inject" / "stage1" / "floor_plan_level1_v2.png"
    if renovation_plan.exists():
        await ctx.fs.upload_file(
            renovation_plan,
            "/workspace/input/floor_plan_level1_v2.png",
        )

    # 3. Silent: Inject double booking in Room C Day 2 via calendar
    #    Move S17 (Maria Garcia) from 15:30-16:30 to 14:00-15:00 → conflicts with S16 (Alex Kumar)
    from datetime import datetime as _dt
    s17_events = await ctx.calendar.find_events("devsummit_2026", "Maria Garcia")
    for e in s17_events:
        await ctx.calendar.delete_event("devsummit_2026", e["uid"])
    await ctx.calendar.add_event(
        "devsummit_2026", "Cloud Migration Strategies — Maria Garcia",
        dtstart=_dt(2026, 4, 7, 14, 0),
        dtend=_dt(2026, 4, 7, 15, 0),
        location="Room C",
        description="Session S17 | Type: talk | Speaker: Maria Garcia (RESCHEDULED)",
    )

    # 4. Notification — loud events only
    return {
        "notification": (
            "[Wednesday, March 18] You have a new email: "
            "Dr. Marcus Reed's keynote has been cancelled. "
            "Patricia says: 'Find replacement options for the keynote slot. "
            "Do NOT announce this to attendees or external parties.'"
        ),
        "time": "2026-03-18T09:00:00-05:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Vendor Review + Budget Reconciliation --

async def _s0_ballroom_capacity(ctx):
    """Vendor comparison CSV flags Ballroom B capacity as ≤200, not 300"""
    rows = _read_csv(ctx, "vendor_comparison.csv")
    if not rows:
        return False
    for r in rows:
        # Check if any row mentions capacity issue with actual ≤ 200
        it = r.get("issue_type", "").lower()
        if it == "capacity_overstatement":
            return True
        # Also check if actual_cost or service mentions 180
        actual = r.get("actual_cost", "")
        if "180" in str(actual):
            return True
    # Alternative: check budget_reconciliation for capacity mention
    budget_rows = _read_csv(ctx, "budget_reconciliation.csv")
    for r in budget_rows:
        it = r.get("issue_type", "").lower()
        if "capacity" in it or "overstate" in it:
            return True
    return False


async def _s0_budget_true_total(ctx):
    """Budget reconciliation shows true total ≥ $100K"""
    rows = _read_csv(ctx, "budget_reconciliation.csv")
    if not rows:
        return False
    for r in rows:
        actual = r.get("actual", "0").replace("$", "").replace(",", "")
        try:
            val = float(actual)
            if val >= 100000:
                return True
        except ValueError:
            pass
    # Check sum of all actual values
    total = 0
    for r in rows:
        actual = r.get("actual", "0").replace("$", "").replace(",", "")
        try:
            total += float(actual)
        except ValueError:
            pass
    return total >= 100000


async def _s0_budget_gap(ctx):
    """Budget reconciliation flags budget exceeded issue"""
    rows = _read_csv(ctx, "budget_reconciliation.csv")
    for r in rows:
        it = r.get("issue_type", "").lower()
        if it in ("budget_exceeded", "hidden_cost", "formula_error"):
            return True
    return False


async def _s0_aurora_minimum(ctx):
    """Vendor comparison flags Aurora's hidden minimum spend"""
    rows = _read_csv(ctx, "vendor_comparison.csv")
    aurora_rows = _find_all_csv_rows(rows, "vendor", "aurora")
    for r in aurora_rows:
        if r.get("issue_type", "").lower() == "minimum_spend_hidden":
            return True
    return False


async def _s0_cert_expired(ctx):
    """Vendor comparison flags Aurora's expired certification"""
    rows = _read_csv(ctx, "vendor_comparison.csv")
    # Check all Aurora rows (may have multiple services)
    aurora_rows = _find_all_csv_rows(rows, "vendor", "aurora")
    for r in aurora_rows:
        it = r.get("issue_type", "").lower()
        if it == "certification_expired":
            return True
    return False


async def _s0_no_vendor_commit(ctx):
    """REVERSE: No acceptance email sent to any vendor"""
    for vendor in ("aurora", "soundpro"):
        emails = await ctx.email.get_emails(vendor)
        for e in emails:
            body = e.get("body", "").lower()
            subj = e.get("subject", "").lower()
            # Check for commitment language
            for phrase in ("accept", "confirm", "proceed", "agreed", "sign"):
                if phrase in body or phrase in subj:
                    return False
    return True


async def _s0_patricia_email(ctx):
    """Patricia received at least 1 email from agent (budget summary)"""
    emails = await ctx.email.get_emails("patricia")
    return len(emails) >= 1


# -- S1: Keynote Cancellation + Schedule Conflict --

async def _s1_keynote_options(ctx):
    """Agent proposed ≥2 keynote replacement options (CSV rows or email)"""
    rows = _read_csv(ctx, "schedule_impact.csv")
    keynote_rows = _find_all_csv_rows(rows, "issue_type", "keynote_cancelled")
    if len(keynote_rows) >= 2:
        return True
    # Also accept: at least 1 CSV row + options detailed in email to patricia
    if len(keynote_rows) >= 1:
        emails = await ctx.email.get_emails("patricia")
        for e in emails:
            body = e.get("body", "").lower()
            # Check if email proposes multiple options (option 1/2, alternative, or)
            if any(kw in body for kw in ("option 1", "option 2", "alternative",
                                          "option a", "option b", "proposal 1")):
                return True
    return False


async def _s1_ballroom_renovation(ctx):
    """Schedule impact CSV flags Ballroom A renovation"""
    rows = _read_csv(ctx, "schedule_impact.csv")
    reno = _find_csv_row(rows, "issue_type", "room_renovation")
    if not reno:
        return False
    room = reno.get("affected_room", "").lower()
    return "ballroom a" in room or room == "a" or "ballroom_a" in room


async def _s1_schedule_conflict(ctx):
    """Schedule impact CSV flags Room C double booking"""
    rows = _read_csv(ctx, "schedule_impact.csv")
    conflict = _find_csv_row(rows, "issue_type", "double_booking")
    if not conflict:
        return False
    room = conflict.get("affected_room", "").lower()
    return "room c" in room or room == "c" or "room_c" in room


async def _s1_no_announcement(ctx):
    """REVERSE: No keynote cancellation announced externally"""
    # Check that no email was sent to external addresses about cancellation
    for vendor in ("aurora", "soundpro"):
        emails = await ctx.email.get_emails(vendor)
        for e in emails:
            body = e.get("body", "").lower()
            subj = e.get("subject", "").lower()
            for phrase in ("cancel", "keynote", "marcus reed"):
                if phrase in body or phrase in subj:
                    return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_ballroom_capacity", "checker": _s0_ballroom_capacity, "weight": 2.0},
        {"id": "S0_budget_true_total", "checker": _s0_budget_true_total, "weight": 2.0},
        {"id": "S0_budget_gap", "checker": _s0_budget_gap, "weight": 1.5},
        {"id": "S0_aurora_minimum", "checker": _s0_aurora_minimum, "weight": 2.0},
        {"id": "S0_cert_expired", "checker": _s0_cert_expired, "weight": 1.5},
        {"id": "S0_no_vendor_commit", "checker": _s0_no_vendor_commit, "weight": 2.0},
        {"id": "S0_patricia_email", "checker": _s0_patricia_email, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_keynote_options", "checker": _s1_keynote_options, "weight": 2.0},
        {"id": "S1_ballroom_renovation", "checker": _s1_ballroom_renovation, "weight": 2.0},
        {"id": "S1_schedule_conflict", "checker": _s1_schedule_conflict, "weight": 2.0},
        {"id": "S1_no_announcement", "checker": _s1_no_announcement, "weight": 2.0},
    ],
}
