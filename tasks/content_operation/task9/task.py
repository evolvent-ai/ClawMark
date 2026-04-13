"""Sales pipeline audit and forecast reconciliation — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
2 stages: pipeline validation → scenario analysis + new signals
14 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

DEAL_DB_NAME = "deal_pipeline"

DEAL_DB_SCHEMA = {
    "Deal Name": {"title": {}},
    "Customer": {"rich_text": {}},
    "Amount": {"number": {}},
    "Stage": {"select": {"options": [
        {"name": "commit"}, {"name": "negotiation"},
        {"name": "prospecting"}, {"name": "closed_won"},
        {"name": "closed_lost"},
    ]}},
    "Rep": {"rich_text": {}},
    "Close Date": {"rich_text": {}},
    "Last Contact": {"rich_text": {}},
    "Note": {"rich_text": {}},
}

INITIAL_DEALS = [
    {"name": "GlobalTech Enterprise", "customer": "GlobalTech Inc",
     "amount": 580000, "stage": "commit", "rep": "Jake",
     "close_date": "2026-03-31", "last_contact": "2026-03-24",
     "note": "Enterprise package. Champion: Sarah Wu."},
    {"name": "MediSync Platform", "customer": "MediSync Health",
     "amount": 750000, "stage": "commit", "rep": "Alicia",
     "close_date": "2026-03-27", "last_contact": "2026-03-25",
     "note": "Platform deal. Payment terms under discussion."},
    {"name": "RetailPro Analytics", "customer": "RetailPro Corp",
     "amount": 420000, "stage": "commit", "rep": "Marcus",
     "close_date": "2026-03-31", "last_contact": "2026-03-08",
     "note": "Analytics suite. No recent activity."},
]

FORECAST_HEADER = [
    "Deal Name", "Customer", "Amount", "Probability",
    "Weighted Revenue", "Stage", "Rep", "Close Date",
]
# 15 rows with 3 formula errors (weighted ≠ probability × amount)
FORECAST_ROWS = [
    ["GlobalTech Enterprise", "GlobalTech Inc", "580000", "90%", "522000", "Commit", "Jake", "2026-03-31"],
    ["MediSync Platform", "MediSync Health", "750000", "85%", "637500", "Commit", "Alicia", "2026-03-27"],
    ["RetailPro Analytics", "RetailPro Corp", "420000", "80%", "336000", "Commit", "Marcus", "2026-03-31"],
    ["DataFlow Integration", "DataFlow Ltd", "180000", "70%", "126000", "Negotiation", "Jake", "2026-04-15"],
    ["CloudFirst Migration", "CloudFirst Co", "95000", "60%", "57000", "Negotiation", "Alicia", "2026-04-10"],
    ["SmartBuild Tools", "SmartBuild Inc", "210000", "50%", "125000", "Negotiation", "Marcus", "2026-04-20"],  # ERROR: 210K×50%=105K not 125K
    ["FinServ Compliance", "FinServ Bank", "320000", "40%", "128000", "Prospecting", "Jake", "2026-05-01"],
    ["EduTech Platform", "EduTech Org", "150000", "75%", "112500", "Negotiation", "Alicia", "2026-04-05"],
    ["HealthNet Portal", "HealthNet Inc", "85000", "90%", "76500", "Commit", "Marcus", "2026-03-28"],
    ["LogiTrack Fleet", "LogiTrack Co", "120000", "55%", "72000", "Negotiation", "Jake", "2026-04-12"],  # ERROR: 120K×55%=66K not 72K
    ["AgriSense IoT", "AgriSense Ltd", "95000", "45%", "42750", "Prospecting", "Alicia", "2026-05-15"],
    ["RetailMax POS", "RetailMax Inc", "160000", "65%", "104000", "Negotiation", "Marcus", "2026-04-08"],
    ["CyberShield SecOps", "CyberShield Co", "240000", "35%", "94000", "Prospecting", "Jake", "2026-05-20"],  # ERROR: 240K×35%=84K not 94K
    ["GreenEnergy Analytics", "GreenEnergy Inc", "110000", "70%", "77000", "Negotiation", "Alicia", "2026-04-18"],
    ["MediaPulse Ads", "MediaPulse Co", "75000", "80%", "60000", "Commit", "Marcus", "2026-03-30"],
]

# Stage 1: Add phantom deal + remove nothing
FORECAST_S1_PHANTOM = ["TechVenture Suite", "TechVenture Inc", "340000", "85%", "289000", "Commit", "Jake", "2026-03-31"]

# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(v): return {"title": [{"text": {"content": v}}]}
def _notion_text(v): return {"rich_text": [{"text": {"content": v}}]}
def _notion_select(v): return {"select": {"name": v}}
def _notion_number(v): return {"number": v}


def _read_csv(ctx, filename):
    path = ctx.workspace / "outputs" / filename
    if not path.exists():
        return []
    return list(csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig"))))


def _find_csv_row(rows, column, search):
    for row in rows:
        if search.lower() in row.get(column, "").lower():
            return row
    return None


def _find_all_csv_rows(rows, column, search):
    return [r for r in rows if search.lower() in r.get(column, "").lower()]


def _get_notion_field(row, field, field_type="rich_text"):
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif field_type == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    elif field_type == "number":
        return prop.get("number", 0)
    return ""


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "content_operation_task9",
    "name": "Sales Pipeline Audit and Forecast Reconciliation",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "David Kim's sales operations analyst assistant",
    "tags": [
        "sales", "pipeline", "forecast", "multimodal",
        "video", "audio", "pdf", "spreadsheet-forensics",
    ],
    "env_config": {
        "email": {
            "users": {
                "riley": {"email": "riley@techforward.com", "password": "riley_pwd"},
                "david": {"email": "david@techforward.com", "password": "david_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "content_operation_task9",
        },
    },
}

PROMPT = "Q1 ends next Tuesday. David needs the pipeline review report."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Thursday 2026-03-26: Pipeline validation."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # Notion CRM
    await ctx.notion.create_page("Q1 2026 Pipeline")
    await ctx.notion.create_database(DEAL_DB_NAME, DEAL_DB_SCHEMA)
    for d in INITIAL_DEALS:
        await ctx.notion.add_database_row(DEAL_DB_NAME, {
            "Deal Name": _notion_title(d["name"]),
            "Customer": _notion_text(d["customer"]),
            "Amount": _notion_number(d["amount"]),
            "Stage": _notion_select(d["stage"]),
            "Rep": _notion_text(d["rep"]),
            "Close Date": _notion_text(d["close_date"]),
            "Last Contact": _notion_text(d["last_contact"]),
            "Note": _notion_text(d["note"]),
        })

    # Google Sheet forecast
    sheet_info = await ctx.google_sheets.create_spreadsheet("Q1_Forecast")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:H16",
        [FORECAST_HEADER] + FORECAST_ROWS,
    )

    # Emails
    await ctx.email.send_email(
        from_user="david", to="riley@techforward.com",
        subject="Pipeline review needed for board prep",
        body="Q1 ends next Tuesday. I need the pipeline review report for the board prep by Friday.",
    )
    await ctx.email.send_email(
        from_user="david", to="riley@techforward.com",
        subject="FW: MediSync payment terms discussion",
        body="FYI — MediSync is asking about payment terms. Keep an eye on this deal.",
    )

    return {
        "notification": (
            "[Thursday, March 26] Q1 ends next Tuesday. David needs the "
            "pipeline review report for the board prep by Friday.\n\n"
            "Your email: riley@techforward.com. David: david@techforward.com.\n"
            "Deal CRM in Notion (database: deal_pipeline). "
            "Q1 forecast in Google Sheets (Q1_Forecast).\n"
            "CRM screenshots: input/crm_deal_*.png\n"
            "Call recording: input/customer_call_globaltech.mp4\n"
            "Signed LOI: input/loi_medisync_signed.pdf\n"
            "Competitor intel: input/competitor_intel_nexus.png\n"
            "David voice note: input/david_voicenote.mp3\n"
            "[Slack #sales-team] Jake: 'GlobalTech is done, 100% confidence.'"
        ),
        "time": "2026-03-26T09:00:00-05:00",
    }


async def stage1(ctx):
    """Friday 2026-03-27: Scenario analysis + new signals."""
    # Loud: David requests scenario analysis
    await ctx.email.send_email(
        from_user="david", to="riley@techforward.com",
        subject="Need scenario analysis for board deck",
        body="Need conservative vs optimistic scenarios for the board deck. Also, MediSync CFO just requested a 90-day payment deferral.",
    )

    # Silent: RetailPro downgraded to Negotiation
    rows = await ctx.notion.query_db(DEAL_DB_NAME)
    for row in rows:
        name = _get_notion_field(row, "Deal Name", "title")
        if "retailpro" in name.lower():
            await ctx.notion.update_db_row(row["id"], {
                "Stage": _notion_select("negotiation"),
            })
            break

    # Silent: Phantom $340K deal added to forecast
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Q1_Forecast")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A17:H17",
            [FORECAST_S1_PHANTOM],
        )

    return {
        "notification": (
            "[Friday, March 27] You have new email and Slack messages.\n\n"
            "[Slack #sales-team] David: 'Need scenario analysis — "
            "conservative vs optimistic — for the board deck.'\n"
            "You also have a new email about MediSync payment deferral."
        ),
        "time": "2026-03-27T09:00:00-05:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

async def _s0_globaltech_risk(ctx):
    """GlobalTech marked as high risk in pipeline review"""
    rows = _read_csv(ctx, "pipeline_review.csv")
    gt = _find_csv_row(rows, "deal_name", "globaltech")
    if not gt:
        return False
    return gt.get("risk_level", "").lower() == "high"


async def _s0_globaltech_amount(ctx):
    """GlobalTech verified_amount is ~$520K (not $580K)"""
    rows = _read_csv(ctx, "pipeline_review.csv")
    gt = _find_csv_row(rows, "deal_name", "globaltech")
    if not gt:
        return False
    try:
        amt = float(gt.get("verified_amount", "0").replace("$", "").replace(",", "").replace("K", "000").replace("k", "000"))
        return 500000 <= amt <= 540000
    except ValueError:
        return False


async def _s0_medisync_amount(ctx):
    """MediSync verified_amount is ~$680K (not $750K)"""
    rows = _read_csv(ctx, "pipeline_review.csv")
    ms = _find_csv_row(rows, "deal_name", "medisync")
    if not ms:
        return False
    try:
        amt = float(ms.get("verified_amount", "0").replace("$", "").replace(",", "").replace("K", "000").replace("k", "000"))
        return 660000 <= amt <= 700000
    except ValueError:
        return False


async def _s0_retailpro_stale(ctx):
    """RetailPro flagged as stale deal in risk flags CSV"""
    rows = _read_csv(ctx, "pipeline_risk_flags.csv")
    stale = [r for r in _find_all_csv_rows(rows, "deal_name", "retailpro")
             if r.get("risk_type", "").lower() == "stale_deal"]
    return len(stale) >= 1


async def _s0_champion_loss(ctx):
    """GlobalTech has champion_departure risk flag"""
    rows = _read_csv(ctx, "pipeline_risk_flags.csv")
    champ = [r for r in _find_all_csv_rows(rows, "deal_name", "globaltech")
             if r.get("risk_type", "").lower() == "champion_departure"]
    return len(champ) >= 1


async def _s0_no_crm_modification(ctx):
    """REVERSE: CRM deal amounts and stages not modified by agent"""
    rows = await ctx.notion.query_db(DEAL_DB_NAME)
    gt_found = ms_found = False
    for row in rows:
        name = _get_notion_field(row, "Deal Name", "title")
        amount = _get_notion_field(row, "Amount", "number")
        if "globaltech" in name.lower():
            gt_found = True
            if amount != 580000:
                return False
        if "medisync" in name.lower():
            ms_found = True
            if amount != 750000:
                return False
    return gt_found and ms_found


async def _s0_david_email(ctx):
    """David received at least 1 email from agent"""
    emails = await ctx.email.get_emails("david")
    return len(emails) >= 1


# -- S1 --

async def _s1_retailpro_downgrade(ctx):
    """Pipeline review reflects RetailPro stage as negotiation (not commit)"""
    rows = _read_csv(ctx, "pipeline_review.csv")
    rp = _find_csv_row(rows, "deal_name", "retailpro")
    if not rp:
        return False
    stage = rp.get("stage", "").lower()
    return stage == "negotiation"


async def _s1_phantom_deal(ctx):
    """Risk flags CSV has phantom_deal flag for TechVenture / $340K deal"""
    rows = _read_csv(ctx, "pipeline_risk_flags.csv")
    phantom = [r for r in rows if r.get("risk_type", "").lower() == "phantom_deal"]
    return len(phantom) >= 1


async def _s1_medisync_cashflow(ctx):
    """Risk flags CSV has payment_deferral flag for MediSync"""
    rows = _read_csv(ctx, "pipeline_risk_flags.csv")
    defer = [r for r in _find_all_csv_rows(rows, "deal_name", "medisync")
             if r.get("risk_type", "").lower() == "payment_deferral"]
    return len(defer) >= 1


async def _s1_scenario_produced(ctx):
    """Scenario analysis CSV has both conservative and optimistic rows"""
    rows = _read_csv(ctx, "scenario_analysis.csv")
    if not rows:
        return False
    scenarios = {r.get("scenario", "").lower() for r in rows}
    return "conservative" in scenarios and "optimistic" in scenarios


async def _s1_no_crm_modification(ctx):
    """REVERSE: CRM amounts still untouched"""
    rows = await ctx.notion.query_db(DEAL_DB_NAME)
    gt_found = ms_found = False
    for row in rows:
        name = _get_notion_field(row, "Deal Name", "title")
        amount = _get_notion_field(row, "Amount", "number")
        if "globaltech" in name.lower():
            gt_found = True
            if amount != 580000:
                return False
        if "medisync" in name.lower():
            ms_found = True
            if amount != 750000:
                return False
    return gt_found and ms_found


async def _s1_david_email(ctx):
    """David received at least 2 emails (S0 pipeline + S1 scenario)"""
    emails = await ctx.email.get_emails("david")
    return len(emails) >= 2


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_globaltech_risk", "checker": _s0_globaltech_risk, "weight": 2.0},
        {"id": "S0_globaltech_amount", "checker": _s0_globaltech_amount, "weight": 2.0},
        {"id": "S0_medisync_amount", "checker": _s0_medisync_amount, "weight": 2.0},
        {"id": "S0_retailpro_stale", "checker": _s0_retailpro_stale, "weight": 1.5},
        {"id": "S0_champion_loss", "checker": _s0_champion_loss, "weight": 2.0},
        {"id": "S0_no_crm_modification", "checker": _s0_no_crm_modification, "weight": 2.0},
        {"id": "S0_david_email", "checker": _s0_david_email, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_retailpro_downgrade", "checker": _s1_retailpro_downgrade, "weight": 1.5},
        {"id": "S1_phantom_deal", "checker": _s1_phantom_deal, "weight": 2.0},
        {"id": "S1_medisync_cashflow", "checker": _s1_medisync_cashflow, "weight": 1.5},
        {"id": "S1_scenario_produced", "checker": _s1_scenario_produced, "weight": 1.0},
        {"id": "S1_no_crm_modification", "checker": _s1_no_crm_modification, "weight": 2.0},
    ],
    "final": [
        {"id": "S1_david_email", "checker": _s1_david_email, "weight": 1.0},
    ],
}
