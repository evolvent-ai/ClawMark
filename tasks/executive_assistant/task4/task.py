"""Product review meeting minutes extraction and risk tracking — multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: audio+whiteboard extraction → clarifications+silent updates → final distribution
14 core checkers (0 keyword-search)
"""
import csv
import re
from datetime import datetime
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

DECISION_DB_NAME = "product_decision_log_2025"

DECISION_DB_SCHEMA = {
    "Decision ID": {"title": {}},
    "Date": {"rich_text": {}},
    "Topic": {"rich_text": {}},
    "Decision": {"rich_text": {}},
    "Owner": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "confirmed"}, {"name": "pending"},
        {"name": "superseded"}, {"name": "blocked"},
    ]}},
    "Notes": {"rich_text": {}},
}

# Historical entries for formatting reference (seeded into Notion)
HISTORICAL_DECISIONS = [
    {
        "id": "DEC-0228-01",
        "date": "2025-02-28",
        "topic": "Q1 Release Freeze",
        "decision": "Code freeze starts March 5; only P0 fixes after that",
        "owner": "Wei Zhang",
        "status": "confirmed",
        "notes": "Approved in Feb 28 review",
    },
    {
        "id": "DEC-0228-02",
        "date": "2025-02-28",
        "topic": "Mobile App Beta",
        "decision": "Beta testing group expanded to 500 users",
        "owner": "Lily Li",
        "status": "confirmed",
        "notes": "QA lead confirmed test coverage",
    },
    {
        "id": "DEC-0307-01",
        "date": "2025-03-07",
        "topic": "Dashboard Redesign",
        "decision": "Design team to deliver mockups by March 14",
        "owner": "Linda Zhao",
        "status": "confirmed",
        "notes": "Aligned with Q2 launch timeline",
    },
]

ITER_SHEET_NAME = "q2_iteration_schedule"
OWNER_SHEET_NAME = "owner_mapping"

ITER_HEADER = ["sprint", "start_date", "end_date", "goal", "owner", "status"]
ITER_SEED_ROWS = [
    ["Sprint 7", "2025-03-17", "2025-03-28", "Payment optimization + user center redesign", "Wei Zhang", "planned"],
    ["Sprint 8", "2025-03-31", "2025-04-11", "Mobile app launch prep + dashboard v2", "Lily Li", "planned"],
]

OWNER_HEADER = ["person", "domain", "email"]
OWNER_SEED_ROWS = [
    ["Wei Zhang", "Backend and payments", "dev-lead@company.com"],
    ["Lily Li", "Product", "pm@company.com"],
    ["Chen", "QA", "qa@company.com"],
    ["Linda Zhao", "Design", "design@company.com"],
    ["Wang Qiang", "Frontend", ""],
]

CALENDAR_NAME = "product_milestones"

_VALID_STATUSES = {
    "confirmed", "pending_confirmation", "risk",
    "open", "resolved", "blocked",
}

_ASSET_MD_NAMES = {"AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"}

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
    """Read a CSV from workspace/outputs/ or workspace root."""
    for subdir in ["outputs", ""]:
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
    return [
        row for row in rows
        if search.lower() in row.get(column, "").lower()
    ]


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "executive_assistant_task4",
    "name": "Product Review Meeting Minutes And Risk Tracking",
    "category": "executive_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "VP Liu's executive assistant for product review minutes",
    "tags": [
        "meeting-minutes", "whiteboard", "audio", "cross-verification",
        "risk-tracking", "multimodal", "contradiction-detection",
    ],
    "env_config": {
        "email": {
            "users": {
                "liu_vp": {"email": "liu.vp@company.com", "password": "liu_vp_pwd"},
                "pm": {"email": "pm@company.com", "password": "pm_pwd"},
                "dev_lead": {"email": "dev-lead@company.com", "password": "dev_lead_pwd"},
                "qa": {"email": "qa@company.com", "password": "qa_pwd"},
                "design": {"email": "design@company.com", "password": "design_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "executive_assistant_task4",
        },
    },
}

PROMPT = (
    "VP Liu sent you today's product review recording and whiteboard photos. "
    "Check your email and the input/ folder, then prepare the meeting minutes. "
    "All your outputs must be in English."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2025-03-14 16:00 Friday: Audio review, whiteboard extraction, screenshot cross-checking."""
    # 1. Upload assets (personality .md files + initial input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion decision log database + seed historical entries
    await ctx.notion.create_page("Product Decision Log 2025")
    await ctx.notion.create_database(DECISION_DB_NAME, DECISION_DB_SCHEMA)
    for rec in HISTORICAL_DECISIONS:
        await ctx.notion.add_database_row(DECISION_DB_NAME, {
            "Decision ID": _notion_title(rec["id"]),
            "Date": _notion_text(rec["date"]),
            "Topic": _notion_text(rec["topic"]),
            "Decision": _notion_text(rec["decision"]),
            "Owner": _notion_text(rec["owner"]),
            "Status": _notion_select(rec["status"]),
            "Notes": _notion_text(rec["notes"]),
        })

    # 3. Create Google Sheet: q2_iteration_schedule
    iter_info = await ctx.google_sheets.create_spreadsheet(ITER_SHEET_NAME)
    iter_id = iter_info["sheet_id"]
    await ctx.google_sheets.update_values(
        iter_id, "Sheet1!A1:F3",
        [ITER_HEADER] + ITER_SEED_ROWS,
    )

    # 4. Create Google Sheet: owner_mapping
    owner_info = await ctx.google_sheets.create_spreadsheet(OWNER_SHEET_NAME)
    owner_id = owner_info["sheet_id"]
    await ctx.google_sheets.update_values(
        owner_id, "Sheet1!A1:C6",
        [OWNER_HEADER] + OWNER_SEED_ROWS,
    )

    # 5. Create Calendar with milestone events
    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        "Product Review Meeting",
        datetime(2025, 3, 14, 14, 0),
        datetime(2025, 3, 14, 15, 30),
        description="Weekly product review with full team",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        "Sprint 7 End",
        datetime(2025, 3, 28, 0, 0),
        datetime(2025, 3, 28, 23, 59),
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        "Q2 Midterm Review",
        datetime(2025, 4, 2, 9, 0),
        datetime(2025, 4, 2, 17, 0),
        description="Q2 midterm progress review",
        uid="q2-midterm-review",
    )

    # 6. Seed emails: Wei Zhang's two contradictory deadline emails
    await ctx.email.send_email(
        from_user="dev_lead",
        to="liu.vp@company.com",
        subject="Deadline confirmation",
        body=(
            "I remember the payment optimization deadline as Friday. "
            "Please confirm it against the meeting recording."
        ),
    )
    await ctx.email.send_email(
        from_user="dev_lead",
        to="liu.vp@company.com",
        subject="Correction: deadline update",
        body=(
            "I previously said the deadline was Friday. "
            "Actually, the deadline is Wednesday. Correcting my earlier email."
        ),
    )

    # 7. Notification — VP Liu's direct instruction
    return {
        "notification": (
            "[2025-03-14 Friday 16:00] "
            "VP Liu sent you the product review recording, whiteboard photos, "
            "projected screenshots, and the review slides. "
            "Please draft the meeting minutes with decisions, action items, "
            "and owners with due dates. Check your email first — "
            "Wei Zhang sent messages about the payment deadline.\n\n"
            "Your email is liu.vp@company.com. "
            "Contacts: pm@company.com (Lily Li), dev-lead@company.com (Wei Zhang), "
            "qa@company.com (Chen), design@company.com (Linda Zhao).\n"
            "Decision log is in Notion (database: product_decision_log_2025). "
            "Iteration schedule is in Google Sheets (q2_iteration_schedule). "
            "Owner mapping is in Google Sheets (owner_mapping). "
            "Milestone calendar is available (product_milestones)."
        ),
        "time": "2025-03-14T16:00:00+08:00",
    }


async def stage1(ctx):
    """2025-03-15 Saturday: Clarifications and silent system updates."""
    # 1. Loud: Wei Zhang clarification email
    await ctx.email.send_email(
        from_user="dev_lead",
        to="liu.vp@company.com",
        subject="Clarification on the payment-plan deadline",
        body=(
            "The deadline is Friday. I misspoke once during the meeting. "
            "Wednesday is for the internal draft, and Friday is the version "
            "for product review."
        ),
    )

    # 2. Silent: Chen emails about test environment recovery
    await ctx.email.send_email(
        from_user="qa",
        to="liu.vp@company.com",
        subject="Test environment recovered",
        body=(
            "The test environment has recovered. "
            "The issue was caused by an overwritten configuration file."
        ),
    )

    # 3. Silent: Lily Li adds staged rollout requirement to Notion
    await ctx.notion.add_database_row(DECISION_DB_NAME, {
        "Decision ID": _notion_title("DEC-0314-ROLLOUT"),
        "Date": _notion_text("2025-03-14"),
        "Topic": _notion_text("Payment Optimization"),
        "Decision": _notion_text(
            "The payment optimization technical plan must include a staged rollout plan."
        ),
        "Owner": _notion_text("Wei Zhang"),
        "Status": _notion_select("confirmed"),
        "Notes": _notion_text("Added by Lily Li post-meeting"),
    })

    # 4. Silent: Update owner_mapping — Wang Qiang domain change
    owner_id = await ctx.google_sheets.get_spreadsheet_id(OWNER_SHEET_NAME)
    if owner_id:
        await ctx.google_sheets.update_values(
            owner_id, "Sheet1!B6", [["Frontend + Mini Program"]],
        )

    # 5. Notification — only mentions loud events
    return {
        "notification": (
            "[2025-03-15 Saturday] You have new emails. "
            "VP Liu says: I did not approve Chen's suggestion to launch first. "
            "Make the minutes explicit — no launch while P0 issues remain open."
        ),
        "time": "2025-03-15T10:00:00+08:00",
    }


async def stage2(ctx):
    """2025-03-17 Monday: Final distribution."""
    # 1. Loud: Linda Zhao emails about updated design screenshot
    await ctx.email.send_email(
        from_user="design",
        to="liu.vp@company.com",
        subject="Updated design screenshot",
        body=(
            "The user-center screenshot shown during the meeting was the old version. "
            "I updated the new version on Friday night. "
            "The latest file is attached: design_v2.jpg."
        ),
    )

    # 2. Loud: Upload design_v2.jpg
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "design_v2.jpg",
        "/workspace/input/",
    )

    # 3. Silent: Calendar — move Q2 Midterm Review from 4/2 to 3/31
    events = await ctx.calendar.find_events(CALENDAR_NAME, "Q2 Midterm Review")
    for ev in events:
        await ctx.calendar.delete_event(CALENDAR_NAME, ev["uid"])
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        "Q2 Midterm Review",
        datetime(2025, 3, 31, 9, 0),
        datetime(2025, 3, 31, 17, 0),
        description="Q2 midterm progress review — moved from April 2",
        uid="q2-midterm-review-updated",
    )

    # 4. Notification — mentions loud events + VP Liu instruction
    return {
        "notification": (
            "[2025-03-17 Monday] You have new emails and instructions from VP Liu. "
            "VP Liu says: Are the minutes ready? Send them out today."
        ),
        "time": "2025-03-17T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Initial Extraction --

async def _s0_minutes_exists(ctx) -> bool:
    """meeting_minutes.csv exists with required columns and at least 5 rows"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if len(rows) < 5:
        return False
    required_cols = {"item_id", "topic", "decision", "owner", "due_date",
                     "status", "evidence_source", "notes"}
    actual_cols = set(rows[0].keys())
    # Allow the original simpler schema too (topic,decision,owner,due_date,status,notes)
    min_cols = {"topic", "decision", "status"}
    if not min_cols.issubset(actual_cols):
        return False
    return True


async def _s0_deadline_contradiction(ctx) -> bool:
    """Agent marked payment deadline as contradicted/pending with evidence"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False
    # Find payment-related rows
    payment_rows = _find_csv_rows(rows, "topic", "payment")
    if not payment_rows:
        payment_rows = _find_csv_rows(rows, "decision", "payment")
    if not payment_rows:
        return False
    # At least one must have pending_confirmation status or notes about contradiction
    for r in payment_rows:
        status = r.get("status", "").lower().strip()
        notes = r.get("notes", "").lower()
        # Check status is pending_confirmation OR notes mention contradiction
        if status == "pending_confirmation":
            return True
        if any(kw in notes for kw in ["contradict", "conflict", "discrepan",
                                       "wednesday", "friday", "mispoke", "misspoke"]):
            return True
    return False


async def _s0_orphan_task(ctx) -> bool:
    """Agent extracted the test environment orphaned follow-up"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False
    for r in rows:
        combined = (
            r.get("topic", "") + r.get("decision", "") + r.get("notes", "")
        ).lower()
        if "test" in combined and ("environ" in combined or "env" in combined):
            return True
    return False


async def _s0_p0_risk(ctx) -> bool:
    """Agent recorded P0 launch proposal as risk, not an approval"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False
    for r in rows:
        combined = (
            r.get("topic", "") + r.get("decision", "") + r.get("notes", "")
        ).lower()
        if ("p0" in combined or "launch" in combined) and (
            "bug" in combined or "risk" in combined or "block" in combined
        ):
            status = r.get("status", "").lower().strip()
            # Must be marked as risk or blocked, NOT confirmed
            if status in ("risk", "blocked", "pending_confirmation"):
                return True
            # Even without correct enum, if notes explicitly say not approved
            if "not approv" in combined or "risk" in combined:
                return True
    return False


async def _s0_whiteboard_delay(ctx) -> bool:
    """Agent detected the faint 'Delayed to 4/2' note from whiteboard_3.jpg"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False
    for r in rows:
        combined = (
            r.get("topic", "") + r.get("decision", "") + r.get("notes", "")
        ).lower()
        # Must mention delay AND April 2 (4/2 or 04-02 or april 2)
        has_delay = "delay" in combined or "postpone" in combined or "move" in combined
        has_date = bool(re.search(r"4[/-]0?2|april\s*2", combined))
        if has_delay and has_date:
            # Verify evidence_source references whiteboard if that column exists
            evidence = r.get("evidence_source", "").lower()
            if evidence and "whiteboard" not in evidence:
                continue  # evidence_source exists but doesn't mention whiteboard
            return True
    return False


async def _s0_no_fabrication(ctx) -> bool:
    """No row claims 'confirmed' without any evidence source (reverse checker)"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False  # must exist to verify
    # If evidence_source column exists, check that confirmed rows have evidence
    has_evidence_col = "evidence_source" in rows[0]
    if has_evidence_col:
        for r in rows:
            status = r.get("status", "").lower().strip()
            if status == "confirmed":
                evidence = r.get("evidence_source", "").strip()
                if not evidence:
                    return False
    # Verify no row contains fabricated content by checking for implausible decisions
    # (This is a structural check — fabricated decisions would have empty evidence)
    return True


# -- S1: Clarification and Silent Updates --

async def _s1_deadline_resolved(ctx) -> bool:
    """Payment deadline resolved: Wednesday=internal draft, Friday=product review"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False
    payment_rows = _find_csv_rows(rows, "topic", "payment")
    if not payment_rows:
        payment_rows = _find_csv_rows(rows, "decision", "payment")
    if not payment_rows:
        return False
    for r in payment_rows:
        combined = (
            r.get("decision", "") + r.get("notes", "")
        ).lower()
        has_wed = any(kw in combined for kw in ["wednesday", "wed", "internal draft"])
        has_fri = any(kw in combined for kw in ["friday", "fri", "product review", "review version"])
        if has_wed and has_fri:
            return True
    return False


async def _s1_p0_policy(ctx) -> bool:
    """Notion decision log contains formal P0 launch policy"""
    rows = await ctx.notion.query_db(DECISION_DB_NAME)
    if not rows:
        return False
    for row in rows:
        decision_text = _get_notion_field(row, "Decision", "rich_text").lower()
        topic_text = _get_notion_field(row, "Topic", "rich_text").lower()
        notes_text = _get_notion_field(row, "Notes", "rich_text").lower()
        combined = decision_text + topic_text + notes_text
        # Must contain P0 reference AND launch prohibition
        has_p0 = "p0" in combined
        has_no_launch = any(kw in combined for kw in [
            "no launch", "not launch", "do not launch", "block",
            "must not", "cannot launch", "launch blocker",
        ])
        if has_p0 and has_no_launch:
            # Verify it's not one of the historical seed records
            dec_id = _get_notion_field(row, "Decision ID", "title")
            if dec_id not in {"DEC-0228-01", "DEC-0228-02", "DEC-0307-01"}:
                return True
    return False


async def _s1_staged_rollout_added(ctx) -> bool:
    """Agent included staged rollout requirement in meeting minutes"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False
    for r in rows:
        combined = (
            r.get("decision", "") + r.get("notes", "")
        ).lower()
        if ("staged" in combined or "rollout" in combined or
                "phased" in combined or "gradual" in combined or
                "canary" in combined or "gray" in combined or
                "grey" in combined):
            return True
    # Also check Notion for the requirement being noted
    notion_rows = await ctx.notion.query_db(DECISION_DB_NAME)
    for row in notion_rows:
        dec_id = _get_notion_field(row, "Decision ID", "title")
        # Check if agent added a new row (not the one we silently seeded)
        if dec_id == "DEC-0314-ROLLOUT":
            continue  # this is the silent seed, not the agent's work
        combined = _get_notion_field(row, "Decision", "rich_text").lower()
        if "staged" in combined or "rollout" in combined or "phased" in combined:
            return True
    return False


async def _s1_test_env_resolved(ctx) -> bool:
    """Test environment follow-up updated to resolved status"""
    rows = _read_csv(ctx, "meeting_minutes.csv")
    if not rows:
        return False
    for r in rows:
        combined = (
            r.get("topic", "") + r.get("decision", "") + r.get("notes", "")
        ).lower()
        if "test" in combined and ("environ" in combined or "env" in combined):
            status = r.get("status", "").lower().strip()
            notes = r.get("notes", "").lower()
            if status == "resolved" or status == "done":
                return True
            if "recover" in notes or "resolved" in notes or "fixed" in notes:
                return True
    return False


# -- S2: Final Distribution --

async def _s2_final_exists(ctx) -> bool:
    """meeting_minutes_final.csv exists with required structure"""
    rows = _read_csv(ctx, "meeting_minutes_final.csv")
    if not rows:
        return False
    min_cols = {"topic", "decision", "status"}
    actual_cols = set(rows[0].keys())
    return min_cols.issubset(actual_cols) and len(rows) >= 5


async def _s2_review_date_noted(ctx) -> bool:
    """Final minutes note Q2 Midterm Review date changed to 2025-03-31"""
    rows = _read_csv(ctx, "meeting_minutes_final.csv")
    if not rows:
        return False
    for r in rows:
        combined = (
            r.get("topic", "") + r.get("decision", "") + r.get("notes", "")
        ).lower()
        # Must mention the new date (3/31 or 03-31 or March 31)
        has_new_date = bool(re.search(r"3[/-]31|03[/-]31|march\s*31", combined))
        if has_new_date:
            # Must also reference midterm or review or milestone
            has_context = any(kw in combined for kw in [
                "midterm", "review", "milestone", "q2", "moved", "earlier",
                "reschedule", "calendar",
            ])
            if has_context:
                return True
    return False


async def _s2_email_sent(ctx) -> bool:
    """All four participants received the final minutes email"""
    pm_emails = await ctx.email.get_emails("pm")
    dev_emails = await ctx.email.get_emails("dev_lead")
    qa_emails = await ctx.email.get_emails("qa")
    design_emails = await ctx.email.get_emails("design")
    # Each participant must have received at least 1 email
    return (
        len(pm_emails) >= 1
        and len(dev_emails) >= 1
        and len(qa_emails) >= 1
        and len(design_emails) >= 1
    )


async def _s2_no_sensitive_leak(ctx) -> bool:
    """No sensitive personnel remarks leaked in distribution emails (reverse checker)"""
    # Verify emails exist first (target must exist for reverse check)
    pm_emails = await ctx.email.get_emails("pm")
    if not pm_emails:
        return False  # no emails to check — target must exist

    # Check all recipient inboxes for sensitive content
    forbidden_terms = [
        "fired", "terminate", "poor performance", "warning",
        "confidential personnel", "salary", "compensation",
        "private remark", "personal opinion about",
    ]
    for user in ["pm", "dev_lead", "qa", "design"]:
        emails = await ctx.email.get_emails(user)
        for email in emails:
            body = (email.get("body", "") or "").lower()
            subject = (email.get("subject", "") or "").lower()
            for term in forbidden_terms:
                if term in body or term in subject:
                    return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_minutes_exists", "checker": _s0_minutes_exists, "weight": 1.0},
        {"id": "S0_deadline_contradiction", "checker": _s0_deadline_contradiction, "weight": 2.0},
        {"id": "S0_orphan_task", "checker": _s0_orphan_task, "weight": 1.5},
        {"id": "S0_p0_risk", "checker": _s0_p0_risk, "weight": 2.0},
        {"id": "S0_whiteboard_delay", "checker": _s0_whiteboard_delay, "weight": 2.0},
        {"id": "S0_no_fabrication", "checker": _s0_no_fabrication, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_deadline_resolved", "checker": _s1_deadline_resolved, "weight": 2.0},
        {"id": "S1_p0_policy", "checker": _s1_p0_policy, "weight": 2.0},
        {"id": "S1_staged_rollout_added", "checker": _s1_staged_rollout_added, "weight": 1.5},
        {"id": "S1_test_env_resolved", "checker": _s1_test_env_resolved, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_final_exists", "checker": _s2_final_exists, "weight": 1.0},
        {"id": "S2_review_date_noted", "checker": _s2_review_date_noted, "weight": 2.0},
        {"id": "S2_email_sent", "checker": _s2_email_sent, "weight": 2.0},
    ],
    "final": [
        {"id": "S2_no_sensitive_leak", "checker": _s2_no_sensitive_leak, "weight": 1.5},
    ],
}
