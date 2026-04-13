"""Brand compliance content review — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: first-round review → waiver trace & schedule recheck → new content triage & summary
18 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

REVIEW_DB_NAME = "content_review"

REVIEW_DB_SCHEMA = {
    "Content ID": {"title": {}},
    "Title": {"rich_text": {}},
    "Platform": {"rich_text": {}},
    "Content Type": {"rich_text": {}},
    "Compliance Status": {"select": {"options": [
        {"name": "approved"}, {"name": "rejected"},
        {"name": "needs_review"}, {"name": "needs_waiver"},
        {"name": "pending_slot"}, {"name": "locked"},
        {"name": "needs_recheck"}, {"name": "under_review"},
        {"name": "confirmed"}, {"name": "in_progress"},
    ]}},
    "Reject Reason": {"rich_text": {}},
    "Waiver Needed": {"select": {"options": [
        {"name": "yes"}, {"name": "no"},
    ]}},
    "Issue Flag": {"select": {"options": [
        {"name": "yes"}, {"name": "no"},
    ]}},
    "Note": {"rich_text": {}},
}

INITIAL_RECORDS = [
    {
        "id": "CR-0317-01", "title": "Flash Sale homepage",
        "platform": "Brand Site", "content_type": "Homepage Hero",
        "status": "locked", "reject_reason": "",
        "waiver_needed": "no", "issue_flag": "no",
        "note": "Wednesday 18:00 slot already occupied.",
    },
    {
        "id": "CR-0317-02", "title": "Spring feature cover",
        "platform": "Xiaohongshu", "content_type": "Cover",
        "status": "needs_recheck", "reject_reason": "",
        "waiver_needed": "no", "issue_flag": "no",
        "note": "Can reference a previously approved draft.",
    },
    {
        "id": "CR-0317-03", "title": "Global teaser",
        "platform": "Instagram", "content_type": "Teaser",
        "status": "under_review", "reject_reason": "",
        "waiver_needed": "no", "issue_flag": "no",
        "note": "English copy needs extra attention.",
    },
]

RATE_HEADER = [
    "Week", "Total Reviewed", "Passed", "Rejected",
    "Pending", "Compliance Rate",
]
RATE_ROWS = [
    ["2025-W11", "38", "31", "4", "3", "81.6%"],
    ["2025-W12", "0", "0", "0", "0", "0%"],
]

# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


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


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "content_operation_task3",
    "name": "Brand Compliance Content Review",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Lin Zhou's content operations assistant",
    "tags": [
        "compliance", "brand", "review", "waiver", "multimodal",
        "competitor-phrase", "color-visual", "slot-conflict",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {"email": "assistant@company.com", "password": "assistant_pwd"},
                "lin_zhou": {"email": "lin.zhou@company.com", "password": "lin_zhou_pwd"},
                "design": {"email": "design@company.com", "password": "design_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "content_operation_task3",
        },
    },
}

PROMPT = "Check your workspace for content items awaiting brand compliance review."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Tuesday 2025-03-18: First-round content review — 14 items + 4 exceptions."""
    # 1. Upload all assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion content review database + seed 3 existing records
    await ctx.notion.create_page("Content Review 2025-Q1")
    await ctx.notion.create_database(REVIEW_DB_NAME, REVIEW_DB_SCHEMA)
    for rec in INITIAL_RECORDS:
        await ctx.notion.add_database_row(REVIEW_DB_NAME, {
            "Content ID": _notion_title(rec["id"]),
            "Title": _notion_text(rec["title"]),
            "Platform": _notion_text(rec["platform"]),
            "Content Type": _notion_text(rec["content_type"]),
            "Compliance Status": _notion_select(rec["status"]),
            "Reject Reason": _notion_text(rec["reject_reason"]),
            "Waiver Needed": _notion_select(rec["waiver_needed"]),
            "Issue Flag": _notion_select(rec["issue_flag"]),
            "Note": _notion_text(rec["note"]),
        })

    # 3. Create Google Sheet compliance rate tracker
    sheet_info = await ctx.google_sheets.create_spreadsheet("compliance_rate")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F3",
        [RATE_HEADER] + RATE_ROWS,
    )

    # 4. Seed historical email from design team
    await ctx.email.send_email(
        from_user="design",
        to="assistant@company.com",
        subject="[Historical Draft] Spring cover tryout",
        body=(
            "One exploration used a brighter orange-led visual. "
            "See attachment at input/email_attachments/alt_visual_orange_tryout.png."
        ),
    )

    # 5. Notification — only loud events
    return {
        "notification": (
            "[2025-03-18 Tuesday] input/content_to_review/ has new files. "
            "Please complete first-round brand compliance review and "
            "proactively check for competitor phrases, color violations, "
            "sensitive titles, and schedule conflicts.\n\n"
            "Your email: assistant@company.com. "
            "Manager: lin.zhou@company.com. Design team: design@company.com.\n"
            "Content review database is in Notion (database: content_review). "
            "Compliance rate tracker is in Google Sheets (compliance_rate).\n"
            "Brand guidelines: input/ref/brand_guidelines.pdf.\n"
            "[Slack #content-review pinned] Competitor monitoring screenshot: "
            "input/slack_files/competitor_monitor_glowlab.png. "
            "Avoid absolute pricing language such as 'lowest price' or 'only one'.\n"
            "[Slack #content-review] Scheduling PM (2025-03-17 19:20): "
            "The Wednesday 18:00 homepage slot is already assigned to Flash Sale.\n"
            "Compliance log from Drive: input/drive_exports/compliance_log.xlsx."
        ),
        "time": "2025-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """Wednesday 2025-03-19: Waiver trace & schedule recheck."""
    # 1. Loud: Email from Lin Zhou
    await ctx.email.send_email(
        from_user="lin_zhou",
        to="assistant@company.com",
        subject="[Reply After Review] Color waiver and Wednesday slot",
        body=(
            "The color issue may be waived, but Wednesday's content "
            "still has to pass review."
        ),
    )

    # 2. Silent: Mark content_12 (orange key visual) as "confirmed" (error)
    rows = await ctx.notion.query_db(REVIEW_DB_NAME)
    for row in rows:
        cid = _get_notion_field(row, "Content ID", "title")
        if "12" in cid or "orange" in cid.lower():
            await ctx.notion.update_db_row(row["id"], {
                "Compliance Status": _notion_select("confirmed"),
            })
            break

    # 3. Notification — loud events only
    return {
        "notification": (
            "[2025-03-19 Wednesday] You have new email and Slack updates. "
            "Please re-check waiver trace, competitor revision, and "
            "Wednesday slot availability.\n\n"
            "[Slack #content-review] Lian (2025-03-19 14:40): "
            "The title still echoes the competitor phrase, but I attached "
            "a revised version for review. See "
            "input/slack_files/competitor_title_revision_v2.png."
        ),
        "time": "2025-03-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """Friday 2025-03-21: New content triage & weekly summary."""
    # 1. Loud: Lin Zhou approval email
    await ctx.email.send_email(
        from_user="lin_zhou",
        to="assistant@company.com",
        subject="[Approval] Competitor-like phrase approved after revision",
        body="The title can pass after the competitor-like phrase is revised.",
    )

    # 2. Silent: Sheet compliance_rate rolled back
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("compliance_rate")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!F3", [["temporarily rolled back"]],
        )

    # 3. Silent: 3 new content items (files already in assets, uploaded in stage0)
    # Add Notion records for new content
    new_content = [
        {"id": "CR-0321-15", "title": "Global Reels teaser",
         "platform": "Instagram Reels", "content_type": "Reels"},
        {"id": "CR-0321-16", "title": "TikTok Shop card",
         "platform": "TikTok", "content_type": "Shop Card"},
        {"id": "CR-0321-17", "title": "Basic Figma export",
         "platform": "Multi-platform", "content_type": "Banner"},
    ]
    for c in new_content:
        await ctx.notion.add_database_row(REVIEW_DB_NAME, {
            "Content ID": _notion_title(c["id"]),
            "Title": _notion_text(c["title"]),
            "Platform": _notion_text(c["platform"]),
            "Content Type": _notion_text(c["content_type"]),
            "Compliance Status": _notion_select("under_review"),
            "Reject Reason": _notion_text(""),
            "Waiver Needed": _notion_select("no"),
            "Issue Flag": _notion_select("no"),
            "Note": _notion_text(""),
        })

    # 4. Notification
    return {
        "notification": (
            "[2025-03-21 Friday] You have a new email from Lin Zhou. "
            "Please finalize pending statuses and send the weekly "
            "compliance summary before end of day."
        ),
        "time": "2025-03-21T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: First-Round Review --

async def _s0_csv_complete(ctx):
    """stage0_reviews.csv has ≥ 14 rows with valid enum fields"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    if len(rows) < 14:
        return False
    valid_status = {"approved", "rejected", "needs_review", "needs_waiver",
                    "pending_slot", "locked", "needs_recheck", "under_review",
                    "confirmed", "in_progress"}
    valid_issue = {"competitor_phrase", "color_waiver_required",
                   "sensitive_title", "slot_conflict",
                   "guideline_gap", "none", ""}
    for r in rows:
        if r.get("compliance_status", "").lower() not in valid_status:
            return False
        if r.get("issue_type", "").lower() not in valid_issue:
            return False
    return True


async def _s0_competitor_flagged(ctx):
    """Content 11 flagged as competitor_phrase + not approved in Notion"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    c11 = _find_csv_row(rows, "source_file", "competitor_title")
    if not c11:
        c11 = _find_csv_row(rows, "content_id", "11")
    if not c11:
        return False
    if c11.get("issue_type", "").lower() != "competitor_phrase":
        return False
    if c11.get("issue_flag", "").lower() != "yes":
        return False

    # Exceptions CSV also records this
    exc_rows = _read_csv(ctx, "stage0_exceptions.csv")
    exc = _find_csv_row(exc_rows, "exception_type", "competitor_phrase")
    if not exc:
        return False

    # Notion: competitor content not approved
    notion_rows = await ctx.notion.query_db(REVIEW_DB_NAME)
    for row in notion_rows:
        cid = _get_notion_field(row, "Content ID", "title")
        if "11" in cid or "competitor" in cid.lower():
            status = _get_notion_field(row, "Compliance Status", "select")
            if status.lower() == "approved":
                return False
    return True


async def _s0_color_flagged(ctx):
    """Content 12 flagged as color_waiver_required with waiver_needed=yes"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    c12 = _find_csv_row(rows, "source_file", "orange_key_visual")
    if not c12:
        c12 = _find_csv_row(rows, "content_id", "12")
    if not c12:
        return False
    if c12.get("issue_type", "").lower() != "color_waiver_required":
        return False
    if c12.get("waiver_needed", "").lower() != "yes":
        return False
    return True


async def _s0_sensitive_flagged(ctx):
    """Content 13 flagged as sensitive_title"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    c13 = _find_csv_row(rows, "source_file", "sensitive_title")
    if not c13:
        c13 = _find_csv_row(rows, "content_id", "13")
    if not c13:
        return False
    if c13.get("issue_type", "").lower() != "sensitive_title":
        return False
    if c13.get("issue_flag", "").lower() != "yes":
        return False
    return True


async def _s0_slot_conflict(ctx):
    """Content 14 flagged as slot_conflict"""
    rows = _read_csv(ctx, "stage0_reviews.csv")
    c14 = _find_csv_row(rows, "source_file", "wed_slot_claim")
    if not c14:
        c14 = _find_csv_row(rows, "content_id", "14")
    if not c14:
        return False
    if c14.get("issue_type", "").lower() != "slot_conflict":
        return False
    if c14.get("issue_flag", "").lower() != "yes":
        return False
    return True


async def _s0_notion_records(ctx):
    """Notion content_review has at least 13 records (3 initial + ≥10 new)"""
    rows = await ctx.notion.query_db(REVIEW_DB_NAME)
    return len(rows) >= 13


async def _s0_design_email_sent(ctx):
    """Design team received at least 1 email from agent"""
    emails = await ctx.email.get_emails("design")
    return len(emails) >= 1


async def _s0_linzhou_email_sent(ctx):
    """Lin Zhou received at least 1 email from agent (exception report)"""
    emails = await ctx.email.get_emails("lin_zhou")
    return len(emails) >= 1


async def _s0_no_unapproved_exception(ctx):
    """REVERSE: Content 11/12/13/14 must NOT be approved in Notion"""
    notion_rows = await ctx.notion.query_db(REVIEW_DB_NAME)
    if len(notion_rows) < 3:
        return False  # Notion DB must have at least the 3 seeded records
    for row in notion_rows:
        cid = _get_notion_field(row, "Content ID", "title")
        status = _get_notion_field(row, "Compliance Status", "select")
        for marker in ("11", "12", "13", "14"):
            if marker in cid and status.lower() == "approved":
                return False
    return True


# -- S1: Waiver Trace & Schedule Recheck --

async def _s1_color_status_repaired(ctx):
    """Content 12's incorrect 'confirmed' status fixed in CSV + Notion"""
    rows = _read_csv(ctx, "stage1_updates.csv")
    c12 = _find_csv_row(rows, "content_id", "12")
    if not c12:
        return False
    before = c12.get("status_before", "").lower()
    after = c12.get("status_after", "").lower()
    if before != "confirmed":
        return False
    if after == "confirmed":
        return False

    # Notion: content_12 should not be "confirmed"
    notion_rows = await ctx.notion.query_db(REVIEW_DB_NAME)
    for row in notion_rows:
        cid = _get_notion_field(row, "Content ID", "title")
        if "12" in cid or "orange" in cid.lower():
            status = _get_notion_field(row, "Compliance Status", "select")
            if status.lower() == "confirmed":
                return False
    return True


async def _s1_waiver_escalated(ctx):
    """Waiver decision handled with Lin Zhou involvement: CSV + inbox ≥ 2"""
    rows = _read_csv(ctx, "stage1_updates.csv")
    c12 = _find_csv_row(rows, "content_id", "12")
    if not c12:
        return False
    # Accept both "lin_zhou" (escalated) and "none"/"approved" (already approved)
    approver = c12.get("approver_needed", "").lower()
    status = c12.get("status_after", "").lower()
    # Either still needs escalation to lin_zhou, or already processed the approval
    if approver not in ("lin_zhou", "none", "") and status not in ("approved", "waiver_approved"):
        return False
    emails = await ctx.email.get_emails("lin_zhou")
    return len(emails) >= 2


async def _s1_no_unauthorized_approval(ctx):
    """REVERSE: Exception content not approved without proper trace"""
    notion_rows = await ctx.notion.query_db(REVIEW_DB_NAME)
    if len(notion_rows) < 3:
        return False  # DB must exist with records
    for row in notion_rows:
        cid = _get_notion_field(row, "Content ID", "title")
        status = _get_notion_field(row, "Compliance Status", "select")
        issue = _get_notion_field(row, "Issue Flag", "select")
        if issue.lower() == "yes" and status.lower() == "approved":
            return False
        for marker in ("13", "14"):
            if marker in cid and status.lower() == "approved":
                return False
    return True


# -- S2: New Content Triage & Summary --

async def _s2_new_content_csv(ctx):
    """stage2_new_content_triage.csv has ≥ 3 rows with valid enums"""
    rows = _read_csv(ctx, "stage2_new_content_triage.csv")
    if len(rows) < 3:
        return False
    valid_triage = {"ready", "needs_guideline", "needs_revision", "escalate"}
    for r in rows:
        if r.get("triage_status", "").lower() not in valid_triage:
            return False
    return True


async def _s2_guideline_gap_flagged(ctx):
    """At least 2 new content items flagged as guideline_gap"""
    rows = _read_csv(ctx, "stage2_new_content_triage.csv")
    gap_count = sum(
        1 for r in rows
        if r.get("issue_type", "").lower() == "guideline_gap"
    )
    return gap_count >= 2


async def _s2_sheet_compliance_rate(ctx):
    """Sheet compliance_rate for W12 is numeric, not empty or 'rolled back'"""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("compliance_rate")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!F3")
    if not vals or not vals[0] or not vals[0][0]:
        return False
    val = vals[0][0].lower()
    if "rolled" in val or "temporary" in val or val == "0%":
        return False
    return True


async def _s2_guideline_gap_email(ctx):
    """Lin Zhou received ≥ 3 emails (S0 exception + S1 waiver + S2 guideline gap)"""
    emails = await ctx.email.get_emails("lin_zhou")
    return len(emails) >= 3


async def _s2_weekly_summary_sent(ctx):
    """Lin Zhou received ≥ 4 emails (S0 + S1 + S2 gap + S2 weekly summary)"""
    emails = await ctx.email.get_emails("lin_zhou")
    return len(emails) >= 4


async def _s2_exception_content_resolved(ctx):
    """Notion: content_11 (competitor phrase) eventually approved after revision"""
    notion_rows = await ctx.notion.query_db(REVIEW_DB_NAME)
    for row in notion_rows:
        cid = _get_notion_field(row, "Content ID", "title")
        if "11" in cid or "competitor" in cid.lower():
            status = _get_notion_field(row, "Compliance Status", "select")
            return status.lower() == "approved"
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_csv_complete", "checker": _s0_csv_complete, "weight": 1.0},
        {"id": "S0_competitor_flagged", "checker": _s0_competitor_flagged, "weight": 2.0},
        {"id": "S0_color_flagged", "checker": _s0_color_flagged, "weight": 2.0},
        {"id": "S0_sensitive_flagged", "checker": _s0_sensitive_flagged, "weight": 2.0},
        {"id": "S0_slot_conflict", "checker": _s0_slot_conflict, "weight": 2.0},
        {"id": "S0_notion_records", "checker": _s0_notion_records, "weight": 1.0},
        {"id": "S0_design_email_sent", "checker": _s0_design_email_sent, "weight": 1.0},
        {"id": "S0_linzhou_email_sent", "checker": _s0_linzhou_email_sent, "weight": 1.0},
        {"id": "S0_no_unapproved_exception", "checker": _s0_no_unapproved_exception, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_color_status_repaired", "checker": _s1_color_status_repaired, "weight": 1.5},
        {"id": "S1_waiver_escalated", "checker": _s1_waiver_escalated, "weight": 2.0},
        {"id": "S1_no_unauthorized_approval", "checker": _s1_no_unauthorized_approval, "weight": 2.0},
    ],
    "stage2": [
        {"id": "S2_new_content_csv", "checker": _s2_new_content_csv, "weight": 1.0},
        {"id": "S2_guideline_gap_flagged", "checker": _s2_guideline_gap_flagged, "weight": 2.0},
        {"id": "S2_sheet_compliance_rate", "checker": _s2_sheet_compliance_rate, "weight": 1.5},
        {"id": "S2_guideline_gap_email", "checker": _s2_guideline_gap_email, "weight": 1.5},
        {"id": "S2_exception_content_resolved", "checker": _s2_exception_content_resolved, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_weekly_summary_sent", "checker": _s2_weekly_summary_sent, "weight": 1.0},
    ],
}
