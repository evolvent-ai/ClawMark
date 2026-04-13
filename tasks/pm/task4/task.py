"""Product Manager — StarLan Collab v2.5 release plan.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: initial scope & schedule → effort update & silent backlog change → freeze constraint discovery
15 checkers (0 keyword-search)
"""

import json
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────

BACKLOG_DB_NAME = "product_backlog"

BACKLOG_DB_SCHEMA = {
    "Backlog ID": {"title": {}},
    "Title": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "in_progress"}, {"name": "not_started"},
    ]}},
    "Priority": {"select": {"options": [
        {"name": "P0"}, {"name": "P1"}, {"name": "P2"}, {"name": "P3"},
    ]}},
    "Target Version": {"select": {"options": [
        {"name": "v2.5"}, {"name": "v2.6"}, {"name": "—"},
    ]}},
    "Decision Source": {"rich_text": {}},
    "Last Updated": {"rich_text": {}},
    "Assignee": {"rich_text": {}},
    "Module": {"rich_text": {}},
}

INITIAL_BACKLOG_ROWS = [
    {
        "id": "PB-001", "title": "Cross-dept Approval Flow Refactor",
        "status": "in_progress", "priority": "P0", "version": "v2.5",
        "source": "roadmap_sync", "updated": "2025-03-21",
        "assignee": "William Zhang", "module": "approval",
    },
    {
        "id": "PB-002", "title": "Smart Calendar Assistant",
        "status": "not_started", "priority": "P0", "version": "v2.5",
        "source": "roadmap_sync", "updated": "2025-03-21",
        "assignee": "William Zhang", "module": "smart_schedule",
    },
    {
        "id": "PB-003", "title": "Cross-org Collaboration Space",
        "status": "not_started", "priority": "P1", "version": "—",
        "source": "roadmap_sync", "updated": "2025-03-21",
        "assignee": "Fiona Liu", "module": "cross_org",
    },
    {
        "id": "PB-004", "title": "AI Meeting Notes",
        "status": "not_started", "priority": "P2", "version": "—",
        "source": "roadmap_sync", "updated": "2025-03-21",
        "assignee": "William Zhang", "module": "ai_meeting",
    },
    {
        "id": "PB-005", "title": "Mobile Notification Optimization",
        "status": "not_started", "priority": "P1", "version": "v2.5",
        "source": "roadmap_sync", "updated": "2025-03-21",
        "assignee": "Fiona Liu", "module": "mobile_notify",
    },
    {
        "id": "PB-006", "title": "File Version Management",
        "status": "not_started", "priority": "P2", "version": "v2.5",
        "source": "roadmap_sync", "updated": "2025-03-21",
        "assignee": "Fiona Liu", "module": "file_version",
    },
    {
        "id": "PB-007", "title": "Approval Data Dashboard",
        "status": "not_started", "priority": "P3", "version": "—",
        "source": "roadmap_sync", "updated": "2025-03-21",
        "assignee": "Fiona Liu", "module": "approval_dashboard",
    },
]

# Google Sheets: release_capacity_q2 — all data in Sheet1 with section headers
# Rows 1-13: team_capacity; Row 14: section; Rows 15-18: committed_allocations;
# Row 19: section; Rows 20-21: shared_constraints (header + initially empty)
TEAM_CAPACITY_HEADER = ["Name", "Team", "Role", "Q2 Available Days", "Notes"]
TEAM_CAPACITY_ROWS = [
    ["William Zhang", "Backend", "Lead", "55", ""],
    ["Gary Zhao", "Backend", "Senior", "60", ""],
    ["Tom Sun", "Backend", "Mid", "60", ""],
    ["Leo Zhou", "Backend", "Mid", "55", "4/14-4/18 annual leave"],
    ["Fiona Liu", "Frontend", "Lead", "55", ""],
    ["Jill Lin", "Frontend", "Senior", "60", ""],
    ["Frank Yang", "Frontend", "Mid", "58", ""],
    ["Sean Wang", "QA", "Lead", "55", ""],
    ["Mike Li", "QA", "Senior", "48", "4/7-4/18 wedding leave"],
    ["Tina Hu", "QA", "Mid", "60", ""],
    ["Harry Han", "QA", "Junior", "60", ""],
    ["Sam Sun", "SRE", "Lead", "55", ""],
]

ALLOCATIONS_HEADER = ["Project", "Team", "Headcount", "Period", "Business Days"]
ALLOCATIONS_ROWS = [
    ["v2.4.3 hotfix", "Backend", "2", "3/24-3/28", "5"],
    ["Security compliance audit", "Backend", "1", "4/1-4/30", "22"],
    ["Security compliance audit", "SRE", "1", "4/1-4/15", "11"],
]

CONSTRAINTS_HEADER = ["date", "type", "reason"]

CAL_NAME = "starlan-v25-milestones"
SHEETS_NAME = "release_capacity_q2"

# Row offset for shared_constraints data rows (Sheet1, 1-indexed):
# Row 20 = constraints header; Row 21 = first data row (S2 will write here)
_CONSTRAINTS_DATA_ROW = 21


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


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
    return ""


async def _find_notion_row(ctx, db_name: str, backlog_id: str) -> dict:
    """Find a Notion row by Backlog ID (title field)."""
    rows = await ctx.notion.query_db(db_name)
    for row in rows:
        bid = _get_notion_field(row, "Backlog ID", "title")
        if bid == backlog_id:
            return row
    return None


def _load_release_plan(ctx) -> dict:
    """Load and parse workspace/output/release_plan.json."""
    path = ctx.workspace / "output" / "release_plan.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_feature_in_scope(plan: dict, feature_id: str) -> dict:
    """Return the in_scope entry for a given feature_id, or None."""
    in_scope = plan.get("scope_decision", {}).get("in_scope", [])
    for entry in in_scope:
        if entry.get("feature_id", "").upper() == feature_id.upper():
            return entry
    return None


def _get_feature_out_scope(plan: dict, feature_id: str) -> dict:
    """Return the out_of_scope entry for a given feature_id, or None."""
    out_scope = plan.get("scope_decision", {}).get("out_of_scope", [])
    for entry in out_scope:
        if entry.get("feature_id", "").upper() == feature_id.upper():
            return entry
    return None


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "pm_task4",
    "name": "Product Manager Release Planning — StarLan Collab v2.5",
    "category": "project_and_product_manager",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "Yue Chen, Senior Product Manager at StarLan Tech",
    "tags": [
        "product-manager", "release-planning", "multimodal", "audio", "visual-trap",
        "cross-source-contradiction", "silent-event", "notion", "calendar",
        "google-sheets", "schedule-recalculation", "dependency-chain",
    ],
    "env_config": {
        "email": {
            "users": {
                "chenyue": {"email": "chenyue@starlan.com", "password": "chenyue_pwd"},
                "liyan": {"email": "liyan@starlan.com", "password": "liyan_pwd"},
                "sales_ops": {"email": "sales-ops@starlan.com", "password": "sales_ops_pwd"},
                "zhangwei": {"email": "zhangwei@starlan.com", "password": "zhangwei_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "pm_task4",
        },
    },
}

PROMPT = "Check your email and workspace for new messages and prepare the v2.5 release plan."


# ── Stage Functions ────────────────────────────────────────────────

async def stage0(ctx):
    """2025-03-27: Initial release planning kickoff.

    Loud events:
      - email-001: Ian Li (VP) email asking to finalize the v2.5 schedule,
        includes client_escalation.pdf (PDF with handwritten annotations visible only in image)
      - email-002: Sales Ops email with competitor_alert.png (FlyPigeon Collab 3.0 screenshot)
      - Feishu group messages: audio standup (team_standup_0324.mp3) and
        whiteboard image (backlog_priorities.png) from Linda Chen

    Silent events: none in stage0
    """
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create output directory
    await ctx.fs._sandbox.exec("mkdir -p /workspace/output")

    # 3. Create Notion product backlog database + seed 7 records
    await ctx.notion.create_page("StarLan Collab Product Backlog")
    await ctx.notion.create_database(BACKLOG_DB_NAME, BACKLOG_DB_SCHEMA)
    for rec in INITIAL_BACKLOG_ROWS:
        await ctx.notion.add_database_row(BACKLOG_DB_NAME, {
            "Backlog ID": _notion_title(rec["id"]),
            "Title": _notion_text(rec["title"]),
            "Status": _notion_select(rec["status"]),
            "Priority": _notion_select(rec["priority"]),
            "Target Version": _notion_select(rec["version"]),
            "Decision Source": _notion_text(rec["source"]),
            "Last Updated": _notion_text(rec["updated"]),
            "Assignee": _notion_text(rec["assignee"]),
            "Module": _notion_text(rec["module"]),
        })

    # 4. Create Google Sheets release_capacity_q2 with all capacity/constraint data
    sheet_info = await ctx.google_sheets.create_spreadsheet(SHEETS_NAME)
    sheet_id = sheet_info["sheet_id"]
    # Section 1: team_capacity (rows 1-13)
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:E13",
        [TEAM_CAPACITY_HEADER] + TEAM_CAPACITY_ROWS,
    )
    # Section separator (row 14)
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A14:E14",
        [["committed_allocations", "", "", "", ""]],
    )
    # Section 2: committed_allocations (rows 15-18)
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A15:E18",
        [ALLOCATIONS_HEADER] + ALLOCATIONS_ROWS,
    )
    # Section separator (row 19)
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A19:C19",
        [["shared_constraints", "", ""]],
    )
    # Section 3: shared_constraints (row 20 = header, row 21+ = data, initially empty)
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A20:C20",
        [CONSTRAINTS_HEADER],
    )

    # 5. Create Google Calendar for v2.5 milestones
    await ctx.calendar.create_calendar(CAL_NAME)

    # 6. Seed emails: VP escalation + competitor alert
    await ctx.email.send_email(
        from_user="liyan",
        to="chenyue@starlan.com",
        subject="Finalize v2.5 schedule this week",
        body=(
            "Yue, the v2.5 schedule must be finalized this week. "
            "I reviewed DingHe Group's escalation -- the approval flow must be in this release. "
            "Also, sales has been repeatedly asking about \"Smart Calendar,\" so please make "
            "that section clear in your plan. "
            "Send me a confirmation email once the plan is ready; "
            "I need to review it with the CEO by Friday.\n\n"
            "Attachment: input/client_escalation.pdf (DingHe Group escalation letter)"
        ),
    )
    await ctx.email.send_email(
        from_user="sales_ops",
        to="chenyue@starlan.com",
        subject="FlyPigeon 3.0 media screenshot",
        body=(
            "FlyPigeon's press release came out this week, and clients have been asking "
            "about it a lot. Please review this screenshot when working on the schedule.\n\n"
            "Attachment: input/competitor_alert.png (FlyPigeon 3.0 press screenshot)"
        ),
    )

    # 7. Notification — includes Feishu group chat messages (audio + image)
    return {
        "notification": (
            "[2025-03-27 Thursday] You have new emails in your inbox and new messages "
            "in the Feishu project group. Ian Li (VP Product) is asking you to finalize "
            "the v2.5 release plan this week.\n\n"
            "--- Feishu Group Chat: StarLan Collab v2.5 Project Group ---\n\n"
            "[2025-03-24 09:15] William Zhang (Backend Lead):\n"
            "[Audio: input/team_standup_0324.mp3]\n"
            "\"Morning standup recording, some info about current dev progress "
            "and scheduling notes. Please listen.\"\n\n"
            "[2025-03-24 10:00] Linda Chen (Design Lead):\n"
            "[Image: input/backlog_priorities.png]\n"
            "\"Here's the whiteboard photo from yesterday's priority workshop. "
            "This was our ranking discussion result.\"\n\n"
            "--- End of Feishu Messages ---\n\n"
            "Please do the following:\n"
            "1. Read your email inbox (especially Ian Li's email with the PDF attachment "
            "and Sales Ops' competitor screenshot).\n"
            "2. Listen to the audio standup and review the backlog priority whiteboard image.\n"
            "3. Check the Notion Product Backlog (database: product_backlog) for current "
            "backlog status. Fix any incorrect data you find.\n"
            "4. Review the feature dependency table (input/feature_dependency.csv) and the "
            "scoring policy (input/scoring_policy.pdf).\n"
            "5. Score each feature (F-001 through F-007) using the priority scoring formula "
            "in the policy (threshold ≥ 6.0 for inclusion). Use the cross-referenced "
            "competitor and client escalation data to fill in the score dimensions.\n"
            "6. Build the v2.5 release schedule: calculate dev/test dates for each "
            "in-scope feature (business days only, Mon–Fri). Respect feature dependencies "
            "(see feature_dependency.csv). Check team capacity from Google Sheets "
            "(release_capacity_q2).\n"
            "7. Output the completed release plan to output/release_plan.json "
            "(follow the release_plan_template.json structure in your workspace).\n"
            "8. Create 4 milestone calendar events in Google Calendar "
            "(calendar: starlan-v25-milestones): kickoff, alpha, beta, and release.\n"
            "9. Send a confirmation email to Ian Li (liyan@starlan.com) "
            "with the plan summary and key risks.\n\n"
            "Your email: chenyue@starlan.com. "
            "VP Product Ian Li: liyan@starlan.com. "
            "Backend Lead William Zhang: zhangwei@starlan.com. "
            "Product Backlog is in Notion (product_backlog). "
            "Team capacity is in Google Sheets (release_capacity_q2). "
            "Use Google Calendar (starlan-v25-milestones) for milestone events."
        ),
        "time": "2025-03-27T09:00:00+08:00",
    }


async def stage1(ctx):
    """2025-03-31: Effort update from backend lead + silent VP backlog change.

    Loud events:
      - email-003: William Zhang email — F-001 remaining effort reduced from 11 to 8 days
        (extra effort 5 days → 2 days; 6 + 2 = 8 business days remaining)

    Silent events:
      - Notion PB-004 (AI Meeting Notes): VP silently updates priority P2→P1,
        target_version '—'→'v2.5', decision_source 'roadmap_sync'→'VP_decision',
        last_updated '2025-03-21'→'2025-03-31'
    """
    # 1. Loud: William Zhang sends updated effort estimate
    await ctx.email.send_email(
        from_user="zhangwei",
        to="chenyue@starlan.com",
        subject="Approval flow refactor effort update",
        body=(
            "Yue, here's an update on the approval flow refactor estimate.\n\n"
            "The permission model adjustment we previously estimated at 5 extra business days -- "
            "over the weekend we re-evaluated the approach and found we can reuse the existing "
            "RBAC framework. The extra effort is now reduced from 5 days to 2 days.\n\n"
            "So the approval flow refactor remaining effort is now 6 + 2 = 8 business days "
            "(previously 6 + 5 = 11 days).\n\n"
            "Please update the schedule on your end accordingly."
        ),
    )

    # 2. Silent: VP adjusts PB-004 (AI Meeting Notes) to P1 + v2.5 in Notion
    #    Agent is not notified; must proactively re-check Notion to discover this.
    pb004_row = await _find_notion_row(ctx, BACKLOG_DB_NAME, "PB-004")
    if pb004_row:
        await ctx.notion.update_db_row(pb004_row["id"], {
            "Priority": _notion_select("P1"),
            "Target Version": _notion_select("v2.5"),
            "Decision Source": _notion_text("VP_decision"),
            "Last Updated": _notion_text("2025-03-31"),
        })

    # 3. Notification — mentions loud event only; does NOT mention Notion change
    return {
        "notification": (
            "[2025-03-31 Monday] You have a new email from William Zhang (Backend Lead) "
            "with an update on the approval flow refactor estimate.\n\n"
            "Please check your inbox and update the release plan accordingly. "
            "Remember to re-verify all data sources for any changes before finalizing.\n\n"
            "Update output/release_plan.json and the calendar events with the revised schedule."
        ),
        "time": "2025-03-31T09:00:00+08:00",
    }


async def stage2(ctx):
    """2025-04-02: Ian Li Feishu reminder + silent Google Sheets release freeze entry.

    Loud events:
      - Ian Li Feishu message: CEO wants to see the plan Friday, re-check constraints

    Silent events:
      - Google Sheets shared_constraints: new row appended —
        date=2025-05-23, type=release_freeze, reason="Company disaster recovery drill,
        no production releases allowed all day"
    """
    # 1. Silent: Append release freeze row to shared_constraints (row 21)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(SHEETS_NAME)
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, f"Sheet1!A{_CONSTRAINTS_DATA_ROW}:C{_CONSTRAINTS_DATA_ROW}",
            [["2025-05-23", "release_freeze",
              "Company disaster recovery drill, no production releases allowed all day"]],
        )

    # 2. Loud: Ian Li sends Feishu message asking to reconfirm release date + constraints
    #    (Feishu is simulated via the notification text)
    return {
        "notification": (
            "[2025-04-02 Wednesday] New message from Ian Li (VP Product) in the "
            "StarLan Collab v2.5 Feishu group:\n\n"
            "--- Feishu Group Chat: StarLan Collab v2.5 Project Group ---\n\n"
            "[2025-04-02 09:00] Ian Li (VP Product):\n"
            "\"Yue, the CEO wants to see the final version this Friday. "
            "Please confirm the release date and release constraints one more time -- "
            "check if there are any new constraints. "
            "Once confirmed, update the plan and calendar.\"\n\n"
            "--- End of Feishu Messages ---\n\n"
            "Please re-check all constraint data sources (including Google Sheets "
            "release_capacity_q2) for any new entries, and confirm the final release date. "
            "Update output/release_plan.json and the calendar release milestone event accordingly."
        ),
        "time": "2025-04-02T09:00:00+08:00",
    }


# ── Checker Functions ──────────────────────────────────────────────

# ── Stage 0: Initial Release Plan ─────────────────────────────────

async def _s0_competitor_release_date(ctx) -> bool:
    """release_plan.json competitor_context.competitor_release_date == '2025-04-18'.

    Must read competitor_alert.png (image-only) to extract FlyPigeon's release date.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    date = plan.get("competitor_context", {}).get("competitor_release_date", "")
    return date == "2025-04-18"


async def _s0_client_renewal_deadline(ctx) -> bool:
    """release_plan.json client_escalation.renewal_deadline == '2025-07-01'.

    Must read client_escalation.pdf handwritten annotation (visual-only) to extract
    DingHe Group's contract renewal deadline.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    deadline = plan.get("client_escalation", {}).get("renewal_deadline", "")
    return deadline == "2025-07-01"


async def _s0_scope_decision(ctx) -> bool:
    """F-001, F-002, F-005 all in in_scope; F-003, F-004, F-006, F-007 all out_of_scope.

    Verified against the priority scoring threshold (≥6.0):
    F-001=6.2, F-002=6.6, F-005=6.0 qualify; F-003=4.1, F-004=4.1, F-006=4.0, F-007=2.0 do not.
    Also verifies PB-006 (F-006, File Version Management) is NOT in v2.5 scope (red line R1).
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    in_scope_ids = {
        e.get("feature_id", "").upper()
        for e in plan.get("scope_decision", {}).get("in_scope", [])
    }
    out_scope_ids = {
        e.get("feature_id", "").upper()
        for e in plan.get("scope_decision", {}).get("out_of_scope", [])
    }
    required_in = {"F-001", "F-002", "F-005"}
    required_out = {"F-003", "F-004", "F-006", "F-007"}
    return required_in <= in_scope_ids and required_out <= out_scope_ids


async def _s0_f001_dev_end(ctx) -> bool:
    """release_plan.json F-001 dev_end == '2025-04-10'.

    F-001 has 11 remaining business days from 2025-03-27 (kickoff).
    Extra effort = 6 backend remaining + 5 extra days = 11 days.
    11 business days from 2025-03-27 → skip weekends (4/5-4/6) → ends 2025-04-10.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    f001 = _get_feature_in_scope(plan, "F-001")
    if not f001:
        return False
    return f001.get("dev_end", "") == "2025-04-10"


async def _s0_milestone_release(ctx) -> bool:
    """release_plan.json milestones.release == '2025-05-28'.

    Critical-path end = F-002 test_end = 2025-05-20; release = next Wed after 1-week buffer
    = 2025-05-28 (alpha 2025-05-14, beta 2025-05-21, release 2025-05-28).
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    release = plan.get("milestones", {}).get("release", "")
    return release == "2025-05-28"


async def _s0_calendar_milestone(ctx) -> bool:
    """Google Calendar starlan-v25-milestones has a kickoff event on 2025-03-27.

    Agent must create 4 milestone events in the designated calendar;
    we verify kickoff as the anchor point, restricted to the correct calendar.
    """
    try:
        events = await ctx.calendar.get_events(CAL_NAME)
    except Exception:
        return False
    for event in events:
        summary = event.get("summary", "").lower()
        dtstart = str(event.get("dtstart", ""))
        has_kickoff = "kickoff" in summary or "kick-off" in summary or "kick off" in summary
        has_date = "2025-03-27" in dtstart
        if has_kickoff and has_date:
            return True
    return False


# ── Stage 1: Effort Update & Silent Backlog Change ─────────────────

async def _s1_f001_dev_end_updated(ctx) -> bool:
    """release_plan.json F-001 dev_end == '2025-04-07'.

    After effort reduction 11→8 days: 8 business days from 2025-03-27
    → skip weekend 4/5-4/6 → ends 2025-04-07.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    f001 = _get_feature_in_scope(plan, "F-001")
    if not f001:
        return False
    return f001.get("dev_end", "") == "2025-04-07"


async def _s1_f002_chain_recalculated(ctx) -> bool:
    """release_plan.json F-002 dev_start == '2025-04-08'.

    F-002 depends on F-001. After F-001 dev_end shifts to 2025-04-07,
    F-002 dev_start must shift to next business day = 2025-04-08.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    f002 = _get_feature_in_scope(plan, "F-002")
    if not f002:
        return False
    return f002.get("dev_start", "") == "2025-04-08"


async def _s1_milestone_release_updated(ctx) -> bool:
    """release_plan.json milestones.release == '2025-05-23'.

    After F-001 effort reduction: F-002 test_end = 2025-05-15;
    milestones shift to alpha=2025-05-09, beta=2025-05-16, release=2025-05-23.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    release = plan.get("milestones", {}).get("release", "")
    return release == "2025-05-23"


async def _s1_pb004_silent_notion(ctx) -> bool:
    """Agent discovered the silent VP decision on PB-004 and reflected it in the JSON.

    Silent VP decision: PB-004 (AI Meeting Notes) upgraded to P1+v2.5.
    Agent must proactively re-check Notion (SOUL principle: more recent + higher authority).
    We verify the agent's output JSON has F-004 in_scope with a non-empty override_reason,
    proving the agent acted on the Notion change — not just that the framework set it.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    f004 = _get_feature_in_scope(plan, "F-004")
    if not f004:
        return False
    # Agent must document the override reason (VP decision override of default threshold)
    override = str(f004.get("override_reason", "")).strip()
    return len(override) > 0


async def _s1_f004_in_scope(ctx) -> bool:
    """release_plan.json F-004 appears in in_scope.

    VP_decision (silent Notion update) overrides the default threshold for F-004.
    Agent must discover PB-004 change in Notion and include F-004 in the plan.
    Cross-verifies JSON reflects the Notion-discovered VP decision.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    # Verify F-004 is in scope
    f004 = _get_feature_in_scope(plan, "F-004")
    if not f004:
        return False
    # Cross-verify: Notion PB-004 must also reflect the VP decision
    pb004_row = await _find_notion_row(ctx, BACKLOG_DB_NAME, "PB-004")
    if not pb004_row:
        return False
    source = _get_notion_field(pb004_row, "Decision Source", "rich_text")
    return source == "VP_decision"


# ── Stage 2: Freeze Constraint Discovery ──────────────────────────

async def _s2_release_postponed(ctx) -> bool:
    """release_plan.json milestones.release == '2025-05-26'.

    2025-05-23 is a release_freeze day (Google Sheets silent update).
    5/24=Sat, 5/25=Sun → next business day = 2025-05-26 (Mon).
    Red line R2: release cannot fall on a freeze day.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    release = plan.get("milestones", {}).get("release", "")
    return release == "2025-05-26"


async def _s2_freeze_constraint_applied(ctx) -> bool:
    """release_plan.json constraints_applied contains a structured entry for 2025-05-23 freeze.

    Agent must read Google Sheets shared_constraints (silent update), discover
    the freeze date, and record it in constraints_applied.
    Requires a dict entry with date='2025-05-23' and type containing 'freeze'.
    """
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    constraints = plan.get("constraints_applied", [])
    if not constraints:
        return False
    for entry in constraints:
        if isinstance(entry, dict):
            date_val = str(entry.get("date", ""))
            type_val = str(entry.get("type", "")).lower()
            if date_val == "2025-05-23" and "freeze" in type_val:
                return True
        elif isinstance(entry, str):
            # Accept string entries that contain both the date and freeze keyword
            if "2025-05-23" in entry and "freeze" in entry.lower():
                return True
    return False


# ── Final: Red Line Checks ─────────────────────────────────────────

async def _final_pb006_deferred(ctx) -> bool:
    """Red line R1: Notion PB-006 (File Version Management) must NOT be in v2.5.

    Initial state has PB-006 target_version='v2.5' — a stale entry that contradicts
    the scoring decision (F-006 score=4.0 < 6.0 threshold).
    VP audio explicitly deferred File Version Management to v2.6.
    Agent must correct PB-006 target_version to 'v2.6' or '—', not keep 'v2.5'.
    """
    pb006_row = await _find_notion_row(ctx, BACKLOG_DB_NAME, "PB-006")
    if not pb006_row:
        return False
    version = _get_notion_field(pb006_row, "Target Version", "select")
    return version != "v2.5"


async def _final_vp_email_sent(ctx) -> bool:
    """Red line R3: Ian Li inbox has a confirmation email from Yue Chen (chenyue@starlan.com).

    Agent must send Ian Li a plan confirmation email after finalizing the release plan.
    Also cross-checks that the plan JSON has non-empty resource_risks (≥1 risk documented),
    verifying the email was not sent with an empty plan.
    """
    # Check Ian Li received an email from chenyue
    try:
        emails = await ctx.email.get_emails("liyan")
    except Exception:
        return False

    email_sent = False
    for email in emails:
        sender = email.get("from", "")
        if isinstance(sender, dict):
            sender = sender.get("email", "")
        sender = str(sender).lower()
        if "chenyue" in sender or "chenyue@starlan" in sender:
            email_sent = True
            break

    if not email_sent:
        return False

    # Cross-verify: release plan must have at least 1 real documented risk
    # (not just the empty template placeholder)
    plan = _load_release_plan(ctx)
    if not plan:
        return False
    risks = plan.get("resource_risks", [])
    if not risks:
        return False
    # At least one risk must have non-empty description and impact fields
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        desc = str(risk.get("description", "")).strip()
        impact = str(risk.get("impact", "")).strip()
        if desc and impact:
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_competitor_release_date", "checker": _s0_competitor_release_date, "weight": 2.0},
        {"id": "S0_client_renewal_deadline", "checker": _s0_client_renewal_deadline, "weight": 2.0},
        {"id": "S0_scope_decision", "checker": _s0_scope_decision, "weight": 2.5},
        {"id": "S0_f001_dev_end", "checker": _s0_f001_dev_end, "weight": 1.5},
        {"id": "S0_milestone_release", "checker": _s0_milestone_release, "weight": 1.5},
        {"id": "S0_calendar_milestone", "checker": _s0_calendar_milestone, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_f001_dev_end_updated", "checker": _s1_f001_dev_end_updated, "weight": 2.0},
        {"id": "S1_f002_chain_recalculated", "checker": _s1_f002_chain_recalculated, "weight": 2.0},
        {"id": "S1_milestone_release_updated", "checker": _s1_milestone_release_updated, "weight": 1.5},
        {"id": "S1_pb004_silent_notion", "checker": _s1_pb004_silent_notion, "weight": 2.5},
        {"id": "S1_f004_in_scope", "checker": _s1_f004_in_scope, "weight": 2.0},
    ],
    "stage2": [
        {"id": "S2_release_postponed", "checker": _s2_release_postponed, "weight": 3.0},
        {"id": "S2_freeze_constraint_applied", "checker": _s2_freeze_constraint_applied, "weight": 2.0},
    ],
    "final": [
        {"id": "FINAL_pb006_deferred", "checker": _final_pb006_deferred, "weight": 2.0},
        {"id": "FINAL_vp_email_sent", "checker": _final_vp_email_sent, "weight": 1.5},
    ],
}
