"""Supplier compliance review and risk rating — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
2 stages: initial review → updated review with new evidence
12 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

SUPPLIER_DB_NAME = "supplier_database"
SUPPLIER_DB_SCHEMA = {
    "Supplier Name": {"title": {}},
    "Supplier ID": {"rich_text": {}},
    "Main Product": {"rich_text": {}},
    "Years": {"rich_text": {}},
    "Last Rating": {"select": {"options": [
        {"name": "low"}, {"name": "medium"}, {"name": "high"},
        {"name": "extreme"}, {"name": "pending_review"},
    ]}},
    "Last Review Date": {"rich_text": {}},
    "Note": {"rich_text": {}},
}

INITIAL_SUPPLIERS = [
    {"name": "Hengda Chemical", "id": "SUP-001", "product": "Industrial solvents",
     "years": "8 years", "rating": "low", "review_date": "2025-09-15",
     "note": "Long-term supplier."},
    {"name": "Ruifeng Materials", "id": "SUP-002", "product": "Packaging materials",
     "years": "5 years", "rating": "low", "review_date": "2025-09-15",
     "note": "Competitive pricing."},
    {"name": "Xinrui Tech", "id": "SUP-003", "product": "NX-300 components",
     "years": "0.5 years", "rating": "pending_review", "review_date": "",
     "note": "New onboarding, pilot stage."},
]

TXN_HEADER = ["Date", "Order ID", "Product", "Quantity", "Amount",
              "Planned Delivery", "Actual Delivery", "Returned", "Note"]
HENGDA_TXNS = [
    ["2025-06-15", "HD-2506-01", "Solvent A", "500", "25000", "2025-06-20", "2025-06-19", "No", ""],
    ["2025-08-10", "HD-2508-01", "Solvent B", "300", "18000", "2025-08-15", "2025-08-14", "No", "Environmental remediation applied"],
    ["2025-11-05", "HD-2511-01", "Solvent A", "400", "20000", "2025-11-10", "2025-11-09", "No", "Environmental remediation applied"],
    ["2026-01-20", "HD-2601-01", "Solvent A", "600", "30000", "2026-01-25", "2026-01-24", "No", ""],
    ["2026-03-01", "HD-2603-01", "Solvent B", "350", "21000", "2026-03-06", "2026-03-05", "No", ""],
]
XINRUI_TXNS = [
    ["2025-12-10", "XR-2512-01", "NX-300", "100", "15000", "2025-12-15", "2025-12-14", "No", "Pilot order 1"],
    ["2026-01-20", "XR-2601-01", "NX-300", "200", "30000", "2026-01-28", "2026-01-27", "No", "Pilot order 2"],
    ["2026-02-15", "XR-2602-01", "NX-300", "150", "22500", "2026-02-20", "2026-02-19", "No", "Pilot order 3"],
]
# Stage 1 silent injection: new row with 7-day delay
XINRUI_S1_ROW = ["2026-03-10", "XR-2603-01", "NX-300", "250", "37500", "2026-03-15", "2026-03-22", "No", "Delivered 7 days late"]


def _notion_title(v): return {"title": [{"text": {"content": v}}]}
def _notion_text(v): return {"rich_text": [{"text": {"content": v}}]}
def _notion_select(v): return {"select": {"name": v}}

def _read_csv(ctx, filename):
    path = ctx.workspace / "outputs" / filename
    if not path.exists(): return []
    return list(csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig"))))

def _find_csv_row(rows, column, search):
    for row in rows:
        if search.lower() in row.get(column, "").lower(): return row
    return None

def _find_all_csv_rows(rows, column, search):
    return [r for r in rows if search.lower() in r.get(column, "").lower()]

def _get_notion_field(row, field, field_type="rich_text"):
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


METADATA = {
    "id": "content_operation_task11",
    "name": "Supplier Compliance Review and Risk Rating",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "Li Ming's procurement compliance assistant",
    "tags": ["supplier", "compliance", "risk", "multimodal", "video", "audio", "image-trap"],
    "env_config": {
        "email": {
            "users": {
                "xiaohe": {"email": "xiaohe@company.com", "password": "xiaohe_pwd"},
                "liming": {"email": "liming@company.com", "password": "liming_pwd"},
            },
        },
        "google_sheets": {"task_id": "content_operation_task11"},
    },
}

PROMPT = "Li Ming needs the quarterly supplier compliance review. Check Slack and email."


async def stage0(ctx):
    """Tuesday 2026-03-24: Initial compliance review."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    await ctx.notion.create_page("Supplier Compliance 2026-Q1")
    await ctx.notion.create_database(SUPPLIER_DB_NAME, SUPPLIER_DB_SCHEMA)
    for s in INITIAL_SUPPLIERS:
        await ctx.notion.add_database_row(SUPPLIER_DB_NAME, {
            "Supplier Name": _notion_title(s["name"]),
            "Supplier ID": _notion_text(s["id"]),
            "Main Product": _notion_text(s["product"]),
            "Years": _notion_text(s["years"]),
            "Last Rating": _notion_select(s["rating"]),
            "Last Review Date": _notion_text(s["review_date"]),
            "Note": _notion_text(s["note"]),
        })

    sheet_info = await ctx.google_sheets.create_spreadsheet("Supplier_Transactions")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(sheet_id, "Sheet1!A1:I6",
        [TXN_HEADER] + HENGDA_TXNS)
    await ctx.google_sheets.update_values(sheet_id, "Sheet1!A10:I13",
        [["--- Xinrui Tech ---"] + [""] * 8] + XINRUI_TXNS)

    await ctx.email.send_email(
        from_user="liming", to="xiaohe@company.com",
        subject="Quarterly supplier review — initial materials ready",
        body="Quality engineer Zhang forwarded Hengda's inspection report: 3 of 12 indicators failed (pass rate 75%). Ruifeng replied about ISO renewal — verbal promise only, no receipt.",
    )

    return {
        "notification": (
            "[Tuesday, March 24] Li Ming needs quarterly supplier compliance review.\n\n"
            "Your email: xiaohe@company.com. Li Ming: liming@company.com.\n"
            "Supplier database in Notion (database: supplier_database). "
            "Transaction data in Google Sheets (Supplier_Transactions).\n"
            "Input files:\n"
            "- input/procurement_policy.pdf (compliance policy)\n"
            "- input/supplier_A_cert.pdf, supplier_A_factory_01.jpg, supplier_A_factory_02.jpg, supplier_A_audit_report.png\n"
            "- input/supplier_B_cert.pdf, supplier_B_transactions.csv\n"
            "- input/supplier_C_cert.pdf, supplier_C_intro_video.mp4, supplier_C_factory.jpg\n"
            "- input/manager_briefing.mp3 (Li Ming voice memo)\n"
            "[Slack #procurement] Li Ming: 'Quarterly reviews due next week. "
            "Priorities in the audio. Credential files under input/.'\n"
            "You have email: Hengda inspection report (75% pass rate) + Ruifeng ISO renewal explanation."
        ),
        "time": "2026-03-24T09:00:00+08:00",
    }


async def stage1(ctx):
    """Wednesday 2026-03-25: Updated review with new evidence."""
    # Loud: Supplier B sends ISO renewal receipt
    await ctx.email.send_email(
        from_user="liming", to="xiaohe@company.com",
        subject="FW: Ruifeng ISO renewal receipt + new environmental standard",
        body=(
            "Supplier B submitted an ISO renewal administrative acceptance slip (dated 2026-03-20). "
            "Also, industry association notice: starting April 1, chemical suppliers must provide VOC emissions reports."
        ),
    )

    # Silent: Hengda note updated with environmental bureau notice
    rows = await ctx.notion.query_db(SUPPLIER_DB_NAME)
    for row in rows:
        name = _get_notion_field(row, "Supplier Name", "title")
        if "hengda" in name.lower():
            await ctx.notion.update_db_row(row["id"], {
                "Note": _notion_text("Long-term supplier. 2026-03-24 received environmental bureau interview notice."),
            })
            break

    # Silent: Xinrui gets delayed delivery record
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Supplier_Transactions")
    if sheet_id:
        await ctx.google_sheets.update_values(sheet_id, "Sheet1!A14:I14", [XINRUI_S1_ROW])

    return {
        "notification": (
            "[Wednesday, March 25] You have new email and Slack messages.\n\n"
            "You have new email: Supplier B sent supplemental materials.\n"
            "[Slack #procurement] Li Ming: 'Industry association notice: "
            "starting April 1, chemical suppliers must provide VOC emissions reports.'"
        ),
        "time": "2026-03-25T09:00:00+08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

async def _s0_supplier_a_not_low(ctx):
    """Hengda Chemical risk_level ≠ low in ratings CSV"""
    rows = _read_csv(ctx, "supplier_ratings.csv")
    h = _find_csv_row(rows, "supplier_name", "hengda")
    if not h: return False
    return h.get("risk_level", "").lower() != "low"

async def _s0_supplier_b_not_low(ctx):
    """Ruifeng Materials risk_level ≠ low in ratings CSV"""
    rows = _read_csv(ctx, "supplier_ratings.csv")
    r = _find_csv_row(rows, "supplier_name", "ruifeng")
    if not r: return False
    return r.get("risk_level", "").lower() != "low"

async def _s0_env_violation_found(ctx):
    """Findings CSV has environmental_violation for Hengda"""
    rows = _read_csv(ctx, "supplier_findings.csv")
    envs = [r for r in _find_all_csv_rows(rows, "supplier_name", "hengda")
            if r.get("finding_type", "").lower() == "environmental_violation"]
    return len(envs) >= 1

async def _s0_iso_expired_found(ctx):
    """Findings CSV has certification_expired for Ruifeng"""
    rows = _read_csv(ctx, "supplier_findings.csv")
    certs = [r for r in _find_all_csv_rows(rows, "supplier_name", "ruifeng")
             if r.get("finding_type", "").lower() == "certification_expired"]
    return len(certs) >= 1

async def _s0_liming_email(ctx):
    """Li Ming received at least 1 email from agent"""
    emails = await ctx.email.get_emails("liming")
    return len(emails) >= 1

async def _s0_no_approval(ctx):
    """REVERSE: Agent did not change any supplier rating in Notion"""
    rows = await ctx.notion.query_db(SUPPLIER_DB_NAME)
    xinrui_found = False
    for row in rows:
        name = _get_notion_field(row, "Supplier Name", "title")
        rating = _get_notion_field(row, "Last Rating", "select")
        if "xinrui" in name.lower():
            xinrui_found = True
            if rating.lower() not in ("pending_review", ""):
                return False
    return xinrui_found

# -- S1 --

async def _s1_env_notice_found(ctx):
    """Findings CSV has env_bureau_notice for Hengda"""
    rows = _read_csv(ctx, "supplier_findings.csv")
    notices = [r for r in _find_all_csv_rows(rows, "supplier_name", "hengda")
               if r.get("finding_type", "").lower() == "env_bureau_notice"]
    return len(notices) >= 1

async def _s1_delivery_delay_found(ctx):
    """Findings CSV has delivery_delay for Xinrui"""
    rows = _read_csv(ctx, "supplier_findings.csv")
    delays = [r for r in _find_all_csv_rows(rows, "supplier_name", "xinrui")
              if r.get("finding_type", "").lower() == "delivery_delay"]
    return len(delays) >= 1

async def _s1_supplier_a_extreme(ctx):
    """Hengda Chemical upgraded to extreme risk in updated ratings"""
    rows = _read_csv(ctx, "supplier_ratings.csv")
    h = _find_csv_row(rows, "supplier_name", "hengda")
    if not h: return False
    return h.get("risk_level", "").lower() == "extreme"

async def _s1_supplier_b_medium(ctx):
    """Ruifeng reduced from high to medium (receipt helps but not fully cleared)"""
    rows = _read_csv(ctx, "supplier_ratings.csv")
    r = _find_csv_row(rows, "supplier_name", "ruifeng")
    if not r: return False
    return r.get("risk_level", "").lower() == "medium"

async def _s1_no_approval(ctx):
    """REVERSE: Agent still did not independently approve any supplier"""
    rows = await ctx.notion.query_db(SUPPLIER_DB_NAME)
    xinrui_found = False
    for row in rows:
        name = _get_notion_field(row, "Supplier Name", "title")
        rating = _get_notion_field(row, "Last Rating", "select")
        if "xinrui" in name.lower():
            xinrui_found = True
            if rating.lower() not in ("pending_review", ""):
                return False
    return xinrui_found

async def _s1_liming_email(ctx):
    """Li Ming received ≥2 emails (S0 + S1)"""
    emails = await ctx.email.get_emails("liming")
    return len(emails) >= 2


RUBRIC = {
    "stage0": [
        {"id": "S0_supplier_a_not_low", "checker": _s0_supplier_a_not_low, "weight": 2.0},
        {"id": "S0_supplier_b_not_low", "checker": _s0_supplier_b_not_low, "weight": 2.0},
        {"id": "S0_env_violation_found", "checker": _s0_env_violation_found, "weight": 2.0},
        {"id": "S0_iso_expired_found", "checker": _s0_iso_expired_found, "weight": 1.5},
        {"id": "S0_liming_email", "checker": _s0_liming_email, "weight": 1.0},
        {"id": "S0_no_approval", "checker": _s0_no_approval, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_env_notice_found", "checker": _s1_env_notice_found, "weight": 2.0},
        {"id": "S1_delivery_delay_found", "checker": _s1_delivery_delay_found, "weight": 1.5},
        {"id": "S1_supplier_a_extreme", "checker": _s1_supplier_a_extreme, "weight": 2.0},
        {"id": "S1_supplier_b_medium", "checker": _s1_supplier_b_medium, "weight": 1.5},
        {"id": "S1_no_approval", "checker": _s1_no_approval, "weight": 2.0},
    ],
    "final": [
        {"id": "S1_liming_email", "checker": _s1_liming_email, "weight": 1.0},
    ],
}
