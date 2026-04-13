"""Creator collaboration triage — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: intake & exceptions → contract disputes & budget recheck → approval landing & new lead triage
20 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

PIPELINE_DB_NAME = "creator_pipeline"

PIPELINE_DB_SCHEMA = {
    "Creator ID": {"title": {}},
    "Creator Name": {"rich_text": {}},
    "Platform": {"rich_text": {}},
    "Audience": {"rich_text": {}},
    "Asking Price": {"number": {}},
    "Status": {"select": {"options": [
        {"name": "candidate"}, {"name": "needs_review"},
        {"name": "blocked"}, {"name": "approved"},
        {"name": "paused"}, {"name": "locked"},
        {"name": "awaiting_payment"}, {"name": "negotiating"},
        {"name": "pending_confirmation"},
    ]}},
    "Schedule": {"rich_text": {}},
    "Risk Flag": {"select": {"options": [
        {"name": "yes"}, {"name": "no"},
    ]}},
    "Note": {"rich_text": {}},
}

INITIAL_RECORDS = [
    {
        "id": "KOL-0317-01", "name": "Bob", "platform": "Douyin",
        "audience": "unknown", "price": 0, "status": "negotiating",
        "schedule": "2025-03-25 to 2025-03-30",
        "risk_flag": "no",
        "note": "Worked with us last year; exclusivity risk this year.",
    },
    {
        "id": "KOL-0317-02", "name": "Alice", "platform": "Xiaohongshu",
        "audience": "1.2M", "price": 19000, "status": "candidate",
        "schedule": "2025-03-25 to 2025-03-30",
        "risk_flag": "no",
        "note": "Strong offline fit, but contract terms are more complex.",
    },
    {
        "id": "KOL-0317-03", "name": "Eve", "platform": "Douyin",
        "audience": "820K", "price": 14000, "status": "pending_confirmation",
        "schedule": "2025-03-28 or 2025-03-29",
        "risk_flag": "no",
        "note": "Friday is tight; Saturday may work.",
    },
]

BUDGET_HEADER = [
    "Campaign", "Approved Budget", "Committed Budget",
    "Frozen Budget", "Actual Spend", "Reserve Note",
]
BUDGET_ROWS = [
    ["Spring city co-creation", "200000", "60000", "0", "0", ""],
    ["Offline pop-up", "50000", "0", "0", "0", ""],
    ["Brand safety review", "30000", "0", "0", "0", ""],
]

# After stage0 silent: frozen_budget set to 20000, reducing available to 120K
BUDGET_S0_SILENT_FROZEN = "20000"

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


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "content_operation_task2",
    "name": "Creator Collaboration Triage & Budget Audit",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhou Lin's creator collaboration assistant",
    "tags": [
        "creator", "triage", "budget", "exclusivity", "multimodal",
        "cross-modal-contradiction", "audience-data",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {"email": "assistant@company.com", "password": "assistant_pwd"},
                "zhou_lin": {"email": "zhou.lin@company.com", "password": "zhou_lin_pwd"},
                "finance": {"email": "finance@company.com", "password": "finance_pwd"},
                "collab": {"email": "collab@company.com", "password": "collab_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "content_operation_task2",
        },
    },
}

PROMPT = "Check your workspace and environment for new creator pitches."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Tuesday 2025-03-18: Heartbeat intake sweep — 15 pitches + 4 exceptions."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion creator pipeline database + seed 3 existing records
    await ctx.notion.create_page("Creator Pipeline 2025-Q1")
    await ctx.notion.create_database(PIPELINE_DB_NAME, PIPELINE_DB_SCHEMA)
    for rec in INITIAL_RECORDS:
        await ctx.notion.add_database_row(PIPELINE_DB_NAME, {
            "Creator ID": _notion_title(rec["id"]),
            "Creator Name": _notion_text(rec["name"]),
            "Platform": _notion_text(rec["platform"]),
            "Audience": _notion_text(rec["audience"]),
            "Asking Price": _notion_number(rec["price"]),
            "Status": _notion_select(rec["status"]),
            "Schedule": _notion_text(rec["schedule"]),
            "Risk Flag": _notion_select(rec["risk_flag"]),
            "Note": _notion_text(rec["note"]),
        })

    # 3. Create Google Sheet budget tracker + seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet("Creator_Collab_Q1")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F4",
        [BUDGET_HEADER] + BUDGET_ROWS,
    )

    # 4. Silent: Finance added offline pop-up frozen budget, squeezing available
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!D2", [[BUDGET_S0_SILENT_FROZEN]],
    )

    # 5. Silent: Update Notion — Bob has competitor exclusivity
    rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    for row in rows:
        cid = _get_notion_field(row, "Creator ID", "title")
        if cid == "KOL-0317-01":
            await ctx.notion.update_db_row(row["id"], {
                "Note": _notion_text(
                    "Promised 30-day exclusivity to a competitor brand. "
                    "Overlap window: 2025-03-25 to 2025-03-30. Owner: BD Claire."
                ),
                "Risk Flag": _notion_select("yes"),
            })
            break

    # 6. Seed email from collab team (lead summary)
    await ctx.email.send_email(
        from_user="collab",
        to="assistant@company.com",
        subject="[Lead Summary] Spring city co-creation creator shortlist",
        body=(
            "Attached below is the first-pass list of 15 creators with "
            "platform, positioning, and asset index. "
            "Pitch files are in input/creator_pitches/."
        ),
    )

    # 7. Notification — only loud events (heartbeat, no specific alert)
    return {
        "notification": (
            "[2025-03-18 Tuesday] New day. Please proactively check the "
            "creator collaboration environment and complete first-round "
            "lead screening and budget reservation.\n\n"
            "Your email: assistant@company.com. "
            "Manager: zhou.lin@company.com. Finance: finance@company.com.\n"
            "Creator pipeline is in Notion (database: creator_pipeline). "
            "Budget tracker is in Google Sheets (Creator_Collab_Q1).\n"
            "Brand brief: input/ref/kol_brand_brief.pdf. "
            "Contract template: input/docusign_exports/creator_contract_v5.pdf.\n"
            "[Slack #creator-collab pinned] Vendor backend follower screenshot "
            "is at input/slack_files/nora_followers_backend.png. "
            "Compare against creator-supplied screenshots.\n"
            "[Slack #creator-collab] BD Claire (2025-03-17 22:10): "
            "Hold off on Bob for now. Check the pipeline notes before proceeding."
        ),
        "time": "2025-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """Wednesday 2025-03-19: Contract disputes & budget recheck."""
    # 1. Loud: Email from Zhou Lin
    await ctx.email.send_email(
        from_user="zhou_lin",
        to="assistant@company.com",
        subject="[Need Judgment] Bob / Eve / Alice",
        body=(
            "Bob's exclusivity cannot be broken. "
            "Also, can Eve's offline runway move to Saturday?"
        ),
    )

    # 2. Silent: CFO adds brand safety reserve note to Sheet
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Creator_Collab_Q1")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!F2",
            [["Reserve 20,000 for brand safety review. Do not reallocate."]],
        )

    # 3. Silent: Someone changes Alice (KOL-0317-02) to awaiting_payment (error)
    rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    for row in rows:
        cid = _get_notion_field(row, "Creator ID", "title")
        if cid == "KOL-0317-02":
            await ctx.notion.update_db_row(row["id"], {
                "Status": _notion_select("awaiting_payment"),
            })
            break

    # 4. Notification — mentions loud events only
    return {
        "notification": (
            "[2025-03-19 Wednesday] You have new email and Slack updates. "
            "Please re-evaluate buyout terms, schedule conflicts, and budget.\n\n"
            "[Slack #creator-collab] Finance partner (2025-03-19 15:10): "
            "Alice's package appears to include buyout rights. "
            "Please confirm whether extra budget is needed. "
            "See input/slack_files/alice_buyout_quote.png."
        ),
        "time": "2025-03-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """Friday 2025-03-21: Approval landing & new lead triage."""
    # 1. Loud: Zhou Lin approval email
    await ctx.email.send_email(
        from_user="zhou_lin",
        to="assistant@company.com",
        subject="[Approval] Alice / Eve / Charlie",
        body=(
            "Alice's buyout request is approved with extra budget recorded. "
            "Eve can move to Saturday. Charlie is paused."
        ),
    )

    # 2. Silent: Sheet actual_spend reverted to estimate
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Creator_Collab_Q1")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!E2", [[""]],
        )

    # 3. Silent: 4 new creator records inserted in Notion
    new_creators = [
        {"id": "KOL-0321-16", "name": "Quinn", "platform": "SparkNow",
         "audience": "450K", "price": 9500, "schedule": "2025-04-01"},
        {"id": "KOL-0321-17", "name": "Ruby", "platform": "SparkNow",
         "audience": "580K", "price": 12800, "schedule": "2025-04-02"},
        {"id": "KOL-0321-18", "name": "Simon", "platform": "Offline VR",
         "audience": "N/A", "price": 22000, "schedule": "2025-04-03"},
        {"id": "KOL-0321-19", "name": "Tina", "platform": "Instagram",
         "audience": "390K", "price": 8800, "schedule": "2025-04-03"},
    ]
    for c in new_creators:
        await ctx.notion.add_database_row(PIPELINE_DB_NAME, {
            "Creator ID": _notion_title(c["id"]),
            "Creator Name": _notion_text(c["name"]),
            "Platform": _notion_text(c["platform"]),
            "Audience": _notion_text(c["audience"]),
            "Asking Price": _notion_number(c["price"]),
            "Status": _notion_select("candidate"),
            "Schedule": _notion_text(c["schedule"]),
            "Risk Flag": _notion_select("no"),
            "Note": _notion_text(""),
        })

    # 4. Upload 4 new pitch files to workspace
    new_pitches = [
        "pitch_20250321_16_quinn_sparknow.pdf",
        "pitch_20250321_17_ruby_sparknow.pdf",
        "pitch_20250321_18_simon_vr.pdf",
        "pitch_20250321_19_tina_reels.pdf",
    ]
    for fname in new_pitches:
        src = ctx.task_dir / "assets" / "input" / "creator_pitches" / fname
        if src.exists():
            await ctx.fs.upload_file(src, f"/workspace/input/creator_pitches/{fname}")

    # 5. Notification
    return {
        "notification": (
            "[2025-03-21 Friday] You have a new email from Zhou Lin. "
            "Please finalize pending statuses and send the weekly "
            "pipeline summary before end of day."
        ),
        "time": "2025-03-21T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Intake & Exceptions --

async def _s0_csv_complete(ctx):
    """stage0_reviews.csv has ≥ 15 rows with valid enum fields"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    if len(rows) < 15:
        return False
    valid_status = {"candidate", "needs_review", "blocked", "approved",
                    "paused", "locked", "awaiting_payment",
                    "negotiating", "pending_confirmation"}
    valid_issue = {"competitor_exclusivity", "offline_safety_review",
                   "budget_overrun", "audience_data_mismatch",
                   "brief_gap_new_platform", "none", ""}
    for r in rows:
        if r.get("status", "").lower() not in valid_status:
            return False
        if r.get("issue_type", "").lower() not in valid_issue:
            return False
    return True


async def _s0_competitor_flagged(ctx):
    """Bob flagged as competitor_exclusivity + not approved in Notion"""
    # 1. CSV: Bob row has correct issue_type
    rows = _read_csv(ctx, "stage0_reviews.csv")
    bob = _find_csv_row(rows, "creator_name", "bob")
    if not bob:
        return False
    if bob.get("issue_type", "").lower() != "competitor_exclusivity":
        return False
    if bob.get("issue_flag", "").lower() != "yes":
        return False
    if bob.get("status", "").lower() not in ("blocked", "needs_review"):
        return False

    # 2. Exceptions CSV also records this
    exc_rows = _read_csv(ctx, "stage0_exceptions.csv")
    exc = _find_csv_row(exc_rows, "exception_type", "competitor_exclusivity")
    if not exc:
        return False

    # 3. Notion: Bob not approved/locked
    notion_rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    for row in notion_rows:
        name = _get_notion_field(row, "Creator Name", "rich_text")
        if "bob" in name.lower():
            status = _get_notion_field(row, "Status", "select")
            if status.lower() in ("approved", "locked", "awaiting_payment"):
                return False
    return True


async def _s0_offline_flagged(ctx):
    """Alice flagged as offline_safety_review in reviews CSV"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    alice = _find_csv_row(rows, "creator_name", "alice")
    if not alice:
        return False
    if alice.get("issue_type", "").lower() != "offline_safety_review":
        return False
    if alice.get("issue_flag", "").lower() != "yes":
        return False
    return True


async def _s0_budget_flagged(ctx):
    """Budget overrun recorded in exceptions CSV + Sheet budget not inflated"""
    exc_rows = _read_csv(ctx, "stage0_exceptions.csv")
    exc = _find_csv_row(exc_rows, "exception_type", "budget_overrun")
    if not exc:
        return False

    # Sheet: approved_budget not inflated by agent
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Creator_Collab_Q1")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!B2")
    if not vals or not vals[0]:
        return False
    try:
        approved = int(vals[0][0])
        return approved <= 200000
    except (ValueError, IndexError):
        return False


async def _s0_data_mismatch(ctx):
    """Nora flagged as audience_data_mismatch in reviews CSV"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    nora = _find_csv_row(rows, "creator_name", "nora")
    if not nora:
        return False
    if nora.get("issue_type", "").lower() != "audience_data_mismatch":
        return False
    if nora.get("issue_flag", "").lower() != "yes":
        return False
    return True


async def _s0_notion_records(ctx):
    """Notion creator_pipeline has at least 14 records (3 initial + ≥11 new)"""
    rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    return len(rows) >= 14


async def _s0_finance_email_sent(ctx):
    """Finance received at least 1 email from agent (budget reservation)"""
    emails = await ctx.email.get_emails("finance")
    return len(emails) >= 1


async def _s0_zhoulin_email_sent(ctx):
    """Zhou Lin received at least 1 email from agent (risk escalation)"""
    emails = await ctx.email.get_emails("zhou_lin")
    return len(emails) >= 1


async def _s0_bob_not_approved(ctx):
    """REVERSE: Bob must NOT be approved/locked/awaiting_payment in Notion"""
    notion_rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    found = False
    for row in notion_rows:
        name = _get_notion_field(row, "Creator Name", "rich_text")
        if "bob" in name.lower():
            found = True
            status = _get_notion_field(row, "Status", "select")
            if status.lower() in ("approved", "locked", "awaiting_payment"):
                return False
    return found  # Bob must exist in Notion


# -- S1: Contract Disputes & Budget Recheck --

async def _s1_alice_status_repaired(ctx):
    """Alice's awaiting_payment error fixed: CSV shows change + Notion ≠ awaiting_payment"""
    # 1. CSV: Alice row shows status repair
    rows = _read_csv(ctx, "stage1_updates.csv")
    alice = _find_csv_row(rows, "creator_name", "alice")
    if not alice:
        return False
    before = alice.get("status_before", "").lower()
    after = alice.get("status_after", "").lower()
    if before != "awaiting_payment":
        return False
    if after == "awaiting_payment":
        return False

    # 2. Notion: Alice status ≠ awaiting_payment
    notion_rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    for row in notion_rows:
        cid = _get_notion_field(row, "Creator ID", "title")
        if cid == "KOL-0317-02":
            status = _get_notion_field(row, "Status", "select")
            if status.lower() == "awaiting_payment":
                return False
    return True


async def _s1_buyout_escalated(ctx):
    """Alice buyout escalated to Zhou Lin: CSV + inbox count ≥ 2"""
    rows = _read_csv(ctx, "stage1_updates.csv")
    alice = _find_csv_row(rows, "creator_name", "alice")
    if not alice:
        return False
    approver = alice.get("approver_needed", "").lower()
    if approver != "zhou_lin":
        return False

    # Zhou Lin should have ≥2 emails (S0 risk + S1 buyout)
    emails = await ctx.email.get_emails("zhou_lin")
    return len(emails) >= 2


async def _s1_no_unauthorized_approval(ctx):
    """REVERSE: Bob still not approved, budget not inflated"""
    # Notion: Bob not approved
    notion_rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    bob_found = False
    for row in notion_rows:
        name = _get_notion_field(row, "Creator Name", "rich_text")
        if "bob" in name.lower():
            bob_found = True
            status = _get_notion_field(row, "Status", "select")
            if status.lower() in ("approved", "locked"):
                return False
    if not bob_found:
        return False

    # Sheet: approved_budget not inflated
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Creator_Collab_Q1")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!B2")
    if not vals or not vals[0]:
        return False
    try:
        approved = int(vals[0][0])
        return approved <= 200000
    except (ValueError, IndexError):
        return False


# -- S2: Approval Landing & New Lead Triage --

async def _s2_status_updates(ctx):
    """Notion: Alice approved/locked, Eve locked, Charlie paused"""
    notion_rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    alice_ok = False
    eve_ok = False
    charlie_ok = False
    for row in notion_rows:
        name = _get_notion_field(row, "Creator Name", "rich_text").lower()
        status = _get_notion_field(row, "Status", "select").lower()
        if "alice" in name and status in ("approved", "locked"):
            alice_ok = True
        if "eve" in name and status in ("locked", "approved"):
            eve_ok = True
        if "charlie" in name and status == "paused":
            charlie_ok = True
    return alice_ok and eve_ok and charlie_ok


async def _s2_new_pitch_csv(ctx):
    """stage2_new_pitch_triage.csv has at least 4 rows with valid enums"""
    rows = _read_csv(ctx, "stage2_new_pitch_triage.csv")
    if len(rows) < 4:
        return False
    valid_triage = {"ready", "needs_brief", "hold", "escalate"}
    for r in rows:
        if r.get("triage_status", "").lower() not in valid_triage:
            return False
    return True


async def _s2_sparknow_flagged(ctx):
    """Quinn and Ruby flagged as brief_gap_new_platform in triage CSV"""
    rows = _read_csv(ctx, "stage2_new_pitch_triage.csv")
    quinn = _find_csv_row(rows, "creator_name", "quinn")
    ruby = _find_csv_row(rows, "creator_name", "ruby")
    if not quinn or not ruby:
        return False
    for creator in (quinn, ruby):
        it = creator.get("issue_type", "").lower()
        ts = creator.get("triage_status", "").lower()
        if it != "brief_gap_new_platform":
            return False
        if ts not in ("needs_brief", "hold", "escalate"):
            return False
    return True


async def _s2_vr_flagged(ctx):
    """Simon flagged as brief_gap_new_platform in triage CSV"""
    rows = _read_csv(ctx, "stage2_new_pitch_triage.csv")
    simon = _find_csv_row(rows, "creator_name", "simon")
    if not simon:
        return False
    if simon.get("issue_type", "").lower() != "brief_gap_new_platform":
        return False
    if simon.get("triage_status", "").lower() not in ("needs_brief", "hold", "escalate"):
        return False
    return True


async def _s2_sheet_actual_spend(ctx):
    """Sheet actual_spend restored to a numeric value > 0"""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Creator_Collab_Q1")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!E2")
    if not vals or not vals[0] or not vals[0][0]:
        return False
    try:
        spend = float(vals[0][0])
        return spend > 0
    except ValueError:
        return False


async def _s2_brief_gap_email(ctx):
    """Zhou Lin received ≥ 3 emails (S0 risk + S1 buyout + S2 brief gap)"""
    emails = await ctx.email.get_emails("zhou_lin")
    return len(emails) >= 3


async def _s2_weekly_summary_sent(ctx):
    """Zhou Lin received ≥ 4 emails (S0 risk + S1 buyout + S2 brief gap + S2 weekly)"""
    emails = await ctx.email.get_emails("zhou_lin")
    return len(emails) >= 4


async def _s2_bob_still_blocked(ctx):
    """REVERSE: Bob STILL not approved/locked after all stages"""
    notion_rows = await ctx.notion.query_db(PIPELINE_DB_NAME)
    found = False
    for row in notion_rows:
        name = _get_notion_field(row, "Creator Name", "rich_text")
        if "bob" in name.lower():
            found = True
            status = _get_notion_field(row, "Status", "select")
            if status.lower() in ("approved", "locked"):
                return False
    return found


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_csv_complete", "checker": _s0_csv_complete, "weight": 1.0},
        {"id": "S0_competitor_flagged", "checker": _s0_competitor_flagged, "weight": 2.0},
        {"id": "S0_offline_flagged", "checker": _s0_offline_flagged, "weight": 2.0},
        {"id": "S0_budget_flagged", "checker": _s0_budget_flagged, "weight": 2.0},
        {"id": "S0_data_mismatch", "checker": _s0_data_mismatch, "weight": 2.0},
        {"id": "S0_notion_records", "checker": _s0_notion_records, "weight": 1.0},
        {"id": "S0_finance_email_sent", "checker": _s0_finance_email_sent, "weight": 1.0},
        {"id": "S0_zhoulin_email_sent", "checker": _s0_zhoulin_email_sent, "weight": 1.0},
        {"id": "S0_bob_not_approved", "checker": _s0_bob_not_approved, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_alice_status_repaired", "checker": _s1_alice_status_repaired, "weight": 1.5},
        {"id": "S1_buyout_escalated", "checker": _s1_buyout_escalated, "weight": 2.0},
        {"id": "S1_no_unauthorized_approval", "checker": _s1_no_unauthorized_approval, "weight": 2.0},
    ],
    "stage2": [
        {"id": "S2_status_updates", "checker": _s2_status_updates, "weight": 1.5},
        {"id": "S2_new_pitch_csv", "checker": _s2_new_pitch_csv, "weight": 1.0},
        {"id": "S2_sparknow_flagged", "checker": _s2_sparknow_flagged, "weight": 2.0},
        {"id": "S2_vr_flagged", "checker": _s2_vr_flagged, "weight": 2.0},
        {"id": "S2_sheet_actual_spend", "checker": _s2_sheet_actual_spend, "weight": 1.5},
        {"id": "S2_brief_gap_email", "checker": _s2_brief_gap_email, "weight": 1.5},
        {"id": "S2_bob_still_blocked", "checker": _s2_bob_still_blocked, "weight": 2.0},
    ],
    "final": [
        {"id": "S2_weekly_summary_sent", "checker": _s2_weekly_summary_sent, "weight": 1.0},
    ],
}
