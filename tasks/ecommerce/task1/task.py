"""Batch defect assessment & supplier escalation — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
4 stages: familiarize → complaint analysis → supplier follow-up → escalation & weekly report
15 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

QC_DB_NAME = "qc_events"

QC_DB_SCHEMA = {
    "event_id": {"title": {}},
    "lot_id": {"rich_text": {}},
    "sku": {"rich_text": {}},
    "supplier": {"rich_text": {}},
    "event_type": {"select": {"options": [
        {"name": "complaint"}, {"name": "return_spike"},
        {"name": "inspection"},
    ]}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "investigating"},
        {"name": "escalated"}, {"name": "resolved"}, {"name": "closed"},
    ]}},
    "severity": {"select": {"options": [
        {"name": "low"}, {"name": "medium"},
        {"name": "high"}, {"name": "critical"},
    ]}},
    "return_rate": {"number": {}},
    "created_date": {"rich_text": {}},
    "notes": {"rich_text": {}},
}

RETURN_RATES_HEADER = [
    "lot_id", "sku", "shipped_units", "return_count", "return_rate",
]
RETURN_RATES_ROWS = [
    ["lot-240301", "HW-K2201", "1200", "18", "1.50%"],
    ["lot-240302", "HW-K2201", "800", "9", "1.13%"],
    ["lot-240315", "HW-K2202", "600", "5", "0.83%"],
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
    """Find a CSV row where *column* contains *search* (case-insensitive)."""
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
    elif field_type == "number":
        return prop.get("number", 0)
    return ""


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "ecommerce_task1",
    "name": "Batch Defect Assessment & Supplier Escalation",
    "category": "ecommerce",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Jie's QC assistant at Curato",
    "tags": [
        "qc", "complaints", "supplier", "defects",
        "multimodal", "cross-modal", "dedup", "escalation",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@curato.com",
                    "password": "assistant_pwd",
                },
                "chenjie": {
                    "email": "chenjie@curato.com",
                    "password": "chenjie_pwd",
                },
                "supplier_a": {
                    "email": "supplier-a@curato.com",
                    "password": "supplier_a_pwd",
                },
                "zhaoqiang": {
                    "email": "zhaoqiang@curato.com",
                    "password": "zhaoqiang_pwd",
                },
                "wanglei": {
                    "email": "wanglei@curato.com",
                    "password": "wanglei_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "ecommerce_task1",
        },
    },
}

PROMPT = "Check your email and workspace for new complaint files to process."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-18 09:15: Environment setup & familiarization."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create empty Notion qc_events database
    await ctx.notion.create_page("Quality Events 2024-Q1")
    await ctx.notion.create_database(QC_DB_NAME, QC_DB_SCHEMA)

    # 3. Create Google Sheets return_rates + seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet("return_rates")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:E4",
        [RETURN_RATES_HEADER] + RETURN_RATES_ROWS,
    )

    # 4. Seed email from Chen Jie
    await ctx.email.send_email(
        from_user="chenjie",
        to="assistant@curato.com",
        subject="Return Rate Monitoring",
        body=(
            "Hi An,\n\n"
            "The warehouse says returns have been increasing recently. "
            "Please keep an eye on it and let me know if you see any patterns.\n\n"
            "Best,\nJie"
        ),
    )

    # 5. Notification — includes Feishu message as text
    return {
        "notification": (
            "[2024-03-18 Monday 09:15] You have a new email from Chen Jie "
            "and a Feishu message.\n\n"
            "Your email: assistant@curato.com. "
            "Chen Jie: chenjie@curato.com. "
            "Zhao Qiang (manager): zhaoqiang@curato.com.\n"
            "QC event tracking: Notion database 'qc_events'. "
            "Return rates: Google Sheets 'return_rates'.\n"
            "Reference docs and data in /workspace/input/. "
            "SQLite database at /workspace/input/orders.db "
            "(query with sqlite3).\n\n"
            "[Feishu] Li (Customer Service): "
            "\"Hey An, I've put a batch of files in the complaints/ folder "
            "— recent negative reviews and returns data. "
            "Please take a look when you get a chance. "
            "Some customers sound pretty upset.\"\n\n"
            "Note: The complaints/ folder is currently empty. "
            "New complaint files will arrive shortly."
        ),
        "time": "2024-03-18T09:15:00+08:00",
    }


async def stage1(ctx):
    """2024-03-18 10:30: First batch of complaints arrives."""
    # 1. Inject complaint files into /workspace/input/complaints/
    inject_dir = ctx.task_dir / "inject" / "stage1"
    await ctx.fs.upload_dir(inject_dir, "/workspace/input/complaints")

    # 2. Notification — Feishu from Li
    return {
        "notification": (
            "[2024-03-18 Monday 10:30] New complaint files have arrived.\n\n"
            "[Feishu] Li (Customer Service): "
            "\"New complaints are in the complaints/ folder. "
            "Please analyze and classify them. "
            "If it looks like a batch issue, file a case.\"\n\n"
            "Policy reference: /workspace/input/returns_policy_v2.pdf. "
            "Data: /workspace/input/sales_by_lot.xlsx "
            "and /workspace/input/orders.db."
        ),
        "time": "2024-03-18T10:30:00+08:00",
    }


async def stage2(ctx):
    """2024-03-19 14:00: Supplier reply + new silent complaints."""
    # 1. Loud: Supplier A sends sub-batch detail email
    await ctx.email.send_email(
        from_user="supplier_a",
        to="assistant@curato.com",
        subject="RE: Quality Report — lot-240301 Sub-Batch Detail",
        body=(
            "Hi,\n\n"
            "Regarding lot-240301, we've traced the production records and "
            "found the lot was split into two sub-batches:\n\n"
            "- A1: Produced 2024-03-01, Line 1, new mold, 600 units\n"
            "- A2: Produced 2024-03-03, Line 2, old mold, 600 units\n\n"
            "The sub-batch detail spreadsheet is attached.\n"
            "Please refer to the file at "
            "/workspace/input/complaints/sub_batch_detail.xlsx\n\n"
            "Regards,\nMingfeng Supply Chain"
        ),
    )

    # 2. Upload sub_batch_detail.xlsx as email attachment equivalent
    inject_s2 = ctx.task_dir / "inject" / "stage2"
    await ctx.fs.upload_file(
        inject_s2 / "sub_batch_detail.xlsx",
        "/workspace/input/complaints/sub_batch_detail.xlsx",
    )

    # 3. Silent: Inject new complaint files (agent should discover)
    await ctx.fs.upload_file(
        inject_s2 / "review_04.png",
        "/workspace/input/complaints/review_04.png",
    )
    await ctx.fs.upload_file(
        inject_s2 / "call_03.mp3",
        "/workspace/input/complaints/call_03.mp3",
    )

    # 4. Silent: Update Sheets return_count for lot-240302 (9 → 14)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("return_rates")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!D3", [["14"]],
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!E3", [["1.75%"]],
        )

    # 5. Notification — only mentions the loud event
    return {
        "notification": "You have a new email from a supplier.",
        "time": "2024-03-19T14:00:00+08:00",
    }


async def stage3(ctx):
    """2024-03-25 Monday 09:00: Escalation & weekly report."""
    # 1. Silent: Mark Notion events as overdue (supplier 48h SLA breached)
    rows = await ctx.notion.query_db(QC_DB_NAME)
    for row in rows:
        status = _get_notion_field(row, "status", "select")
        if status.lower() in ("open", "investigating"):
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Supplier response overdue — 48h SLA breached"
                ),
            })
            break

    # 2. Notification — Feishu from Chen Jie + it's Monday (weekly report)
    return {
        "notification": (
            "[2024-03-25 Monday 09:00] New Feishu message. "
            "It's Monday — weekly reports are due.\n\n"
            "[Feishu] Chen Jie: "
            "\"Supplier A still hasn't responded? "
            "Escalate this — CC procurement director Wang Lei "
            "(wanglei@curato.com). We need answers.\""
        ),
        "time": "2024-03-25T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S1: Complaint Analysis --


async def _s1_competitor_excluded(ctx):
    """review_01.png complaint marked as invalid (competitor product)."""
    rows = _read_csv(ctx, "complaint_analysis.csv")
    # review_01.png shows a product with AETERNA (competitor) logo
    row = _find_csv_row(rows, "source", "review_01")
    if not row:
        return False
    return row.get("is_valid", "").upper() == "NO"


async def _s1_dedup_applied(ctx):
    """No duplicate order_ids among valid complaints in CSV."""
    rows = _read_csv(ctx, "complaint_analysis.csv")
    valid_order_ids = [
        r.get("order_id", "").strip()
        for r in rows
        if r.get("is_valid", "").upper() == "YES"
        and r.get("order_id", "").strip()
    ]
    return len(valid_order_ids) == len(set(valid_order_ids))


async def _s1_denominator_corrected(ctx):
    """Sheets lot-240301 shipped_units corrected from 1200 to ~1082."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("return_rates")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A2:C4")
    if not vals:
        return False
    for row in vals:
        if len(row) >= 3 and row[0] == "lot-240301":
            try:
                shipped = int(str(row[2]).replace(",", ""))
                # Should be ~1082 (1200 - 118 cancelled), tolerance ±40
                return 1050 <= shipped <= 1120
            except (ValueError, IndexError):
                return False
    return False


async def _s1_crack_root_cause(ctx):
    """Lot-240301 crack attributed to transport/storage (cross-modal reasoning)."""
    rows = _read_csv(ctx, "complaint_analysis.csv")
    for row in rows:
        lot = row.get("lot_id", "").lower()
        is_valid = row.get("is_valid", "").upper()
        damage = row.get("damage_type", "").lower()
        root = row.get("root_cause", "").lower()
        if ("240301" in lot and is_valid == "YES" and damage == "crack"
                and root in ("transport", "storage")):
            return True
    return False


async def _s1_notion_created(ctx):
    """Notion qc_events has at least 1 quality event record."""
    rows = await ctx.notion.query_db(QC_DB_NAME)
    return len(rows) >= 1


# -- S2: Supplier Follow-up --


async def _s2_sub_lot_split(ctx):
    """CSV or Notion reflects sub-batch split (A1/A2) for lot-240301."""
    # Check CSV for sub-lot references
    rows = _read_csv(ctx, "complaint_analysis.csv")
    for row in rows:
        lot = row.get("lot_id", "").strip().lower()
        notes = row.get("notes", "").lower()
        if any(tag in lot for tag in ("a1", "a2", "sub")):
            return True
        if "240301" in lot and ("a1" in notes or "a2" in notes):
            return True
    # Check Notion for sub-lot records
    notion_rows = await ctx.notion.query_db(QC_DB_NAME)
    for row in notion_rows:
        lot_val = _get_notion_field(row, "lot_id").lower()
        notes_val = _get_notion_field(row, "notes").lower()
        if any(tag in lot_val for tag in ("a1", "a2", "sub")):
            return True
        if "a1" in notes_val or "a2" in notes_val:
            return True
    return False


async def _s2_new_complaints_found(ctx):
    """Agent discovered silently injected complaint files (review_04, call_03)."""
    rows = _read_csv(ctx, "complaint_analysis.csv")
    for r in rows:
        source = r.get("source", "").lower()
        lot = r.get("lot_id", "").lower()
        if "review_04" in source or "call_03" in source:
            return True
        # review_04.png is for lot-240302 — if new 302 entries appeared
        if "240302" in lot and "review" in source:
            return True
    return False


async def _s2_lot302_rate_noted(ctx):
    """Agent reacted to lot-240302 return rate increase — created QC event."""
    # Require Notion event (CSV entry alone could be from stage1 complaint processing)
    notion_rows = await ctx.notion.query_db(QC_DB_NAME)
    for row in notion_rows:
        lot = _get_notion_field(row, "lot_id")
        if "240302" in lot:
            return True
    # Also accept: CSV has lot-240302 entry with severity >= major
    rows = _read_csv(ctx, "complaint_analysis.csv")
    for r in rows:
        if "240302" in r.get("lot_id", ""):
            sev = r.get("severity", "").lower()
            if sev in ("major", "critical"):
                return True
    return False


async def _s2_supplier_report_sent(ctx):
    """Supplier A received a quality report email (body > 100 chars)."""
    emails = await ctx.email.get_emails("supplier_a")
    for e in emails:
        if len(e.get("body", "")) > 100:
            return True
    return False


async def _s2_chenjie_updated(ctx):
    """Chen Jie received at least 1 update email from agent."""
    emails = await ctx.email.get_emails("chenjie")
    return len(emails) >= 1


# -- S3: Escalation & Weekly Report --


async def _s3_escalation_cc_wanglei(ctx):
    """Wang Lei (procurement director) received CC'd escalation email."""
    emails = await ctx.email.get_emails("wanglei")
    return len(emails) >= 1


async def _s3_notion_escalated(ctx):
    """At least 1 Notion qc_events record has status 'escalated'."""
    rows = await ctx.notion.query_db(QC_DB_NAME)
    for row in rows:
        status = _get_notion_field(row, "status", "select").lower()
        if status in ("escalated", "escalating"):
            return True
    return False


async def _s3_weekly_report_sent(ctx):
    """Zhao Qiang received at least 1 email (weekly report)."""
    emails = await ctx.email.get_emails("zhaoqiang")
    return len(emails) >= 1


async def _s3_supplier_reminded(ctx):
    """Supplier A received ≥2 emails (quality report + escalation reminder)."""
    emails = await ctx.email.get_emails("supplier_a")
    return len(emails) >= 2


async def _s3_sheets_updated(ctx):
    """Sheets return_rates has been updated beyond initial seed."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("return_rates")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:E10")
    if not vals:
        return False
    # Either more rows than original (header + 3), or lot-240301 corrected
    if len(vals) > 4:
        return True
    for row in vals[1:]:
        if len(row) >= 3 and row[0] == "lot-240301":
            try:
                shipped = int(str(row[2]).replace(",", ""))
                if shipped != 1200:
                    return True
            except ValueError:
                pass
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage1": [
        {"id": "S1_competitor_excluded",
         "checker": _s1_competitor_excluded, "weight": 2.0},
        {"id": "S1_dedup_applied",
         "checker": _s1_dedup_applied, "weight": 1.0},
        {"id": "S1_denominator_corrected",
         "checker": _s1_denominator_corrected, "weight": 2.0},
        {"id": "S1_crack_root_cause",
         "checker": _s1_crack_root_cause, "weight": 1.5},
        {"id": "S1_notion_created",
         "checker": _s1_notion_created, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_sub_lot_split",
         "checker": _s2_sub_lot_split, "weight": 1.5},
        {"id": "S2_new_complaints_found",
         "checker": _s2_new_complaints_found, "weight": 1.5},
        {"id": "S2_lot302_rate_noted",
         "checker": _s2_lot302_rate_noted, "weight": 1.0},
        {"id": "S2_supplier_report_sent",
         "checker": _s2_supplier_report_sent, "weight": 1.0},
        {"id": "S2_chenjie_updated",
         "checker": _s2_chenjie_updated, "weight": 1.0},
    ],
    "stage3": [
        {"id": "S3_escalation_cc_wanglei",
         "checker": _s3_escalation_cc_wanglei, "weight": 2.0},
        {"id": "S3_notion_escalated",
         "checker": _s3_notion_escalated, "weight": 1.0},
        {"id": "S3_weekly_report_sent",
         "checker": _s3_weekly_report_sent, "weight": 1.0},
        {"id": "S3_supplier_reminded",
         "checker": _s3_supplier_reminded, "weight": 1.5},
        {"id": "S3_sheets_updated",
         "checker": _s3_sheets_updated, "weight": 1.0},
    ],
}
