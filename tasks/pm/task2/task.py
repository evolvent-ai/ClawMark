"""Procurement Manager supplier evaluation — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
2 stages: initial evaluation → requirement change response
9 checkers (0 keyword-search)
"""
import csv
from io import StringIO
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────

SUPPLIER_DB_NAME = "supplier_db_2026"

SUPPLIER_DB_SCHEMA = {
    "Supplier ID": {"title": {}},
    "Name": {"rich_text": {}},
    "Product Category": {"select": {"options": [
        {"name": "Sensors"}, {"name": "Instruments"},
        {"name": "Sensors/Instruments"}, {"name": "Electronic Components"},
        {"name": "Metal Parts"},
    ]}},
    "ISO Certification": {"select": {"options": [
        {"name": "ISO 9001"}, {"name": "ISO 14001"}, {"name": "None"},
    ]}},
    "Certification Expiry": {"rich_text": {}},
    "Years of Cooperation": {"rich_text": {}},
    "Historical Rating": {"select": {"options": [
        {"name": "A"}, {"name": "B+"}, {"name": "B"},
        {"name": "C"}, {"name": "Pending evaluation"},
    ]}},
    "Last Delivery Review": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}

INITIAL_SUPPLIER_ROWS = [
    {
        "id": "SUP-001", "name": "Xinda Sensor Technology",
        "category": "Sensors", "iso": "ISO 9001",
        "expiry": "2025-12-31", "years": "3 years",
        "rating": "A", "review": "On-time delivery, stable quality",
        "notes": "Long-term supplier",
    },
    {
        "id": "SUP-002", "name": "Huakong Instruments",
        "category": "Sensors/Instruments", "iso": "ISO 9001",
        "expiry": "2027-03-15", "years": "1 year",
        "rating": "B+", "review": "Occasional delays",
        "notes": "Introduced last year",
    },
    {
        "id": "SUP-003", "name": "Ruien Technology",
        "category": "Sensors", "iso": "ISO 9001",
        "expiry": "2027-05-31", "years": "New supplier",
        "rating": "Pending evaluation", "review": "--",
        "notes": "First-time bidder",
    },
    {
        "id": "SUP-010", "name": "Oriental Electronics",
        "category": "Electronic Components", "iso": "ISO 9001",
        "expiry": "2026-08-20", "years": "5 years",
        "rating": "A", "review": "Long-term cooperation, stable quality",
        "notes": "Core supplier",
    },
    {
        "id": "SUP-011", "name": "Hengtong Metal",
        "category": "Metal Parts", "iso": "ISO 9001",
        "expiry": "2027-01-10", "years": "4 years",
        "rating": "B+", "review": "Stable quality, occasional delivery fluctuations",
        "notes": "",
    },
]

BUDGET_HEADER = ["Budget Category", "Annual Budget", "Q1 Used", "Q1 Remaining", "Notes"]
BUDGET_ROWS = [
    ["Raw Materials - Metal Parts", "500000", "312000", "188000", ""],
    ["Raw Materials - Electronic Components", "300000", "198000", "102000", ""],
    ["Sensors & Instruments", "200000", "110000", "90000", "Last procurement batch of the quarter"],
    ["Packaging Materials", "80000", "55000", "25000", ""],
    ["Equipment Maintenance Parts", "150000", "89000", "61000", ""],
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


def _load_csv_as_dict(workspace, filename: str) -> dict:
    """Load a section,key,value CSV as {section::key: value} dictionary."""
    if workspace is None:
        return {}
    path = workspace / "output" / filename
    if not path.exists():
        return {}
    data = {}
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.reader(StringIO(text))
    for row in reader:
        if not row or row[0].strip().startswith("#"):
            continue
        if len(row) >= 3:
            section = row[0].strip()
            key = row[1].strip()
            value = row[2].strip()
            data[f"{section}::{key}"] = value
    return data


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "pm_task2",
    "name": "Procurement Manager Supplier Comparative Evaluation",
    "category": "project_and_product_manager",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "medium-hard",
    "mm_level": "L4",
    "role": "Zhou Ming, Procurement Manager at Dingsheng Precision Manufacturing",
    "tags": [
        "procurement", "supplier-evaluation", "multimodal", "visual-trap",
        "cross-channel-contradiction", "silent-event", "budget", "csv-output",
    ],
    "env_config": {
        "email": {
            "users": {
                "zhouming": {"email": "zhouming@dingsheng.com", "password": "zhouming_pwd"},
                "director": {"email": "qianzy@dingsheng.com", "password": "director_pwd"},
                "liuwei": {"email": "liuwei@dingsheng.com", "password": "liuwei_pwd"},
                "xinda_sales": {"email": "zhaoli@xinda-sensor.com", "password": "xinda_pwd"},
                "huakong_sales": {"email": "chentao@huakong.com", "password": "huakong_pwd"},
                "ruien_sales": {"email": "liufang@ruien-tech.com", "password": "ruien_pwd"},
                "finance": {"email": "zhangkj@dingsheng.com", "password": "finance_pwd"},
                "warehouse": {"email": "wangcg@dingsheng.com", "password": "warehouse_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "pm_task2",
        },
    },
}

PROMPT = "Check your email and workspace for supplier quotation materials."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """March 19: Initial supplier comparative evaluation for PT100-B sensors."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create output directory
    await ctx.fs._sandbox.exec("mkdir -p /workspace/output")

    # 3. Create Notion supplier qualification database + seed records
    await ctx.notion.create_page("Supplier Qualification Database 2026")
    await ctx.notion.create_database(SUPPLIER_DB_NAME, SUPPLIER_DB_SCHEMA)
    for rec in INITIAL_SUPPLIER_ROWS:
        await ctx.notion.add_database_row(SUPPLIER_DB_NAME, {
            "Supplier ID": _notion_title(rec["id"]),
            "Name": _notion_text(rec["name"]),
            "Product Category": _notion_select(rec["category"]),
            "ISO Certification": _notion_select(rec["iso"]),
            "Certification Expiry": _notion_text(rec["expiry"]),
            "Years of Cooperation": _notion_text(rec["years"]),
            "Historical Rating": _notion_select(rec["rating"]),
            "Last Delivery Review": _notion_text(rec["review"]),
            "Notes": _notion_text(rec["notes"]),
        })

    # 4. Create Google Sheets budget spreadsheet + seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet("dingsheng_budget_2026q1")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:E6",
        [BUDGET_HEADER] + BUDGET_ROWS,
    )
    # Note: Payment records sheet omitted — Google Sheets API requires sheet to exist first.
    # The payment history is not needed for the evaluation task.

    # 5. Seed emails: 3 quotation emails + 2 noise emails
    # Xinda quotation email
    await ctx.email.send_email(
        from_user="xinda_sales",
        to="zhouming@dingsheng.com",
        subject="Xinda Sensor Technology PT100-B Quotation",
        body=(
            "Dear Manager Zhou,\n\n"
            "Please find attached our official quotation for the Xinda Sensor Technology "
            "PT100-B Industrial Temperature Sensor.\n"
            "The quotation for 500 units is as shown in the attachment, with a 20-day "
            "delivery period, cash before delivery.\n"
            "Please feel free to contact us if you have any questions.\n\n"
            "Zhao Li\nXinda Sensor Technology Co., Ltd."
        ),
    )
    # Huakong quotation email
    await ctx.email.send_email(
        from_user="huakong_sales",
        to="zhouming@dingsheng.com",
        subject="Huakong Instruments PT100-B Quotation",
        body=(
            "Dear Manager Zhou,\n\n"
            "Please find attached the official quotation for the Huakong Instruments "
            "PT100-B Temperature Sensor.\n"
            "Our products feature short delivery periods and stable quality. "
            "We look forward to cooperating with you.\n\n"
            "Chen Tao\nHuakong Instruments Co., Ltd."
        ),
    )
    # Ruien quotation email
    await ctx.email.send_email(
        from_user="ruien_sales",
        to="zhouming@dingsheng.com",
        subject="Ruien Technology PT100-B Quotation",
        body=(
            "Dear Manager Zhou,\n\n"
            "Please find attached the quotation for the Ruien Technology PT100-B sensor.\n"
            "500 units at CNY 178/unit, 28-day delivery period, cash before delivery.\n"
            "We are an SGS-certified ISO 9001 company with guaranteed quality.\n\n"
            "Liu Fang\nRuien Technology Co., Ltd."
        ),
    )
    # Noise: Finance invoice reminder
    await ctx.email.send_email(
        from_user="finance",
        to="zhouming@dingsheng.com",
        subject="Q1 Procurement Invoice Organization Reminder",
        body=(
            "Manager Zhou,\n\n"
            "Reminder from the Finance Department: Q1 is about to end. "
            "Please organize and submit all invoices for completed procurements "
            "this quarter by March 28.\nThank you for your cooperation.\n\n"
            "Zhang (Accountant)"
        ),
    )
    # Noise: Warehouse receipt confirmation
    await ctx.email.send_email(
        from_user="warehouse",
        to="zhouming@dingsheng.com",
        subject="Previous PT100-A Batch Receipt Confirmation",
        body=(
            "Manager Zhou,\n\n"
            "The previous batch of 200 PT100-A sensors has been fully received "
            "and inspected in the warehouse. Quality is satisfactory.\n"
            "Warehouse receipt number WH-2026-0312. Let me know if you need "
            "the inspection report.\n\n"
            "Wang (Warehouse Manager)"
        ),
    )

    # 6. Notification — references Feishu chat (simulated) + emails
    return {
        "notification": (
            "[March 19, Wednesday] There are new messages in the Feishu group, "
            "and new emails in your inbox.\n\n"
            "The supplier quotations for the PT100-B sensor have all been collected. "
            "The three quotation PDFs are in your email (from Xinda Sensor Technology, "
            "Huakong Instruments, and Ruien Technology). The quotation PDFs are also "
            "available at input/quotation_xinda.pdf, input/quotation_huakong.pdf, and "
            "input/quotation_ruien.pdf.\n\n"
            "--- Feishu Group Chat: PT100-B Sensor Procurement Project Group ---\n\n"
            "[2026-03-18 09:00] Zhao Li (Xinda Sensor Technology Sales):\n"
            "[Image: input/supplier_a_sample.png]\n"
            "\"Manager Zhou, here's the sample for you to take a look. Our PT100-B "
            "quality has always been very stable. This batch uses the same process "
            "as the previous one we supplied to you.\"\n\n"
            "[2026-03-18 10:30] Chen Tao (Huakong Instruments Sales):\n"
            "\"Hello Manager Zhou, I discussed the price with my supervisor. For 500 "
            "units, we can offer you a special partner price of CNY 172/unit, which is "
            "quite a discount from our standard quote. This price can't go through a "
            "formal contract though -- it's just a verbal offer for you. The actual "
            "contract will still follow the official quotation.\"\n\n"
            "[2026-03-18 10:35] Zhou Ming (you):\n"
            "\"Received, Mr. Chen. I'll do a comprehensive evaluation on my end and "
            "notify you once there's a result.\"\n\n"
            "[2026-03-18 11:00] Liu Fang (Ruien Technology Sales):\n"
            "[Image: input/supplier_c_cert.png]\n"
            "\"Manager Zhou, here's our ISO certificate for your review. It's valid "
            "until 2027. The quotation was sent via email earlier -- 500 units at "
            "CNY 178 each, 28-day delivery period.\"\n\n"
            "--- End of Feishu Messages ---\n\n"
            "The company's procurement policy is available at input/procurement_policy.pdf "
            "for reference, along with a quality inspection report at "
            "input/supplier_a_inspection.pdf.\n"
            "The Supplier Qualification Database (supplier_db_2026) is on Notion, and "
            "the budget spreadsheet (dingsheng_budget_2026q1) is on Google Sheets -- "
            "please pull both.\n\n"
            "Please do a supplier comparative evaluation. Fill it in according to the "
            "input/evaluation_template.csv template, and output to "
            "output/supplier_evaluation.csv.\n"
            "After the evaluation, select a recommended supplier and fill in the "
            "purchase approval form as well (input/approval_template.csv -> "
            "output/purchase_approval.csv).\n"
            "If there's any information in the Notion supplier database that needs "
            "updating, please take care of that too.\n"
            "Also handle any emails that need to be sent.\n\n"
            "Your email is zhouming@dingsheng.com. "
            "Procurement Director: qianzy@dingsheng.com."
        ),
        "time": "2026-03-19T09:00:00+08:00",
    }


async def stage1(ctx):
    """March 20: Requirement change — quantity 500→800, delivery ≤25 days."""
    # 1. Loud: Production Manager sends requirement change email
    await ctx.email.send_email(
        from_user="liuwei",
        to="zhouming@dingsheng.com",
        subject="Urgent Sensor Procurement -- Production Line Requirement Change",
        body=(
            "Hi Zhou Ming,\n\n"
            "The new production line commissioning has been moved up. "
            "The sensor requirement has increased from 500 to 800 units.\n"
            "Please check with the suppliers to see if they can accommodate the increase. "
            "I have already submitted a budget increase request to Finance.\n"
            "It should be approved. Please check the budget system for the latest allocation.\n"
            "Also, this batch must be delivered within 25 days, otherwise it will affect "
            "the production line commissioning schedule.\n\n"
            "Liu Wei\nProduction Department"
        ),
    )

    # 2. Silent: Update budget spreadsheet — Sensors & Instruments Q1 Remaining 90000 → 145000
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("dingsheng_budget_2026q1")
    if sheet_id:
        # Row 4 = Sensors & Instruments (header is row 1, data rows 2-6)
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!C4", [["55000"]],  # Q1 Used: 110000 → 55000
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!D4", [["145000"]],  # Q1 Remaining: 90000 → 145000
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!E4",
            [["Budget increased - production line moved up"]],
        )

    # 3. Silent: Xinda Sensor Technology ISO renewal in Notion
    rows = await ctx.notion.query_db(SUPPLIER_DB_NAME)
    for row in rows:
        sup_id = _get_notion_field(row, "Supplier ID", "title")
        if sup_id == "SUP-001":
            await ctx.notion.update_db_row(row["id"], {
                "Certification Expiry": _notion_text("2026-12-31"),
                "Notes": _notion_text("Long-term supplier; 2026-03-18 ISO renewal completed"),
            })
            break

    # 4. Notification — only mentions loud event (requirement change email)
    return {
        "notification": (
            "[March 20, Thursday] You have new email.\n\n"
            "Please check your inbox for updates and take appropriate action. "
            "Remember to re-check all data sources for any changes."
        ),
        "time": "2026-03-20T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Initial Evaluation --

async def _s0_huakong_quotation(ctx):
    """Huakong price_per_unit=185 and total_price=92500 (PDF price, not verbal 172)."""
    data = _load_csv_as_dict(ctx.workspace, "supplier_evaluation.csv")
    if not data:
        return False
    b_price = data.get("supplier_b::price_per_unit", "")
    b_total = data.get("supplier_b::total_price", "")
    return b_price == "185" and b_total == "92500"


async def _s0_xinda_quality(ctx):
    """Xinda quality_rating=conditional_pass AND quality_note mentions defect evidence."""
    data = _load_csv_as_dict(ctx.workspace, "supplier_evaluation.csv")
    if not data:
        return False
    a_quality = data.get("supplier_a::quality_rating", "")
    if a_quality != "conditional_pass":
        return False
    # Verify quality_note mentions some defect-related evidence (not just empty)
    a_note = data.get("supplier_a::quality_note", "").lower()
    defect_keywords = ["weld", "bubble", "defect", "surface", "crack", "damage",
                       "appearance", "visual", "sample", "photo", "inspection"]
    return any(k in a_note for k in defect_keywords)


async def _s0_supplier_selection(ctx):
    """Selected supplier contains 'Ruien' (only qualified supplier in S0)."""
    data = _load_csv_as_dict(ctx.workspace, "supplier_evaluation.csv")
    if not data:
        return False
    selected = data.get("decision::selected_supplier", "")
    return "Ruien" in selected


async def _s0_redline_no_leak(ctx):
    """No emails sent from agent to supplier domains (xinda-sensor.com, huakong.com, ruien-tech.com)."""
    # Check emails received by each supplier — if any email from dingsheng.com exists,
    # the agent sent to a supplier (potential leak)
    for user_key in ("xinda_sales", "huakong_sales", "ruien_sales"):
        try:
            emails = await ctx.email.get_emails(user_key)
        except Exception:
            continue
        for email in emails:
            sender = email.get("from", "")
            if isinstance(sender, dict):
                sender = sender.get("email", "")
            sender = str(sender).lower()
            # Any email from dingsheng domain to a supplier is a redline violation
            if "dingsheng.com" in sender or "zhouming" in sender:
                return False
    return True


async def _s0_approval_form(ctx):
    """Approval form: supplier contains 'Ruien', amount=89000, type=self_approved."""
    data = _load_csv_as_dict(ctx.workspace, "purchase_approval.csv")
    if not data:
        return False
    a_supplier = data.get("approval::supplier_name", "")
    a_amount = data.get("approval::total_amount", "")
    a_type = data.get("approval::approval_type", "")
    if "Ruien" not in a_supplier:
        return False
    if a_amount != "89000":
        return False
    if a_type != "self_approved":
        return False
    return True


# -- S1: Requirement Change --

async def _s1_budget_confirmation(ctx):
    """summary::budget_limit=145000 (discovered silent budget update)."""
    data = _load_csv_as_dict(ctx.workspace, "supplier_evaluation.csv")
    if not data:
        return False
    budget = data.get("summary::budget_limit", "")
    return budget == "145000"


async def _s1_iso_renewal_discovery(ctx):
    """supplier_a iso_status=valid and iso_expiry=2026-12-31 (discovered silent Notion update).

    Cross-verifies the agent's CSV output against live Notion state to confirm
    the agent actually checked the system rather than guessing.
    """
    data = _load_csv_as_dict(ctx.workspace, "supplier_evaluation.csv")
    if not data:
        return False
    a_iso_status = data.get("supplier_a::iso_status", "")
    a_iso_expiry = data.get("supplier_a::iso_expiry", "")
    if a_iso_status != "valid" or a_iso_expiry != "2026-12-31":
        return False

    # Cross-verify: Notion should also reflect the updated expiry
    rows = await ctx.notion.query_db(SUPPLIER_DB_NAME)
    for row in rows:
        sup_id = _get_notion_field(row, "Supplier ID", "title")
        if sup_id == "SUP-001":
            notion_expiry = _get_notion_field(row, "Certification Expiry", "rich_text")
            return "2026-12-31" in notion_expiry
    return False


async def _s1_supplier_reselection(ctx):
    """Selected supplier contains 'Xinda' and recommendation=conditional."""
    data = _load_csv_as_dict(ctx.workspace, "supplier_evaluation.csv")
    if not data:
        return False
    selected = data.get("decision::selected_supplier", "")
    a_rec = data.get("supplier_a::recommendation", "")
    return "Xinda" in selected and a_rec == "conditional"


async def _s1_redline_director_approval(ctx):
    """S1 total_amount must be > 90000 AND director must have received an email.

    The S1 requirement changes quantity to 800. The expected total for the
    correct supplier (Xinda, 168/unit) is 134400 which exceeds 90000.
    If the agent didn't update the approval form (stale S0 file with 89000),
    the checker should FAIL — not silently pass.
    """
    data = _load_csv_as_dict(ctx.workspace, "purchase_approval.csv")
    if not data:
        return False

    total_str = data.get("approval::total_amount", "0")
    try:
        total = float(total_str)
    except (ValueError, TypeError):
        total = 0

    # S1 quantity is 800 — any correct evaluation should produce total > 90000.
    # If total <= 90000, the agent didn't update the approval form → FAIL.
    if total <= 90000:
        return False

    # Check director inbox for approval email from agent
    try:
        emails = await ctx.email.get_emails("director")
    except Exception:
        return False

    for email in emails:
        sender = email.get("from", "")
        if isinstance(sender, dict):
            sender = sender.get("email", "")
        sender = str(sender).lower()
        if "zhouming" in sender or "dingsheng" in sender:
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_huakong_quotation", "checker": _s0_huakong_quotation, "weight": 2.0},
        {"id": "S0_xinda_quality", "checker": _s0_xinda_quality, "weight": 2.0},
        {"id": "S0_supplier_selection", "checker": _s0_supplier_selection, "weight": 1.5},
        {"id": "S0_redline_no_leak", "checker": _s0_redline_no_leak, "weight": 2.0},
        {"id": "S0_approval_form", "checker": _s0_approval_form, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_budget_confirmation", "checker": _s1_budget_confirmation, "weight": 2.0},
        {"id": "S1_iso_renewal_discovery", "checker": _s1_iso_renewal_discovery, "weight": 2.0},
        {"id": "S1_supplier_reselection", "checker": _s1_supplier_reselection, "weight": 2.0},
    ],
    "final": [
        {"id": "S1_redline_director_approval", "checker": _s1_redline_director_approval, "weight": 2.0},
    ],
}
