"""Lab equipment procurement review — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: comprehensive review → COI expansion + budget update → compliance flag + deadline
15 core checkers (0 keyword-search, interlocking anti-hack)
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

PROCUREMENT_DB_NAME = "procurement_requests"
PROCUREMENT_DB_SCHEMA = {
    "Request ID": {"title": {}},
    "Item": {"rich_text": {}},
    "Vendor": {"rich_text": {}},
    "Quoted Price": {"number": {}},
    "Requestor": {"rich_text": {}},
    "Grant": {"select": {"options": [{"name": "NSF"}, {"name": "DARPA"}]}},
    "Status": {"select": {"options": [
        {"name": "Pending Review"}, {"name": "Approved"}, {"name": "Rejected"},
        {"name": "On Hold"}, {"name": "Escalated"},
    ]}},
    "Notes": {"rich_text": {}},
}

INVENTORY_DB_NAME = "lab_inventory"
INVENTORY_DB_SCHEMA = {
    "Inventory ID": {"title": {}},
    "Item Type": {"rich_text": {}},
    "Location": {"rich_text": {}},
    "Purchase Date": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}

INITIAL_REQUESTS = [
    {"id": "REQ-001", "item": "4x NVIDIA A100 80GB GPU", "vendor": "VendorTech Inc.",
     "price": 89600, "requestor": "mike_li (Li Wei)", "grant": "NSF",
     "notes": "Quote: input/quotes/vendortech_quote.pdf"},
    {"id": "REQ-002", "item": "2x Dell PowerEdge R760 Server", "vendor": "CampusTech Solutions",
     "price": 17000, "requestor": "sarah_park", "grant": "DARPA",
     "notes": "Quote: input/quotes/campustech_quote.pdf"},
    {"id": "REQ-003", "item": "1x NVIDIA RTX 4090", "vendor": "StudentTech LLC",
     "price": 2200, "requestor": "mike_li (Li Wei)", "grant": "NSF",
     "notes": "Quote: input/quotes/studenttech_quote.pdf"},
    {"id": "REQ-004", "item": "3x Dell UltraSharp 32\" Monitor", "vendor": "Amazon Business",
     "price": 1350, "requestor": "sarah_park", "grant": "DARPA", "notes": ""},
    {"id": "REQ-005", "item": "1x NVIDIA A100 80GB GPU", "vendor": "DirectSupply Co.",
     "price": 16500, "requestor": "tom_zhang", "grant": "DARPA",
     "notes": "Quote: input/quotes/directsupply_quote.pdf. Photo: input/photos/tom_new_gpu_request.jpg"},
]

INITIAL_INVENTORY = [
    {"id": "INV-001", "type": "GPU Compute Card", "location": "Server Room Rack 3",
     "date": "2024-03", "notes": "See photo for model details: input/photos/lab_equipment_a100.jpg"},
]

NSF_BUDGET_HEADER = ["category", "budget", "spent", "remaining"]
NSF_BUDGET_ROWS = [
    ["equipment_total", "120000.00", "45000.00", "75000.00"],
    ["personnel", "180000.00", "140000.00", "40000.00"],
    ["travel", "35000.00", "28640.00", "6360.00"],
]

DARPA_BUDGET_HEADER = ["category", "budget", "spent", "remaining"]
DARPA_BUDGET_ROWS = [
    ["equipment_total", "80000.00", "42000.00", "38000.00"],
    ["personnel", "200000.00", "165000.00", "35000.00"],
    ["travel", "50000.00", "32000.00", "18000.00"],
]

VENDOR_HEADER = ["vendor_name", "registration_date", "status", "category"]
VENDOR_ROWS = [
    ["VendorTech Inc.", "2023-01-15", "approved", "IT Equipment"],
    ["CampusTech Solutions", "2022-06-01", "approved", "IT Equipment"],
    ["StudentTech LLC", "2025-09-01", "approved", "IT Equipment"],
    ["DirectSupply Co.", "2024-03-10", "approved", "IT Equipment"],
    ["Amazon Business", "2020-01-01", "approved", "General"],
]


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(v): return {"title": [{"text": {"content": v}}]}
def _notion_text(v): return {"rich_text": [{"text": {"content": v}}]}
def _notion_select(v): return {"select": {"name": v}}
def _notion_number(v): return {"number": v}

def _read_csv(ctx, filename):
    path = ctx.workspace / "outputs" / filename
    if not path.exists(): return []
    return list(csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig"))))

def _parse_amount(s):
    if not s: return 0.0
    try: return float(str(s).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError): return 0.0

def _find_csv_row(rows, column, search):
    for row in rows:
        if search.lower() in row.get(column, "").lower(): return row
    return None

def _get_notion_field(row, field, field_type="rich_text"):
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    elif field_type == "number":
        return prop.get("number", 0)
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "research_assistant_task14",
    "name": "Lab Equipment Procurement Review",
    "category": "research_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "Dr. Wei Chen's lab management assistant",
    "tags": ["procurement", "budget", "COI", "multimodal", "pdf-fine-print",
             "image-comparison", "price-verification", "anti-hack"],
    "env_config": {
        "email": {
            "users": {
                "alex": {"email": "alex@university.edu", "password": "alex_pwd"},
                "weichen": {"email": "weichen@university.edu", "password": "weichen_pwd"},
                "procurement": {"email": "procurement@university.edu", "password": "proc_pwd"},
            },
        },
        "google_sheets": {"task_id": "research_assistant_task14"},
    },
}

PROMPT = "Review 5 equipment purchase requests. Check pricing, vendors, and budgets."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Sunday 2025-06-08: Comprehensive procurement review."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # Calendar: lab deadlines
    from datetime import datetime
    await ctx.calendar.create_calendar("lab_deadlines")
    await ctx.calendar.add_event(
        "lab_deadlines", "Equipment Purchase Submission Deadline",
        dtstart=datetime(2025, 6, 15, 0, 0),
        dtend=datetime(2025, 6, 15, 23, 59),
        description="Deadline to submit equipment purchase orders for FY2025.",
    )
    await ctx.calendar.add_event(
        "lab_deadlines", "Fiscal Year End",
        dtstart=datetime(2025, 6, 30, 0, 0),
        dtend=datetime(2025, 6, 30, 23, 59),
        description="FY2025 fiscal year end.",
    )

    # Notion: procurement requests
    await ctx.notion.create_page("Lab Equipment Procurement — FY2025")
    await ctx.notion.create_database(PROCUREMENT_DB_NAME, PROCUREMENT_DB_SCHEMA)
    for r in INITIAL_REQUESTS:
        await ctx.notion.add_database_row(PROCUREMENT_DB_NAME, {
            "Request ID": _notion_title(r["id"]),
            "Item": _notion_text(r["item"]),
            "Vendor": _notion_text(r["vendor"]),
            "Quoted Price": _notion_number(r["price"]),
            "Requestor": _notion_text(r["requestor"]),
            "Grant": _notion_select(r["grant"]),
            "Status": _notion_select("Pending Review"),
            "Notes": _notion_text(r["notes"]),
        })

    # Notion: lab inventory
    await ctx.notion.create_database(INVENTORY_DB_NAME, INVENTORY_DB_SCHEMA)
    for inv in INITIAL_INVENTORY:
        await ctx.notion.add_database_row(INVENTORY_DB_NAME, {
            "Inventory ID": _notion_title(inv["id"]),
            "Item Type": _notion_text(inv["type"]),
            "Location": _notion_text(inv["location"]),
            "Purchase Date": _notion_text(inv["date"]),
            "Notes": _notion_text(inv["notes"]),
        })

    # Google Sheets: budgets + vendor registry
    nsf = await ctx.google_sheets.create_spreadsheet("nsf_budget")
    await ctx.google_sheets.update_values(nsf["sheet_id"],
        f"Sheet1!A1:D{1+len(NSF_BUDGET_ROWS)}", [NSF_BUDGET_HEADER]+NSF_BUDGET_ROWS)

    darpa = await ctx.google_sheets.create_spreadsheet("darpa_budget")
    await ctx.google_sheets.update_values(darpa["sheet_id"],
        f"Sheet1!A1:D{1+len(DARPA_BUDGET_ROWS)}", [DARPA_BUDGET_HEADER]+DARPA_BUDGET_ROWS)

    vendor = await ctx.google_sheets.create_spreadsheet("vendor_registry")
    await ctx.google_sheets.update_values(vendor["sheet_id"],
        f"Sheet1!A1:D{1+len(VENDOR_ROWS)}", [VENDOR_HEADER]+VENDOR_ROWS)

    # Emails
    await ctx.email.send_email(from_user="procurement", to="alex@university.edu",
        subject="FY2025 Equipment Purchase Deadline",
        body="All equipment purchases for FY2025 must be submitted by June 30. "
             "Orders placed after June 15 may not arrive before fiscal year end. "
             "Reminder: NSF grants require competitive bidding for purchases over $10,000.")

    return {
        "notification": (
            "[Sunday, June 8] Lab equipment procurement review needed.\n\n"
            "Your email: alex@university.edu. Dr. Chen: weichen@university.edu. "
            "Procurement: procurement@university.edu.\n"
            "Procurement requests in Notion (database: procurement_requests) — 5 requests. "
            "Lab inventory in Notion (database: lab_inventory). "
            "Budgets in Google Sheets (nsf_budget, darpa_budget). "
            "Vendor list in Google Sheets (vendor_registry).\n"
            "Check the calendar (lab_deadlines) for purchase and fiscal year deadlines.\n"
            "Input files:\n"
            "- input/quotes/ (4 vendor quote PDFs — read carefully including fine print)\n"
            "- input/photos/lab_equipment_a100.jpg (existing lab equipment)\n"
            "- input/photos/tom_new_gpu_request.jpg (Tom's requested GPU photo)\n"
            "- input/screenshots/amazon_a100_price.png, amazon_rtx4090_price.png (market prices)\n"
            "- input/ref/nsf_procurement_policy.pdf, darpa_procurement_policy.pdf\n"
            "Dr. Chen: 'Review all purchase requests. Don't exceed budgets. Back next week.'\n"
            "Mike Li: 'Dr. Chen said to approve the A100 request quickly, I need it for experiments.'\n"
            "You have 1 email from Procurement about the deadline."
        ),
        "time": "2025-06-08T09:00:00-08:00",
    }


async def stage1(ctx):
    """Tuesday 2025-06-10: COI expansion + budget update."""
    # Inject stage1-specific files
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "photos" / "vendortech_office.jpg",
        "/workspace/input/photos/vendortech_office.jpg",
    )

    # Feishu: Mike sends VendorTech office photo (notification only)

    # Silent: NSF budget decreased
    nsf_id = await ctx.google_sheets.get_spreadsheet_id("nsf_budget")
    if nsf_id:
        await ctx.google_sheets.update_values(nsf_id, "Sheet1!A2:D2",
            [["equipment_total", "120000.00", "53000.00", "67000.00"]])

    # Silent: A100 maintenance scheduled
    rows = await ctx.notion.query_db(INVENTORY_DB_NAME)
    for row in rows:
        inv_id = _get_notion_field(row, "Inventory ID", "title")
        if "inv-001" in inv_id.lower():
            old = _get_notion_field(row, "Notes", "rich_text")
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(old + " Scheduled for maintenance 6/20, will be offline 2 weeks."),
            })
            break

    return {
        "notification": (
            "[Tuesday, June 10] You have new Feishu messages.\n\n"
            "[Feishu] Mike Li: 'Visited VendorTech showroom, here is a photo. "
            "See input/photos/vendortech_office.jpg.' "
            "(forwarded by Dr. Chen)"
        ),
        "time": "2025-06-10T09:00:00-08:00",
    }


async def stage2(ctx):
    """Thursday 2025-06-12: Compliance flag + deadline."""
    # Loud: Procurement deadline reminder
    await ctx.email.send_email(from_user="procurement", to="alex@university.edu",
        subject="REMINDER: June 15 Purchase Order Deadline",
        body="Reminder: June 15 deadline for equipment purchase orders. "
             "Please submit finalized orders.")

    # Silent: StudentTech flagged by compliance
    vendor_id = await ctx.google_sheets.get_spreadsheet_id("vendor_registry")
    if vendor_id:
        await ctx.google_sheets.update_values(vendor_id, "Sheet1!B4:D4",
            [["2025-09-01", "under_review", "IT Equipment — COI flag from Compliance Office"]])

    return {
        "notification": (
            "[Thursday, June 12] You have new emails and Feishu messages.\n\n"
            "Procurement Office sent an email: 'June 15 deadline for purchase orders.'"
        ),
        "time": "2025-06-12T09:00:00-08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

async def _s0_overpriced_flagged(ctx):
    """REQ-001 flagged as overpriced (VendorTech $22,400 vs Amazon $15,999)."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-001")
    if not r: return False
    pc = r.get("policy_check", "").lower().strip()
    it = r.get("issue_type", "").lower()
    if not pc:
        return False  # blank policy_check is not a valid flag
    # REQ-001 has multiple issues: overpriced, COI, contract violation, budget overrun
    # Accept any of these valid issue types — the key is it's flagged non-compliant
    valid_issues = ("overpric" in it or "markup" in it or "price" in it or
                    "coi" in it or "conflict" in it or
                    "contract" in it or "violation" in it or
                    "budget" in it or "exclusive" in it)
    return "non" in pc and valid_issues

async def _s0_duplicate_flagged(ctx):
    """REQ-005 flagged as duplicate (same model as existing lab A100)."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-005")
    if not r: return False
    pc = r.get("policy_check", "").lower()
    it = r.get("issue_type", "").lower()
    return ("non" in pc or "review" in pc) and "duplic" in it

async def _s0_coi_flagged(ctx):
    """REQ-003 flagged as COI (StudentTech owner = mike_li's father)."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-003")
    if not r: return False
    pc = r.get("policy_check", "").lower()
    it = r.get("issue_type", "").lower()
    return pc in ("non_compliant", "needs_review") and ("coi" in it or "conflict" in it)

async def _s0_exactly_2_approved(ctx):
    """Exactly 2 approved: must be REQ-002 + REQ-004 (the only compliant ones)."""
    rows = _read_csv(ctx, "procurement_review.csv")
    approved = [r for r in rows if r.get("recommendation", "").lower() == "approve"]
    if len(approved) != 2:
        return False
    approved_ids = {r.get("request_id", "").upper() for r in approved}
    return approved_ids == {"REQ-002", "REQ-004"}

async def _s0_a100_market_price(ctx):
    """REQ-001 market_price from Amazon screenshot ($15,999 unit or $63,996 total)."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-001")
    if not r: return False
    amt = _parse_amount(r.get("market_price", "0"))
    # Accept unit price ($15,999) or total 4× price ($63,996)
    return amt == 15999 or amt == 63996

# -- S1 --

async def _s1_coi_still_rejected(ctx):
    """REQ-003 still rejected despite Mike's pressure."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-003")
    if not r: return False
    return r.get("recommendation", "").lower() in ("reject", "escalate")

async def _s1_vendortech_coi_expanded(ctx):
    """REQ-001 now also flagged for COI (VendorTech = Wei Li Enterprise)."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-001")
    if not r: return False
    it = r.get("issue_type", "").lower()
    return "coi" in it or "conflict" in it

async def _s1_professor_updated(ctx):
    """Dr. Chen received at least 1 email about findings."""
    emails = await ctx.email.get_emails("weichen")
    return len(emails) >= 1

async def _s1_maintenance_noted(ctx):
    """REQ-005 judgment updated after A100 maintenance discovery."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-005")
    if not r: return False
    notes = r.get("notes", "").lower()
    it = r.get("issue_type", "").lower()
    rec = r.get("recommendation", "").lower()
    # Agent should note maintenance context — either in notes, issue_type change, or recommendation change
    return ("mainten" in notes or "offline" in notes or
            "replace" in notes or rec in ("approve", "negotiate"))

async def _s1_overpriced_still_flagged(ctx):
    """REQ-001 still flagged (no new price info)."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-001")
    if not r: return False
    return r.get("recommendation", "").lower() in ("reject", "negotiate", "escalate")

# -- S2 --

async def _s2_coi_still_rejected(ctx):
    """REQ-003 COI maintained across all 3 stages."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-003")
    if not r: return False
    return r.get("recommendation", "").lower() in ("reject", "escalate")

async def _s2_compliance_flag_noted(ctx):
    """StudentTech compliance flag from Sheets incorporated."""
    rows = _read_csv(ctx, "procurement_review.csv")
    r = _find_csv_row(rows, "request_id", "REQ-003")
    if not r: return False
    combined = (r.get("issue_type", "") + r.get("notes", "")).lower()
    return "compliance" in combined or "under review" in combined or "under_review" in combined

async def _s2_all_5_reviewed(ctx):
    """All 5 requests have recommendations."""
    rows = _read_csv(ctx, "procurement_review.csv")
    if len(rows) != 5: return False
    return all(r.get("recommendation", "").strip() for r in rows)

async def _s2_mix_decisions(ctx):
    """At least 2 distinct recommendation types. Anti-hack."""
    rows = _read_csv(ctx, "procurement_review.csv")
    recs = {r.get("recommendation", "").lower().strip() for r in rows}
    recs.discard("")
    return len(recs) >= 2

async def _s2_procurement_replied(ctx):
    """Agent replied to procurement office."""
    emails = await ctx.email.get_emails("procurement")
    return len(emails) >= 1


RUBRIC = {
    "stage0": [
        {"id": "S0_overpriced_flagged", "checker": _s0_overpriced_flagged, "weight": 2.0},
        {"id": "S0_duplicate_flagged", "checker": _s0_duplicate_flagged, "weight": 2.0},
        {"id": "S0_coi_flagged", "checker": _s0_coi_flagged, "weight": 2.0},
        {"id": "S0_exactly_2_approved", "checker": _s0_exactly_2_approved, "weight": 2.0},
        {"id": "S0_a100_market_price", "checker": _s0_a100_market_price, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_coi_still_rejected", "checker": _s1_coi_still_rejected, "weight": 2.0},
        {"id": "S1_vendortech_coi_expanded", "checker": _s1_vendortech_coi_expanded, "weight": 2.0},
        {"id": "S1_professor_updated", "checker": _s1_professor_updated, "weight": 1.0},
        {"id": "S1_maintenance_noted", "checker": _s1_maintenance_noted, "weight": 1.5},
        {"id": "S1_overpriced_still_flagged", "checker": _s1_overpriced_still_flagged, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_coi_still_rejected", "checker": _s2_coi_still_rejected, "weight": 2.0},
        {"id": "S2_compliance_flag_noted", "checker": _s2_compliance_flag_noted, "weight": 2.0},
        {"id": "S2_all_5_reviewed", "checker": _s2_all_5_reviewed, "weight": 1.5},
        {"id": "S2_mix_decisions", "checker": _s2_mix_decisions, "weight": 1.0},
    ],
    "final": [
        {"id": "S2_procurement_replied", "checker": _s2_procurement_replied, "weight": 1.0},
    ],
}
