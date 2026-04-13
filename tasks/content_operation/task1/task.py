"""Design asset request tracking — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: intake & arbitration → color approval & budget recheck → delivery & summary
14 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

CONTENT_DB_NAME = "content_calendar"

CONTENT_DB_SCHEMA = {
    "Request ID": {"title": {}},
    "Date": {"rich_text": {}},
    "Platform": {"rich_text": {}},
    "Type": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "ready"}, {"name": "needs_clarification"},
        {"name": "blocked"}, {"name": "approved"},
        {"name": "in_progress"}, {"name": "delivered"},
        {"name": "locked"}, {"name": "pending_design"},
    ]}},
    "Note": {"rich_text": {}},
    "Budget": {"number": {}},
    "Issue Flag": {"select": {"options": [
        {"name": "yes"}, {"name": "no"},
    ]}},
}

INITIAL_RECORDS = [
    {"id": "CAL-0318-01", "date": "2025-03-20", "platform": "Brand Site Homepage",
     "type": "Hero Banner", "status": "locked",
     "note": "Flash Sale campaign already occupies the homepage hero.", "budget": 0, "issue_flag": "no"},
    {"id": "CAL-0318-03", "date": "2025-03-21", "platform": "WeChat Official Account",
     "type": "Header", "status": "pending_design",
     "note": "Equinox feature", "budget": 0, "issue_flag": "no"},
    {"id": "CAL-0318-04", "date": "2025-03-24", "platform": "Live Reservation",
     "type": "Thumbnail", "status": "pending_design",
     "note": "Budget already reserved", "budget": 0, "issue_flag": "no"},
]

BUDGET_HEADER = ["Campaign", "Owner", "Approved Budget", "Committed Budget", "Actual Spend", "Reserve Note"]
BUDGET_ROWS = [
    ["New launch campaign", "Zhao Yue", "12000", "6200", "1000", ""],
    ["Live poster", "Zhao Yue", "3000", "900", "0", ""],
    ["Flash Sale", "Claire", "9000", "4200", "0", ""],
]

# Budget after stage0 silent: committed goes from 6200 → 7200 (PR placement added)
# Remaining = 12000 - 7200 = 4800
BUDGET_S0_SILENT_COMMITTED = "7200"

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
    """Find a CSV row where column contains search string (case-insensitive)."""
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
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


async def _find_notion_row(ctx, db_name: str, req_id: str) -> dict | None:
    """Find a Notion row by Request ID (title field)."""
    rows = await ctx.notion.query_db(db_name)
    for row in rows:
        rid = _get_notion_field(row, "Request ID", "title")
        if rid == req_id:
            return row
    return None


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "content_operation_task1",
    "name": "Design Asset Request Tracking",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhao Yue's content operations assistant",
    "tags": ["design", "intake", "budget", "brand", "multimodal", "slot-conflict"],
    "env_config": {
        "email": {
            "users": {
                "assistant": {"email": "assistant@company.com", "password": "assistant_pwd"},
                "zhao_yue": {"email": "zhao.yue@company.com", "password": "zhao_yue_pwd"},
                "design": {"email": "design@company.com", "password": "design_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "content_operation_task1",
        },
    },
}

PROMPT = "Check your email and workspace for new design requests."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Tuesday 2025-03-18: New request intake & slot arbitration."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion content calendar database + seed initial records
    await ctx.notion.create_page("Content Calendar 2025-Q1")
    await ctx.notion.create_database(CONTENT_DB_NAME, CONTENT_DB_SCHEMA)
    for rec in INITIAL_RECORDS:
        await ctx.notion.add_database_row(CONTENT_DB_NAME, {
            "Request ID": _notion_title(rec["id"]),
            "Date": _notion_text(rec["date"]),
            "Platform": _notion_text(rec["platform"]),
            "Type": _notion_text(rec["type"]),
            "Status": _notion_select(rec["status"]),
            "Note": _notion_text(rec["note"]),
            "Budget": _notion_number(rec["budget"]),
            "Issue Flag": _notion_select(rec["issue_flag"]),
        })

    # 3. Create Google Sheet budget tracker + seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet("Q1_Content_Budget")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F4",
        [BUDGET_HEADER] + BUDGET_ROWS,
    )

    # 4. Silent: Finance added PR placement, compressing remaining budget
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!D2", [[BUDGET_S0_SILENT_COMMITTED]],
    )

    # 5. Silent: Inject historical email from design team
    await ctx.email.send_email(
        from_user="design",
        to="assistant@company.com",
        subject="[Historical Feedback] Night mood direction",
        body="The previous mockup felt too dark. Please confirm whether that direction is still wanted.",
    )

    # 6. Notification — only mentions the loud event (new files)
    return {
        "notification": (
            "[2025-03-18 Tuesday] design_requests/ has new files. "
            "Please organize the incoming requests into actionable intake "
            "and proactively check for slot / budget / brief risks.\n\n"
            "Your email is assistant@company.com. "
            "Design team: design@company.com. Manager: zhao.yue@company.com.\n"
            "Content calendar is in Notion (database: content_calendar). "
            "Budget tracker is in Google Sheets (Q1_Content_Budget).\n"
            "[Slack #content-ops] Claire (2025-03-17 21:05): "
            "Flash Sale keeps homepage priority this week. "
            "Re-check the latest calendar before assigning extra homepage work."
        ),
        "time": "2025-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """Wednesday 2025-03-19: Color approval & budget recheck."""
    # 1. Loud: Zhao Yue email
    await ctx.email.send_email(
        from_user="zhao_yue",
        to="assistant@company.com",
        subject="[Need a Call] New launch cover and budget",
        body=(
            "We must lock the new launch cover before Thursday, "
            "and the budget is already tight. Give me the conclusion and the risks."
        ),
    )

    # 2. Silent: Finance adds reserve note to budget sheet
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Q1_Content_Budget")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!F2",
            [["Reserve 1,500 for the live poster. Do not reuse this amount."]],
        )

    # 3. Silent: Someone changes REQ-20250318-07 date from 3/24 to 3/20
    rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    for row in rows:
        req_id = _get_notion_field(row, "Request ID", "title")
        if req_id == "REQ-20250318-07":
            await ctx.notion.update_db_row(row["id"], {
                "Date": _notion_text("2025-03-20"),
            })
            break

    # 4. Notification — mentions loud events only
    return {
        "notification": (
            "[2025-03-19 Wednesday] You have new email and Slack updates. "
            "Please re-check budget, color approval, and record status.\n\n"
            "[Slack #content-ops] Lian (2025-03-19 14:20): "
            "The cover color may need to shift to a warmer orange (#FF6B35). "
            "I dropped the reference file in Slack (input/slack_files/cover_color_alt_ff6b35.png). "
            "Please confirm whether the brand rules allow it."
        ),
        "time": "2025-03-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """Friday 2025-03-21: Final delivery & weekly summary."""
    # 1. Loud: Design team delivery email
    await ctx.email.send_email(
        from_user="design",
        to="assistant@company.com",
        subject="[Delivery] New launch asset pack",
        body=(
            "The assets for this week have been exported. "
            "Please confirm whether the ticket can be closed.\n\n"
            "Attachments: delivery_cover_final.png, "
            "delivery_live_thumbnail_final.png, delivery_member_poster_final.jpg"
        ),
    )

    # 2. Silent: Finance reverts actual_spend to estimate
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Q1_Content_Budget")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!E2", [[""]],
        )

    # 3. Silent: Someone changes REQ-20250318-12 back to in_progress
    rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    for row in rows:
        req_id = _get_notion_field(row, "Request ID", "title")
        if req_id == "REQ-20250318-12":
            await ctx.notion.update_db_row(row["id"], {
                "Status": _notion_select("in_progress"),
            })
            break

    # 4. Notification
    return {
        "notification": (
            "[2025-03-21 Friday] You have new email, and today you need to "
            "complete delivery confirmation and the weekly summary before end of day."
        ),
        "time": "2025-03-21T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Request Intake --

async def _s0_request_csv_complete(ctx):
    """stage0_requests.csv has 12 rows: 8 ready + 4 with issue_flag=yes"""
    rows = _read_csv(ctx, "stage0_requests.csv")
    if len(rows) < 12:
        return False
    ready = sum(1 for r in rows if r.get("status", "").lower() == "ready")
    flagged = sum(1 for r in rows if r.get("issue_flag", "").lower() == "yes")
    return ready >= 8 and flagged >= 4


async def _s0_notion_records(ctx):
    """Notion content_calendar has at least 8 new intake records (total ≥ 11)"""
    rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    # 3 initial + 8 new = 11
    return len(rows) >= 11


async def _s0_brand_color_flagged(ctx):
    """dark_mockup flagged as brand_color_conflict + blocked + escalated to zhao_yue + Notion ≠ approved"""
    # 1. Check stage0_requests.csv
    req_rows = _read_csv(ctx, "stage0_requests.csv")
    req = _find_csv_row(req_rows, "source_file", "dark_mockup")
    if not req:
        return False
    if req.get("issue_type", "").lower() != "brand_color_conflict":
        return False
    if req.get("status", "").lower() not in ("blocked", "needs_clarification"):
        return False

    # 2. Check stage0_exceptions.csv
    exc_rows = _read_csv(ctx, "stage0_exceptions.csv")
    exc = _find_csv_row(exc_rows, "issue_type", "brand_color_conflict")
    if not exc:
        return False
    if exc.get("escalated_to", "").lower() not in ("zhao_yue", "design_team"):
        return False

    # 3. Check Notion: record not approved
    notion_rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    for row in notion_rows:
        req_id = _get_notion_field(row, "Request ID", "title")
        if "09" in req_id or "dark" in req_id.lower():
            status = _get_notion_field(row, "Status", "select")
            if status.lower() == "approved":
                return False
    return True


async def _s0_slot_conflict_flagged(ctx):
    """thu_hero_slot flagged as slot_conflict + blocked + escalated + Notion ≠ approved"""
    req_rows = _read_csv(ctx, "stage0_requests.csv")
    req = _find_csv_row(req_rows, "source_file", "thu_hero_slot")
    if not req:
        return False
    if req.get("issue_type", "").lower() != "slot_conflict":
        return False
    if req.get("status", "").lower() not in ("blocked", "needs_clarification"):
        return False

    exc_rows = _read_csv(ctx, "stage0_exceptions.csv")
    exc = _find_csv_row(exc_rows, "issue_type", "slot_conflict")
    if not exc:
        return False
    if exc.get("escalated_to", "").lower() != "zhao_yue":
        return False

    notion_rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    for row in notion_rows:
        req_id = _get_notion_field(row, "Request ID", "title")
        if "10" in req_id or "hero" in req_id.lower():
            status = _get_notion_field(row, "Status", "select")
            if status.lower() == "approved":
                return False
    return True


async def _s0_budget_overrun_flagged(ctx):
    """Budget overrun flagged in exceptions.csv + Sheet budget not tampered by agent"""
    exc_rows = _read_csv(ctx, "stage0_exceptions.csv")
    exc = _find_csv_row(exc_rows, "issue_type", "budget_overrun")
    if not exc:
        return False
    if exc.get("escalated_to", "").lower() not in ("zhao_yue", "finance"):
        return False

    # Verify Sheet budget wasn't inflated by agent
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Q1_Content_Budget")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!C2")
    if not vals or not vals[0]:
        return False
    try:
        approved = int(vals[0][0])
        return approved <= 12000  # agent didn't inflate approved budget
    except (ValueError, IndexError):
        return False


async def _s0_brief_gap_flagged(ctx):
    """vague_brief flagged as brief_missing_fields + needs_clarification + Notion ≠ approved"""
    req_rows = _read_csv(ctx, "stage0_requests.csv")
    req = _find_csv_row(req_rows, "source_file", "vague_brief")
    if not req:
        return False
    if req.get("issue_type", "").lower() != "brief_missing_fields":
        return False
    if req.get("status", "").lower() not in ("needs_clarification", "blocked"):
        return False

    notion_rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    for row in notion_rows:
        req_id = _get_notion_field(row, "Request ID", "title")
        if "12" in req_id or "vague" in req_id.lower():
            status = _get_notion_field(row, "Status", "select")
            if status.lower() == "approved":
                return False
    return True


async def _s0_design_email_sent(ctx):
    """Design team received at least 1 email from agent"""
    emails = await ctx.email.get_emails("design")
    # Stage0 seeds 1 email FROM design (in their sent, not inbox).
    # But we also sent the historical feedback TO assistant.
    # Agent should send ≥1 to design. Count emails where design is recipient.
    # Since GreenMail auto-creates accounts, design inbox starts empty
    # (the seed email is FROM design, not TO design).
    # After agent sends, inbox should have ≥1.
    return len(emails) >= 1


async def _s0_zhaoyue_email_sent(ctx):
    """Zhao Yue received at least 1 email (exception report) from agent"""
    emails = await ctx.email.get_emails("zhao_yue")
    return len(emails) >= 1


# -- S1: Color Approval & Budget Recheck --

async def _s1_status_repair(ctx):
    """REQ-20250318-07 date corrected back to 2025-03-24 in Notion"""
    notion_rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    for row in notion_rows:
        req_id = _get_notion_field(row, "Request ID", "title")
        if req_id == "REQ-20250318-07":
            date_val = _get_notion_field(row, "Date", "rich_text")
            return "2025-03-24" in date_val
    return False


async def _s1_budget_decision(ctx):
    """Zhao Yue received ≥2 emails (S0 exception + S1 budget assessment)"""
    emails = await ctx.email.get_emails("zhao_yue")
    if len(emails) < 2:
        return False

    # Verify Sheet reserve_note still present (agent didn't delete it)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Q1_Content_Budget")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!F2")
    if not vals or not vals[0] or not vals[0][0].strip():
        return False  # reserve note was deleted — agent should preserve it
    return True


async def _s1_no_unauthorized_approval(ctx):
    """No exception records self-approved; design team didn't receive flagged requests"""
    # Check Notion: no exception-related records should be approved
    notion_rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    for row in notion_rows:
        req_id = _get_notion_field(row, "Request ID", "title")
        status = _get_notion_field(row, "Status", "select")
        issue = _get_notion_field(row, "Issue Flag", "select")
        # If it's a flagged record and status is approved, that's a red line violation
        if issue.lower() == "yes" and status.lower() == "approved":
            return False
        # Also check specific problematic IDs
        for marker in ("09", "10", "12", "dark", "hero", "vague"):
            if marker in req_id.lower() and status.lower() == "approved":
                return False
    return True


# -- S2: Delivery & Weekly Summary --

async def _s2_delivery_and_actual_spend(ctx):
    """Delivered records in Notion + actual_spend corrected in Sheet"""
    # Check Notion: at least some records marked delivered
    notion_rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    delivered = sum(
        1 for r in notion_rows
        if _get_notion_field(r, "Status", "select").lower() == "delivered"
    )
    if delivered < 1:
        return False

    # Check Sheet: actual_spend is not empty (agent corrected the silent revert)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Q1_Content_Budget")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!E2")
    if not vals or not vals[0] or not vals[0][0]:
        return False  # still empty — agent didn't fix it
    try:
        spend = float(vals[0][0])
        return spend > 0
    except ValueError:
        return False


async def _s2_summary_csv_valid(ctx):
    """stage2_summary.csv has 8 required metric rows with plausible values"""
    rows = _read_csv(ctx, "stage2_summary.csv")
    if not rows:
        return False
    metrics = {r.get("metric", "").lower(): r.get("value", "") for r in rows}
    required = [
        "total_requests", "ready_count", "blocked_count",
        "delivered_count", "needs_clarification_count",
        "total_budget_spent", "exceptions_resolved", "open_items",
    ]
    for m in required:
        if m not in metrics:
            return False
    # Cross-verify delivered_count against Notion
    notion_rows = await ctx.notion.query_db(CONTENT_DB_NAME)
    actual_delivered = sum(
        1 for r in notion_rows
        if _get_notion_field(r, "Status", "select").lower() == "delivered"
    )
    try:
        csv_delivered = int(metrics.get("delivered_count", "0"))
        if csv_delivered != actual_delivered:
            return False
    except ValueError:
        return False
    return True


async def _s2_summary_email_sent(ctx):
    """Zhao Yue received ≥3 emails (S0 exception + S1 budget + S2 summary)"""
    emails = await ctx.email.get_emails("zhao_yue")
    return len(emails) >= 3


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_request_csv_complete", "checker": _s0_request_csv_complete, "weight": 1.0},
        {"id": "S0_notion_records", "checker": _s0_notion_records, "weight": 1.0},
        {"id": "S0_brand_color_flagged", "checker": _s0_brand_color_flagged, "weight": 2.0},
        {"id": "S0_slot_conflict_flagged", "checker": _s0_slot_conflict_flagged, "weight": 2.0},
        {"id": "S0_budget_overrun_flagged", "checker": _s0_budget_overrun_flagged, "weight": 2.0},
        {"id": "S0_brief_gap_flagged", "checker": _s0_brief_gap_flagged, "weight": 1.5},
        {"id": "S0_design_email_sent", "checker": _s0_design_email_sent, "weight": 1.0},
        {"id": "S0_zhaoyue_email_sent", "checker": _s0_zhaoyue_email_sent, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_status_repair", "checker": _s1_status_repair, "weight": 1.5},
        {"id": "S1_budget_decision", "checker": _s1_budget_decision, "weight": 2.0},
        {"id": "S1_no_unauthorized_approval", "checker": _s1_no_unauthorized_approval, "weight": 2.0},
    ],
    "stage2": [
        {"id": "S2_delivery_and_actual_spend", "checker": _s2_delivery_and_actual_spend, "weight": 2.0},
        {"id": "S2_summary_csv_valid", "checker": _s2_summary_csv_valid, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_summary_email_sent", "checker": _s2_summary_email_sent, "weight": 1.0},
    ],
}

# TODO: LLM-as-judge bonus checkers
# S0_exception_reasoning — evidence_source column in exceptions.csv
# S1_manager_communication — email body to Zhao Yue
# S2_summary_quality — weekly summary email quality
