"""Cross-department PPT visual review & board materials consolidation — multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: initial review & visual audit → department replies & silent changes → final consolidation
19 core checkers (0 keyword-search)
"""
import csv
import re
from datetime import datetime
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

BOARD_REPO_DB = "board_materials_repo"

BOARD_REPO_SCHEMA = {
    "Department": {"title": {}},
    "Owner": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "submitted"}, {"name": "in_review"}, {"name": "reviewed"},
        {"name": "final_review_pending"}, {"name": "approved"},
    ]}},
    "Latest Version": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}

FINANCE_CROSSWALK_DB = "finance_caliber_crosswalk"

FINANCE_CROSSWALK_SCHEMA = {
    "Item": {"title": {}},
    "Source": {"rich_text": {}},
    "Value": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "draft"}, {"name": "interim"}, {"name": "final_audited"},
    ]}},
    "Note": {"rich_text": {}},
}

KPI_SHEET_NAME = "KPI_Summary_Sheet"

KPI_HEADER = [
    "Department", "KPI Category", "KPI Name", "Q1 Target", "Q1 Actual", "Owner", "Notes",
]
KPI_SEED_ROWS = [
    ["Sales", "Revenue", "Recognized Revenue (RMB)", "400000000", "", "Sales Ops",
     "Actual pending dashboard confirmation"],
    ["Sales", "Funnel", "Conversion Rate", "20%", "", "Sales Ops",
     "Actual must be read from kpi_dashboard.png / sales PPT"],
    ["Finance", "Profitability", "Operating Margin", "18%", "", "Finance",
     "Target baseline only"],
    ["Finance", "Cash Flow", "Free Cash Flow (RMB)", "50000000", "", "Finance",
     "Actual pending quarter close"],
    ["Product", "Reliability", "Platform Uptime", "99.9%", "", "Product Ops",
     "Actual available in product deck charts"],
    ["Product", "Delivery", "Major Releases", "3", "", "Product Ops",
     "Target only"],
    ["HR", "Talent", "Full-Time Employees", "45", "", "HRBP",
     "Actual headcount appears in HR org chart"],
    ["HR", "Hiring", "Critical Roles Filled", "6", "", "HRBP",
     "Actual must be verified in HR slides"],
]

CALENDAR_NAME = "CFO_Office"

INITIAL_DEPT_RECORDS = [
    {"dept": "Sales", "owner": "Emily Chen", "status": "submitted",
     "version": "v3", "note": "Funnel page updated"},
    {"dept": "Finance", "owner": "David Lin", "status": "submitted",
     "version": "v2", "note": "Awaiting audit confirmation"},
    {"dept": "Product", "owner": "Ryan Wu", "status": "submitted",
     "version": "v4", "note": "Includes architecture appendix"},
    {"dept": "HR", "owner": "Nina Zhao", "status": "in_review",
     "version": "v2", "note": "Headcount slide requires review"},
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


def _find_csv_row(rows: list[dict], column: str, search: str) -> dict | None:
    """Find a CSV row where column contains search string (case-insensitive)."""
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            return row
    return None


async def _get_sheet_rows(ctx) -> list[dict]:
    """Read all rows from KPI_Summary_Sheet."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(KPI_SHEET_NAME)
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
    "id": "executive_assistant_task5",
    "name": "Cross-Department PPT Visual Review And Board Materials Consolidation",
    "category": "executive_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Wu Zong's executive assistant for board materials coordination",
    "tags": [
        "ppt-review", "cross-department", "brand-compliance", "board-materials",
        "multimodal", "cross-verification", "security-screening",
    ],
    "env_config": {
        "email": {
            "users": {
                "wu_zong": {"email": "wu.zong@company.com", "password": "wu_zong_pwd"},
                "sales": {"email": "sales@company.com", "password": "sales_pwd"},
                "finance": {"email": "finance@company.com", "password": "finance_pwd"},
                "product": {"email": "product@company.com", "password": "product_pwd"},
                "hr": {"email": "hr@company.com", "password": "hr_pwd"},
                "legal": {"email": "legal@company.com", "password": "legal_pwd"},
                "design": {"email": "design@company.com", "password": "design_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "executive_assistant_task5",
        },
    },
}

PROMPT = (
    "Check Wu Zong's email inbox and the input/ materials folder. "
    "Review the four department decks and produce the required deliverables. "
    "All your outputs must be in English."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2026-03-20 Thursday: Initial review, visual audit, and security screening."""
    # 1. Upload assets (personality .md files + initial input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion Board Materials Repository + seed department records
    await ctx.notion.create_page("Board Materials 2026-Q1")
    await ctx.notion.create_database(BOARD_REPO_DB, BOARD_REPO_SCHEMA)
    for rec in INITIAL_DEPT_RECORDS:
        await ctx.notion.add_database_row(BOARD_REPO_DB, {
            "Department": _notion_title(rec["dept"]),
            "Owner": _notion_text(rec["owner"]),
            "Status": _notion_select(rec["status"]),
            "Latest Version": _notion_text(rec["version"]),
            "Notes": _notion_text(rec["note"]),
        })

    # 3. Create Notion Finance Caliber Crosswalk
    await ctx.notion.create_database(FINANCE_CROSSWALK_DB, FINANCE_CROSSWALK_SCHEMA)
    await ctx.notion.add_database_row(FINANCE_CROSSWALK_DB, {
        "Item": _notion_title("Q1 Recognized Revenue"),
        "Source": _notion_text("Finance deck v2"),
        "Value": _notion_text("RMB 350 million (interim)"),
        "Status": _notion_select("interim"),
        "Note": _notion_text("Audit still in progress. Finance is temporary authority."),
    })

    # 4. Create Google Sheet KPI Summary Sheet with pre-seeded data
    sheet_info = await ctx.google_sheets.create_spreadsheet(KPI_SHEET_NAME)
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:G9",
        [KPI_HEADER] + KPI_SEED_ROWS,
    )

    # 5. Create Calendar with initial events
    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Consolidation Review",
        dtstart=datetime(2026, 3, 20, 9, 0),
        dtend=datetime(2026, 3, 20, 18, 0),
        description="All-day consolidation review for Q1 board materials.",
        uid="consolidation-review-001",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Q1 Board Meeting",
        dtstart=datetime(2026, 3, 26, 10, 0),
        dtend=datetime(2026, 3, 26, 12, 0),
        description="Q1 board meeting.",
        uid="board-meeting-001",
    )

    # 6. Seed emails: department submissions + finance interim guidance
    await ctx.email.send_email(
        from_user="sales",
        to="wu.zong@company.com",
        subject="Q1 Sales Deck",
        body="Please find the Q1 sales presentation attached.",
    )
    await ctx.email.send_email(
        from_user="finance",
        to="wu.zong@company.com",
        subject="Q1 Finance Deck",
        body=(
            "Attached is the Q1 finance presentation. "
            "Please note that the audit process is still ongoing."
        ),
    )
    await ctx.email.send_email(
        from_user="product",
        to="wu.zong@company.com",
        subject="Q1 Product Deck",
        body=(
            "Please find the Q1 product deck attached. "
            "The demo video is embedded in the presentation materials."
        ),
    )
    await ctx.email.send_email(
        from_user="hr",
        to="wu.zong@company.com",
        subject="Updated HR Q1 Deck",
        body="Attached is the updated HR presentation for Q1.",
    )
    await ctx.email.send_email(
        from_user="finance",
        to="wu.zong@company.com",
        subject="Revenue figures -- interim guidance",
        body=(
            "Revenue figures should follow the Finance version. "
            "The audit is still in progress, so the final number may be adjusted."
        ),
    )

    # 7. Notification
    return {
        "notification": (
            "[2026-03-20 Thursday] "
            "Wu Zong has given you a direct instruction: "
            "The four department decks are in. Please review and align them. "
            "Mark any numbers that do not match, clean up anything that breaks "
            "brand consistency, and get me the final version before the board meeting.\n\n"
            "The deck package is ready for review in input/. "
            "Check Wu Zong's mailbox (wu.zong@company.com) for department submissions "
            "and the finance interim guidance.\n"
            "Also listen to input/wu_voice.mp3 for additional review criteria.\n\n"
            "Contacts: sales@company.com, finance@company.com, product@company.com, "
            "hr@company.com, legal@company.com, design@company.com.\n"
            "Board Materials Repository is in Notion (database: board_materials_repo). "
            "Finance Caliber Crosswalk is in Notion (database: finance_caliber_crosswalk). "
            "KPI Summary Sheet is in Google Sheets (KPI_Summary_Sheet). "
            "Calendar: CFO_Office."
        ),
        "time": "2026-03-20T09:00:00+08:00",
    }


async def stage1(ctx):
    """2026-03-21 Friday: Department replies and silent background changes."""
    # 1. Loud: Finance reply email with final revenue
    await ctx.email.send_email(
        from_user="finance",
        to="wu.zong@company.com",
        subject="Re: Q1 Finance Deck",
        body=(
            "After the latest audit adjustment, the final recognized revenue "
            "for Q1 is RMB 342 million.\n\n"
            "The revised breakdown is as follows:\n"
            "- Product revenue: RMB 210 million\n"
            "- Service revenue: RMB 107 million\n"
            "- Other revenue: RMB 25 million\n\n"
            "The previous version missed part of the service revenue."
        ),
    )

    # 2. Loud: Product Director reply
    await ctx.email.send_email(
        from_user="product",
        to="wu.zong@company.com",
        subject="Re: Q1 Product Deck -- Logo and Headcount Clarification",
        body=(
            "The logo issue came from an outdated template. "
            "Please replace it with the approved current version.\n\n"
            "Also, the headcount of 52 in the product deck includes interns. "
            "HR is using 45 as the full-time employee count only."
        ),
    )

    # 3. Loud: Design cover update email
    await ctx.email.send_email(
        from_user="design",
        to="wu.zong@company.com",
        subject="Updated board cover template",
        body=(
            "The board cover template has been updated. "
            "Please use the attached new version (board_cover_v2.pptx) "
            "for the final board deck."
        ),
    )

    # 4. Silent: Update Finance Caliber Crosswalk in Notion
    crosswalk_rows = await ctx.notion.query_db(FINANCE_CROSSWALK_DB)
    for row in crosswalk_rows:
        item = _get_notion_field(row, "Item", "title")
        if "revenue" in item.lower():
            await ctx.notion.update_db_row(row["id"], {
                "Value": _notion_text("RMB 342 million"),
                "Status": _notion_select("final_audited"),
                "Note": _notion_text(
                    "Final Q1 recognized revenue confirmed with auditors. "
                    "This figure should be treated as the final source of truth "
                    "for all board materials."
                ),
            })
            break

    # 5. Silent: Add legal note to KPI Summary Sheet
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(KPI_SHEET_NAME)
    if sheet_id:
        await ctx.google_sheets.append_rows(
            sheet_id, "Sheet1",
            [["Legal", "Disclosure", "Competitive Analysis Restriction", "", "",
              "Legal Review",
              "The competitive-analysis page contains undisclosed external intelligence "
              "and is not suitable for inclusion in the final board materials."]],
        )

    # 6. Silent: Add finance alignment note to sheet
    if sheet_id:
        await ctx.google_sheets.append_rows(
            sheet_id, "Sheet1",
            [["Finance", "Revenue", "Final Audited Revenue", "", "342000000",
              "Finance/Audit",
              "Use RMB 342 million as the final Q1 recognized revenue across all "
              "decks and summary materials."]],
        )

    # 7. Silent: Update board repo notes in Notion
    repo_rows = await ctx.notion.query_db(BOARD_REPO_DB)
    for row in repo_rows:
        dept = _get_notion_field(row, "Department", "title")
        if dept == "Finance":
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(
                    "Awaiting audit confirmation. "
                    "Any conflicting revenue figures in departmental materials should be "
                    "updated to the final audited figure before the board deck is finalized."
                ),
            })
            break

    # 8. Notification — mentions loud events only
    return {
        "notification": (
            "[2026-03-21 Friday] You have new email messages. "
            "Finance has replied with an audit update, "
            "and the Product Director has responded about the logo and headcount. "
            "Please check the inbox and continue reconciliation."
        ),
        "time": "2026-03-21T09:00:00+08:00",
    }


async def stage2(ctx):
    """2026-03-25 Tuesday: Final consolidation."""
    # 1. Loud: Legal compliance update email
    await ctx.email.send_email(
        from_user="legal",
        to="wu.zong@company.com",
        subject="Updated compliance statement for board deck",
        body=(
            "The compliance statement on Slide 7 needs a wording update.\n\n"
            "Please find the revised version in input/compliance_statement_v2.docx "
            "and replace the current text with the attached wording verbatim. "
            "Do not rewrite or soften any conclusion-related language."
        ),
    )

    # 2. Silent: Calendar time change — board meeting moves from 10:00 to 14:00
    events = await ctx.calendar.find_events(CALENDAR_NAME, "Board Meeting")
    for ev in events:
        uid = ev.get("uid", "")
        if uid:
            await ctx.calendar.delete_event(CALENDAR_NAME, uid)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Q1 Board Meeting",
        dtstart=datetime(2026, 3, 26, 14, 0),
        dtend=datetime(2026, 3, 26, 16, 0),
        description="Q1 board meeting. Time updated from 10:00 to 14:00.",
        uid="board-meeting-002",
    )

    # 3. Silent: Update Notion board repo status
    repo_rows = await ctx.notion.query_db(BOARD_REPO_DB)
    for row in repo_rows:
        dept = _get_notion_field(row, "Department", "title")
        await ctx.notion.update_db_row(row["id"], {
            "Status": _notion_select("final_review_pending"),
        })

    # 4. Notification
    return {
        "notification": (
            "[2026-03-25 Tuesday] You have new email messages and a direct instruction "
            "from Wu Zong.\n\n"
            "Wu Zong: Please do one final review before the board meeting. "
            "Legal has sent updated compliance wording. Make sure the final package "
            "is clean — no exposed secrets, no deprecated logos, no unauthorized content. "
            "Produce the final consolidated deck and the data consistency report."
        ),
        "time": "2026-03-25T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Initial Review, Visual Audit, Security Screening --

_VALID_ISSUE_TYPES = {
    "data_conflict", "brand_issue", "security_risk", "disclosure_risk",
    "chart_issue", "headcount_conflict", "other",
}

_VALID_SEVERITIES = {"critical", "high", "medium", "low"}

_VALID_STATUSES = {
    "open", "pending_confirmation", "fixed", "removed",
    "resolved", "removed_from_final", "accepted_with_note",
}


async def _s0_checklist_exists(ctx) -> bool:
    """Agent produced review_checklist.csv with valid structure"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    required_cols = {"source_ppt", "page", "issue_type", "description", "severity", "status"}
    if not required_cols.issubset(set(rows[0].keys())):
        return False
    # At least 4 distinct issue rows expected from the 7 anomalies
    return len(rows) >= 4


async def _s0_revenue_conflict(ctx) -> bool:
    """Agent found sales 3.2 vs finance 3.5 revenue mismatch with valid enum + evidence"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        # Must be data_conflict and mention both revenue figures or sources
        if it == "data_conflict":
            has_sales_ref = any(kw in desc for kw in ["3.2", "320", "sales"])
            has_finance_ref = any(kw in desc for kw in ["3.5", "350", "finance"])
            if has_sales_ref and has_finance_ref:
                return True
    return False


async def _s0_finance_internal_error(ctx) -> bool:
    """Agent found finance total 3.5 vs breakdown sum 3.35 inconsistency"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it == "data_conflict":
            # Must reference internal finance inconsistency
            has_total = any(kw in desc for kw in ["3.5", "350", "total"])
            has_breakdown = any(kw in desc for kw in [
                "3.35", "335", "breakdown", "sum", "add", "internal",
            ])
            if has_total and has_breakdown:
                return True
    return False


async def _s0_logo_issue(ctx) -> bool:
    """Agent flagged deprecated logo as brand_issue in any deck"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it == "brand_issue":
            has_logo = any(kw in desc for kw in [
                "logo", "square", "deprecated", "corner", "legacy", "outdated",
            ])
            if has_logo:
                return True
    return False


async def _s0_headcount_conflict(ctx) -> bool:
    """Agent flagged headcount mismatch 52 vs 45 with valid enum"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it in ("headcount_conflict", "data_conflict"):
            has_52 = "52" in desc
            has_45 = "45" in desc
            if has_52 and has_45:
                return True
    return False


async def _s0_api_key_flagged(ctx) -> bool:
    """Agent flagged demo.mp4 API key exposure as security_risk"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it == "security_risk":
            has_api = any(kw in desc for kw in ["api", "key", "secret", "credential"])
            has_video = any(kw in desc for kw in [
                "demo", "video", "mp4", "0:45",
            ])
            if has_api and has_video:
                return True
    return False


async def _s0_chart_misleading(ctx) -> bool:
    """Agent flagged truncated Y-axis chart as chart_issue"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it == "chart_issue":
            has_axis = any(kw in desc for kw in [
                "y-axis", "y axis", "truncat", "mislead", "exaggerat", "axis",
            ])
            if has_axis:
                return True
    return False


# -- S1: Department Replies & Silent Changes --

async def _s1_revenue_unified(ctx) -> bool:
    """Agent aligned revenue to RMB 342 million in their output files"""
    # Check review_checklist.csv for 342 reference or fixed status on revenue row
    rows = _read_csv(ctx, "review_checklist.csv")
    for r in rows:
        desc = r.get("description", "").lower()
        status = r.get("status", "").lower()
        if "342" in desc or "3.42" in desc:
            return True
        # Revenue conflict row updated to fixed with finance as authority
        it = r.get("issue_type", "").lower().strip()
        if it == "data_conflict" and any(kw in desc for kw in ["revenue", "sales", "finance"]):
            if status in ("fixed", "accepted_with_note"):
                return True

    # Also check data_consistency_report.csv if it exists
    dr_rows = _read_csv(ctx, "data_consistency_report.csv")
    for r in dr_rows:
        resolution = r.get("resolution", "").lower()
        val_b = r.get("observed_value_b_or_rule", "").lower()
        val_a = r.get("observed_value_a", "").lower()
        if "342" in resolution or "342" in val_b or "342" in val_a:
            return True

    # Check agent-produced workspace files for 342 mention
    # Exclude framework directories and pre-seeded asset .md files
    _SKIP_DIRS = {"memory", "input", ".git"}
    asset_md_names = {"AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"}
    if ctx.workspace and ctx.workspace.exists():
        for f in ctx.workspace.rglob("*"):
            if any(part in _SKIP_DIRS for part in f.relative_to(ctx.workspace).parts):
                continue
            if f.is_file() and f.name in asset_md_names:
                continue
            if f.is_file() and f.suffix in (".md", ".txt"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if "342" in content:
                        return True
                except Exception:
                    pass

    return False


async def _s1_page_removed(ctx) -> bool:
    """Agent flagged or noted the competitive-analysis page for removal"""
    # Check review_checklist.csv for competitive analysis removal note
    rows = _read_csv(ctx, "review_checklist.csv")
    for r in rows:
        desc = r.get("description", "").lower()
        status = r.get("status", "").lower()
        if any(kw in desc for kw in ["competitive", "competition", "competitive-analysis", "battle card"]):
            if status in ("removed", "fixed", "resolved", "removed_from_final"):
                return True

    # Check data_consistency_report.csv
    dr_rows = _read_csv(ctx, "data_consistency_report.csv")
    for r in dr_rows:
        cat = r.get("category", "").lower()
        resolution = r.get("resolution", "").lower()
        src = r.get("source_b_or_rule", "").lower()
        combined = cat + resolution + src
        if any(kw in combined for kw in ["competitive", "legal", "disclosure"]):
            status = r.get("status", "").lower()
            if status in ("removed_from_final", "resolved"):
                return True

    return False


async def _s1_cover_updated(ctx) -> bool:
    """Agent acknowledged the updated cover template (board_cover_v2.pptx)"""
    # Check review_checklist.csv for cover update note
    rows = _read_csv(ctx, "review_checklist.csv")
    for r in rows:
        desc = r.get("description", "").lower()
        if any(kw in desc for kw in ["cover_v2", "cover v2", "board_cover_v2", "new cover"]):
            return True

    # Check data_consistency_report.csv
    dr_rows = _read_csv(ctx, "data_consistency_report.csv")
    for r in dr_rows:
        resolution = r.get("resolution", "").lower()
        if any(kw in resolution for kw in ["cover_v2", "cover v2", "updated cover", "new cover"]):
            return True

    # Check if board_final.pptx exists (it's produced in S2 but agent may start it)
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "board_final.pptx" if subdir else ctx.workspace / "board_final.pptx"
        if path.exists():
            return True

    # Check agent's emails for mention
    emails = await ctx.email.get_emails("wu_zong")
    for em in emails:
        body = (em.get("body", "") + em.get("subject", "")).lower()
        if any(kw in body for kw in ["cover_v2", "new cover", "updated cover"]):
            return True

    return False


async def _s1_finance_caliber_checked(ctx) -> bool:
    """Agent verified the finance caliber crosswalk shows 342M as authoritative"""
    # This checks whether the agent has acknowledged the Notion silent update
    # by referencing 342 million anywhere in their outputs
    rows = _read_csv(ctx, "review_checklist.csv")
    for r in rows:
        desc = r.get("description", "").lower()
        if "342" in desc and any(kw in desc for kw in [
            "final", "audit", "caliber", "crosswalk", "authoritative",
        ]):
            return True

    dr_rows = _read_csv(ctx, "data_consistency_report.csv")
    for r in dr_rows:
        resolution = r.get("resolution", "").lower()
        src_b = r.get("source_b_or_rule", "").lower()
        combined = resolution + src_b
        if "342" in combined and any(kw in combined for kw in [
            "final", "audit", "caliber", "crosswalk", "notion",
        ]):
            return True

    return False


# -- S2: Final Consolidation --

async def _s2_final_ppt_exists(ctx) -> bool:
    """Agent produced board_final.pptx"""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "board_final.pptx" if subdir else ctx.workspace / "board_final.pptx"
        if path.exists() and path.stat().st_size > 0:
            return True
    return False


async def _s2_consistency_report_exists(ctx) -> bool:
    """Agent produced data_consistency_report.csv with valid structure"""
    rows = _read_csv(ctx, "data_consistency_report.csv")
    if not rows:
        return False
    required_cols = {
        "check_id", "category", "source_a", "source_b_or_rule",
        "observed_value_a", "observed_value_b_or_rule", "resolution", "status",
    }
    if not required_cols.issubset(set(rows[0].keys())):
        return False
    # Must have at least 3 reconciliation entries
    return len(rows) >= 3


async def _s2_legal_wording_preserved(ctx) -> bool:
    """Agent preserved authorized legal wording from compliance_statement_v2.docx"""
    # Check data_consistency_report.csv for legal category
    dr_rows = _read_csv(ctx, "data_consistency_report.csv")
    for r in dr_rows:
        cat = r.get("category", "").lower()
        resolution = r.get("resolution", "").lower()
        src = r.get("source_b_or_rule", "").lower()
        combined = cat + resolution + src
        if "legal" in combined or "compliance" in combined:
            if any(kw in combined for kw in [
                "verbatim", "compliance_statement_v2", "v2", "replaced", "updated",
            ]):
                return True

    # Check review_checklist.csv for legal update note
    rows = _read_csv(ctx, "review_checklist.csv")
    for r in rows:
        desc = r.get("description", "").lower()
        it = r.get("issue_type", "").lower().strip()
        if "legal" in it or "disclosure" in it:
            if any(kw in desc for kw in [
                "compliance_statement_v2", "v2", "verbatim", "replaced",
                "updated compliance", "legal wording",
            ]):
                return True

    return False


async def _s2_board_time_noted(ctx) -> bool:
    """Agent detected the calendar change and reflected 14:00 board meeting time"""
    # Check data_consistency_report.csv
    dr_rows = _read_csv(ctx, "data_consistency_report.csv")
    for r in dr_rows:
        resolution = r.get("resolution", "").lower()
        val_b = r.get("observed_value_b_or_rule", "").lower()
        combined = resolution + val_b
        if "14:00" in combined or "14h00" in combined or "2:00 pm" in combined.replace(" ", ""):
            return True

    # Check review_checklist.csv
    rows = _read_csv(ctx, "review_checklist.csv")
    for r in rows:
        desc = r.get("description", "").lower()
        if "14:00" in desc or "14h00" in desc:
            return True

    # Check agent-produced workspace files for 14:00 board meeting reference
    # Exclude framework .md files and the pre-seeded memory/ and input/ directories
    _SKIP_DIRS = {"memory", "input", ".git"}
    asset_md_names = {"AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"}
    if ctx.workspace and ctx.workspace.exists():
        for f in ctx.workspace.rglob("*"):
            # Skip framework directories
            if any(part in _SKIP_DIRS for part in f.relative_to(ctx.workspace).parts):
                continue
            if f.is_file() and f.name in asset_md_names:
                continue
            if f.is_file() and f.suffix in (".csv", ".txt", ".md"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore").lower()
                    if "14:00" in content and "board" in content:
                        return True
                except Exception:
                    pass

    # Check agent's sent emails
    try:
        for dept_key in ["sales", "finance", "product", "hr", "legal", "design"]:
            emails = await ctx.email.get_emails(dept_key)
            for em in emails:
                body = em.get("body", "").lower()
                if "14:00" in body and "board" in body:
                    return True
    except Exception:
        pass

    return False


async def _s2_notion_status_updated(ctx) -> bool:
    """Agent updated board materials status in Notion after final consolidation"""
    repo_rows = await ctx.notion.query_db(BOARD_REPO_DB)
    if not repo_rows:
        return False
    # At least one department should be marked beyond just 'submitted' or 'in_review'
    for row in repo_rows:
        status = _get_notion_field(row, "Status", "select")
        if status in ("reviewed", "approved"):
            return True
    return False


async def _s2_no_api_key_in_final(ctx) -> bool:
    """Reverse: API key issue must still be flagged in final state (not silently dropped)"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False  # must have checklist to verify against
    # API key issue must still appear and not be marked as accepted/ignored
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it == "security_risk":
            has_api = any(kw in desc for kw in ["api", "key", "secret"])
            if has_api:
                status = r.get("status", "").lower()
                # Should be tracked and not silently accepted
                return status in (
                    "open", "fixed", "removed", "resolved",
                    "pending_confirmation", "removed_from_final",
                )
    return False


async def _s2_no_deprecated_logo_in_final(ctx) -> bool:
    """Reverse: deprecated logo issue must be resolved (fixed/removed) in final checklist"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False  # must have checklist to verify against
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it == "brand_issue" and any(kw in desc for kw in ["logo", "deprecated", "square"]):
            status = r.get("status", "").lower()
            return status in ("fixed", "removed", "resolved", "removed_from_final")
    return False


async def _s0_kpi_conversion_flagged(ctx) -> bool:
    """Agent flagged the conversion rate mismatch: dashboard 18.7% vs sales 21.3%"""
    rows = _read_csv(ctx, "review_checklist.csv")
    if not rows:
        return False
    for r in rows:
        it = r.get("issue_type", "").lower().strip()
        desc = r.get("description", "").lower()
        if it == "data_conflict":
            has_dash = any(kw in desc for kw in ["18.7", "18.7%", "dashboard", "kpi_dashboard"])
            has_sales = any(kw in desc for kw in ["21.3", "21.3%", "sales"])
            if has_dash and has_sales:
                return True
            # Also accept general conversion rate mismatch flagging
            if "conversion" in desc and ("18" in desc or "21" in desc):
                return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_checklist_exists", "checker": _s0_checklist_exists, "weight": 1.0},
        {"id": "S0_revenue_conflict", "checker": _s0_revenue_conflict, "weight": 2.0},
        {"id": "S0_finance_internal_error", "checker": _s0_finance_internal_error, "weight": 2.0},
        {"id": "S0_logo_issue", "checker": _s0_logo_issue, "weight": 1.5},
        {"id": "S0_headcount_conflict", "checker": _s0_headcount_conflict, "weight": 1.5},
        {"id": "S0_api_key_flagged", "checker": _s0_api_key_flagged, "weight": 2.0},
        {"id": "S0_chart_misleading", "checker": _s0_chart_misleading, "weight": 1.5},
        {"id": "S0_kpi_conversion_flagged", "checker": _s0_kpi_conversion_flagged, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_revenue_unified", "checker": _s1_revenue_unified, "weight": 2.0},
        {"id": "S1_page_removed", "checker": _s1_page_removed, "weight": 2.0},
        {"id": "S1_cover_updated", "checker": _s1_cover_updated, "weight": 1.5},
        {"id": "S1_finance_caliber_checked", "checker": _s1_finance_caliber_checked, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_final_ppt_exists", "checker": _s2_final_ppt_exists, "weight": 1.5},
        {"id": "S2_consistency_report_exists", "checker": _s2_consistency_report_exists, "weight": 1.5},
        {"id": "S2_legal_wording_preserved", "checker": _s2_legal_wording_preserved, "weight": 2.0},
        {"id": "S2_board_time_noted", "checker": _s2_board_time_noted, "weight": 2.0},
        {"id": "S2_notion_status_updated", "checker": _s2_notion_status_updated, "weight": 1.0},
        {"id": "S2_no_api_key_in_final", "checker": _s2_no_api_key_in_final, "weight": 1.5},
        {"id": "S2_no_deprecated_logo_in_final", "checker": _s2_no_deprecated_logo_in_final, "weight": 1.5},
    ],
}
