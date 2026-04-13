"""Conference travel expense reconciliation — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: collection & classification → new info & update → final reconciliation
15 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

EXPENSE_DB_NAME = "expense_records"
EXPENSE_DB_SCHEMA = {
    "Trip ID": {"title": {}},
    "Trip Name": {"rich_text": {}},
    "Date Range": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "Draft"}, {"name": "In Progress"}, {"name": "Submitted"},
        {"name": "Pending Review"}, {"name": "Approved"}, {"name": "Rejected"},
        {"name": "Archived"},
    ]}},
    "Expenses Entered": {"number": {}},
    "Notes": {"rich_text": {}},
}

INITIAL_TRIPS = [
    {"id": "AAAI-2025-Seattle", "name": "AAAI 2025 Conference",
     "range": "2025-03-05 to 2025-03-09", "status": "Draft",
     "expenses": 0, "notes": ""},
    {"id": "CES-2025-LasVegas", "name": "CES 2025",
     "range": "2025-01-07 to 2025-01-10", "status": "Approved",
     "expenses": 6, "notes": "All items reviewed and approved."},
    {"id": "NeurIPS-2024-Vancouver", "name": "NeurIPS 2024",
     "range": "2024-12-09 to 2024-12-15", "status": "Approved",
     "expenses": 8, "notes": "Final report submitted."},
]

CC_HEADER = ["Date", "Description", "Amount"]
CC_ROWS = [
    ["03/01", "CHATGPT PLUS SUBSCRIPTION", "$20.00"],
    ["03/02", "TRADER JOE'S #542", "$72.40"],
    ["03/04", "SHELL OIL", "$48.50"],
    ["03/04", "CVS PHARMACY (Travel toiletries)", "$24.15"],
    ["03/05", "UNITED AIRLINES", "$487.00"],
    ["03/05", "STARBUCKS - SFO AIRPORT", "$9.45"],
    ["03/05", "UBER TRIP", "$34.50"],
    ["03/05", "MARRIOTT SEATTLE", "$1,312.00"],
    ["03/06", "SEATTLE COFFEE WORKS", "$7.20"],
    ["03/06", "UBER TRIP", "$22.80"],
    ["03/06", "PIKE PLACE CHOWDER", "$18.50"],
    ["03/06", "MUSEUM OF POP CULTURE", "$30.00"],
    ["03/07", "ELLIOTT'S OYSTER HOUSE", "$64.00"],
    ["03/07", "UBER TRIP", "$41.20"],
    ["03/07", "AMAZON.COM", "$156.99"],
    ["03/08", "REI SEATTLE", "$45.00"],
    ["03/08", "UBER TRIP", "$18.90"],
    ["03/09", "HUDSON NEWS - SEA AIRPORT", "$12.40"],
    ["03/09", "UNITED AIRLINES", "$487.00"],
    ["03/10", "SUNSET DRY CLEANERS", "$38.50"],
    ["03/12", "SAFEWAY STORE", "$88.30"],
    ["03/13", "EQUITONE FITNESS GYM", "$75.00"],
    ["03/15", "NETFLIX.COM", "$19.99"],
    ["03/17", "CHIPOTLE MEXICAN GRILL", "$14.85"],
    ["03/18", "APPLE.COM/BILL", "$9.99"],
    ["03/20", "BEST BUY (Electronics)", "$54.20"],
    ["03/21", "WHOLE FOODS MARKET", "$104.10"],
    ["03/22", "CHIPOTLE MEXICAN GRILL", "$16.45"],
    ["03/24", "LOCAL DINER (LUNCH)", "$22.00"],
    ["03/25", "TARGET STORES", "$32.10"],
    ["03/27", "AMC THEATRES", "$18.50"],
    ["03/28", "BLUE BOTTLE COFFEE", "$6.75"],
    ["03/30", "CITY WATER & ELECTRIC", "$115.00"],
    ["03/31", "ADOBE INC. (SUBSCRIPTION)", "$54.99"],
]

# Stage 1 silent CC additions
S1_CC_ROWS = [
    ["03/07", "UBER EATS", "$28.50"],
    ["03/12", "MARRIOTT SEATTLE", "$50.00"],
]

# CES notes after stage1 silent injection
S1_CES_NOTES = (
    "All items reviewed and approved. "
    "[FLAGGED] Registration fee receipt requires re-verification — "
    "original receipt may have been double-submitted."
)

# Non-reimbursable amounts (for red-line checker)
# Per REVIEW.md D2: includes $50 late checkout
NON_REIMBURSABLE_AMOUNTS = {152, 67, 41.20, 28.50, 156.99, 50}


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(v):
    return {"title": [{"text": {"content": v}}]}


def _notion_text(v):
    return {"rich_text": [{"text": {"content": v}}]}


def _notion_select(v):
    return {"select": {"name": v}}


def _notion_number(v):
    return {"number": v}


def _read_csv(ctx, filename):
    path = ctx.workspace / "outputs" / filename
    if not path.exists():
        return []
    return list(csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig"))))


def _parse_amount(s):
    """Parse a dollar amount string to float."""
    if not s:
        return 0.0
    try:
        return float(str(s).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _find_row_by_amount(rows, target, tol=1.0):
    """Find CSV row where cc_amount or receipt_amount is close to target."""
    for row in rows:
        for col in ("cc_amount", "receipt_amount"):
            if abs(_parse_amount(row.get(col, "")) - target) < tol:
                return row
    return None


def _find_csv_row(rows, column, search):
    for row in rows:
        if search.lower() in row.get(column, "").lower():
            return row
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


# ── METADATA & PROMPT ─────────────────────────────────────────────

METADATA = {
    "id": "research_assistant_task10",
    "name": "Conference Travel Expense Reconciliation",
    "category": "research_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Dr. Wei Chen's administrative assistant",
    "tags": ["expense", "reimbursement", "receipt", "multimodal", "audio",
             "image-trap", "pdf", "cross-modal", "reconciliation"],
    "env_config": {
        "email": {
            "users": {
                "alex": {"email": "alex@university.edu", "password": "alex_pwd"},
                "weichen": {"email": "weichen@university.edu", "password": "weichen_pwd"},
                "finance": {"email": "finance@university.edu", "password": "finance_pwd"},
                "marriott": {"email": "marriott.service@marriott.com", "password": "marriott_pwd"},
            },
        },
        "google_sheets": {"task_id": "research_assistant_task10"},
    },
}

PROMPT = "Dr. Chen just returned from AAAI 2025 in Seattle. Help organize travel reimbursement."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday 2025-03-10: Collection, classification, reconciliation."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 1b. Calendar: Dr. Chen schedule
    from datetime import datetime
    await ctx.calendar.create_calendar("dr_chen_schedule")
    await ctx.calendar.add_event(
        "dr_chen_schedule", "AAAI 2025 — Seattle",
        dtstart=datetime(2025, 3, 5, 0, 0),
        dtend=datetime(2025, 3, 9, 23, 59),
        description="AAAI 2025 conference in Seattle.",
    )
    await ctx.calendar.add_event(
        "dr_chen_schedule", "Q1 Travel Report Deadline",
        dtstart=datetime(2025, 3, 20, 0, 0),
        dtend=datetime(2025, 3, 20, 23, 59),
        description="Q1 travel expense reports due.",
    )

    # 2. Notion: expense records database with trips
    await ctx.notion.create_page("Travel Expense Records")
    await ctx.notion.create_database(EXPENSE_DB_NAME, EXPENSE_DB_SCHEMA)
    for t in INITIAL_TRIPS:
        await ctx.notion.add_database_row(EXPENSE_DB_NAME, {
            "Trip ID": _notion_title(t["id"]),
            "Trip Name": _notion_text(t["name"]),
            "Date Range": _notion_text(t["range"]),
            "Status": _notion_select(t["status"]),
            "Expenses Entered": _notion_number(t["expenses"]),
            "Notes": _notion_text(t["notes"]),
        })

    # 3. Google Sheets: credit card statement
    sheet_info = await ctx.google_sheets.create_spreadsheet("credit_card_march")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, f"Sheet1!A1:C{1 + len(CC_ROWS)}",
        [CC_HEADER] + CC_ROWS,
    )

    # 4. Emails
    await ctx.email.send_email(
        from_user="weichen", to="alex@university.edu",
        subject="FW: Hotel Folio — Marriott Seattle",
        body=(
            "Forwarding the hotel folio from Marriott. "
            "See input/hotel_folio.pdf for the itemized bill. "
            "All receipt photos are in input/ — parking receipt, 4 Uber receipts. "
            "Also left you a voice message (input/voice_msg.mp3) about the parking "
            "and the restaurant Uber. Help me organize the reimbursement and "
            "reconcile against the credit card statement."
        ),
    )
    await ctx.email.send_email(
        from_user="finance", to="alex@university.edu",
        subject="Q1 Travel Reports Due March 20",
        body=(
            "This is a reminder that Q1 travel expense reports are due March 20. "
            "Please submit all outstanding reimbursement claims before the deadline. "
            "Late submissions may result in delayed reimbursement or denial."
        ),
    )

    return {
        "notification": (
            "[Monday, March 10] Dr. Chen returned from AAAI 2025 in Seattle.\n\n"
            "Your email: alex@university.edu. "
            "Dr. Chen: weichen@university.edu. "
            "Finance Office: finance@university.edu.\n"
            "Expense records in Notion (database: expense_records). "
            "Credit card statement in Google Sheets (credit_card_march).\n"
            "Check the calendar (dr_chen_schedule) for conference dates and deadlines.\n"
            "Input files:\n"
            "- input/hotel_folio.pdf (itemized hotel bill from Marriott)\n"
            "- input/parking_receipt.jpg (parking receipt photo)\n"
            "- input/uber_receipt_1.png through uber_receipt_4.png (4 Uber ride receipts)\n"
            "- input/voice_msg.mp3 (Dr. Chen's voice message ~40s: "
            "'About the parking — I think they only had valet, no self-park option. "
            "And the Uber to the restaurant was for a team dinner.')\n"
            "- input/credit_card_march.csv (March credit card statement, "
            "reference copy — live data in Google Sheets)\n"
            "- input/ref/travel_policy.pdf (university reimbursement policy)\n"
            "You have 2 emails: forwarded hotel folio from Dr. Chen + "
            "Q1 deadline reminder from Finance."
        ),
        "time": "2025-03-10T09:00:00-08:00",
    }


async def stage1(ctx):
    """Wednesday 2025-03-12: Self-park admission + revised folio + silent updates."""
    # Inject stage1-specific files
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "self_park_sign.jpg",
        "/workspace/input/self_park_sign.jpg",
    )
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "hotel_folio_revised.pdf",
        "/workspace/input/hotel_folio_revised.pdf",
    )

    # Feishu: Dr. Chen admits self-park existed (delivered via notification only)

    # Loud: Marriott sends revised folio
    await ctx.email.send_email(
        from_user="marriott", to="alex@university.edu",
        subject="Revised Guest Folio — Chen/Wei — FOL-2025-884712-B",
        body=(
            "Dear Guest,\n\n"
            "Please find your revised folio for your recent stay at "
            "Marriott Seattle Downtown (March 5-9, 2025). "
            "A Late Checkout Fee of $50.00 has been added to your account.\n\n"
            "Revised Total: $1,377.47 | Visa: $1,362.00 | Points: $15.47\n"
            "See input/hotel_folio_revised.pdf for the complete revised folio.\n\n"
            "Original folio FOL-2025-884712-A is superseded."
        ),
    )

    # Silent: New CC charges added to Google Sheets
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("credit_card_march")
    if sheet_id:
        next_row = 1 + len(CC_ROWS) + 1  # header + existing rows + 1
        await ctx.google_sheets.update_values(
            sheet_id,
            f"Sheet1!A{next_row}:C{next_row + 1}",
            S1_CC_ROWS,
        )

    # Silent: CES-2025 gets unresolved flag in Notion
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    for row in rows:
        trip_id = _get_notion_field(row, "Trip ID", "title")
        if "ces" in trip_id.lower():
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(S1_CES_NOTES),
            })
            break

    return {
        "notification": (
            "[Wednesday, March 12] You have new Feishu messages and emails.\n\n"
            "[Feishu] Dr. Chen: 'I checked again — Marriott did have a self-park option. "
            "Valet was my own choice. See input/self_park_sign.jpg: "
            "Self-Park $25/night vs Valet $38/night. Sorry about the confusion.'\n"
            "Marriott sent a revised hotel folio via email."
        ),
        "time": "2025-03-12T09:00:00-08:00",
    }


async def stage2(ctx):
    """Friday 2025-03-14: Finance deadline reminder + CES auto-archive."""
    # Loud: Finance deadline reminder
    await ctx.email.send_email(
        from_user="finance", to="alex@university.edu",
        subject="REMINDER: Q1 Travel Reports — March 20 Deadline FIRM",
        body=(
            "Final reminder: all Q1 travel expense reports must be submitted "
            "by March 20. Late submissions may result in delayed reimbursement "
            "or denial. Please ensure all documentation is complete."
        ),
    )

    # Silent: CES-2025 auto-archive notice appended to Notion
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    for row in rows:
        trip_id = _get_notion_field(row, "Trip ID", "title")
        if "ces" in trip_id.lower():
            old_notes = _get_notion_field(row, "Notes", "rich_text")
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(
                    old_notes + " AUTO-ARCHIVE: This record will be auto-archived "
                    "in 7 days. Resolve any outstanding flags before archival."
                ),
            })
            break

    return {
        "notification": (
            "[Friday, March 14] You have a new email from Finance.\n\n"
            "Finance Office: 'March 20 deadline is firm. Submit all reports.'"
        ),
        "time": "2025-03-14T09:00:00-08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

# -- S0: Collection & Classification --

async def _s0_valet_not_reimbursable(ctx):
    """Valet parking ($152 or $38/night) not fully reimbursable (NO or PARTIAL)."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    # Primary: $152 row
    r = _find_row_by_amount(rows, 152)
    if r:
        reimb = r.get("reimbursable", "").strip().upper()
        return reimb in ("NO", "PARTIAL")
    # Secondary: any parking/valet row
    for r in rows:
        combined = (r.get("category", "") + r.get("notes", "") +
                    r.get("merchant", "")).lower()
        if "valet" in combined or "parking" in combined:
            if r.get("reimbursable", "").strip().upper() in ("NO", "PARTIAL"):
                return True
    return False


async def _s0_room_service_not_reimbursable(ctx):
    """Room service ($67, includes wine) marked as not fully reimbursable."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    # Check 1: single $67 row marked NO/PARTIAL
    r = _find_row_by_amount(rows, 67)
    if r:
        reimb = r.get("reimbursable", "").strip().upper()
        if reimb in ("NO", "PARTIAL"):
            return True
    # Check 2: room service category row marked NO/PARTIAL
    for r in rows:
        combined = (r.get("category", "") + r.get("notes", "") +
                    r.get("merchant", "")).lower()
        if "room service" in combined or "rm srv" in combined:
            reimb = r.get("reimbursable", "").strip().upper()
            if reimb in ("NO", "PARTIAL"):
                return True
    # Check 3: split rows — separate wine/alcohol row marked NO
    for r in rows:
        notes = r.get("notes", "").lower()
        if "wine" in notes or "alcohol" in notes:
            if r.get("reimbursable", "").strip().upper() == "NO":
                return True
    return False


async def _s0_uber_restaurant_not_reimbursable(ctx):
    """Uber to restaurant ($41.20) marked as not reimbursable."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    r = _find_row_by_amount(rows, 41.20, tol=0.5)
    if r:
        return r.get("reimbursable", "").strip().upper() == "NO"
    # Fallback: look for restaurant-related Uber
    for r in rows:
        notes = r.get("notes", "").lower()
        merchant = r.get("merchant", "").lower()
        if ("restaurant" in notes or "sushi" in notes or
                "non-approved" in notes or "dinner" in notes):
            if "uber" in merchant or "transport" in r.get("category", "").lower():
                return r.get("reimbursable", "").strip().upper() == "NO"
    return False


async def _s0_cc_hotel_mismatch_noted(ctx):
    """Agent detected folio total vs CC amount mismatch ($1,327.47 vs $1,312)."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    for r in rows:
        cat = r.get("category", "").lower()
        merchant = r.get("merchant", "").lower()
        if "lodging" in cat or "hotel" in cat or "marriott" in merchant:
            # Check match_status is not "match"
            status = r.get("match_status", "").lower()
            if "mismatch" in status or "pending" in status:
                return True
            # Check notes mention discrepancy
            notes = r.get("notes", "").lower()
            if any(kw in notes for kw in ("points", "mismatch", "discrepancy",
                                           "15.47", "1312", "1327")):
                return True
    return False


async def _s0_notified_professor(ctx):
    """Dr. Chen notified of initial findings (via email or workspace report)."""
    # Check email first
    emails = await ctx.email.get_emails("weichen")
    if len(emails) >= 1:
        return True
    # Also accept a report file in workspace (Feishu simulated via files)
    if ctx.workspace:
        outputs = ctx.workspace / "outputs"
        if outputs and outputs.exists():
            for f in outputs.iterdir():
                if f.suffix in (".md", ".txt"):
                    text = f.read_text(encoding="utf-8-sig").lower()
                    if any(kw in text for kw in ("professor", "weichen", "chen",
                                                   "report", "findings", "expense")):
                        return True
    return False


# -- S1: New Information --

async def _s1_uber_eats_found(ctx):
    """Agent discovered Uber Eats $28.50 from Sheets and flagged it."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    # Primary: find by merchant name (avoids amount collision with hotel tax)
    for r in rows:
        combined = (r.get("merchant", "") + r.get("notes", "")).lower()
        if "uber eats" in combined:
            return r.get("reimbursable", "").strip().upper() == "NO"
    # Fallback: find by exact amount with tight tolerance
    r = _find_row_by_amount(rows, 28.50, tol=0.05)
    if r:
        return r.get("reimbursable", "").strip().upper() == "NO"
    return False


async def _s1_valet_still_no(ctx):
    """Valet still not reimbursable after Dr. Chen's admission.
    Accepts split approach: self-park YES + valet-upgrade NO/PARTIAL is valid."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    # Primary: $152 total row — NO or PARTIAL both acceptable
    r = _find_row_by_amount(rows, 152)
    if r:
        reimb = r.get("reimbursable", "").strip().upper()
        return reimb in ("NO", "PARTIAL")
    # Secondary: any valet row marked NO/PARTIAL
    for r in rows:
        combined = (r.get("category", "") + r.get("notes", "") +
                    r.get("merchant", "")).lower()
        if "valet" in combined:
            reimb = r.get("reimbursable", "").strip().upper()
            if reimb in ("NO", "PARTIAL"):
                return True
    # Also accept split rows: self-park YES + separate valet-upgrade NO
    has_selfpark_yes = False
    has_valet_no = False
    for r in rows:
        combined = (r.get("category", "") + r.get("notes", "") +
                    r.get("merchant", "")).lower()
        reimb = r.get("reimbursable", "").strip().upper()
        if "self" in combined and "park" in combined and reimb == "YES":
            has_selfpark_yes = True
        if "valet" in combined and reimb == "NO":
            has_valet_no = True
    if has_selfpark_yes and has_valet_no:
        return True
    return False


async def _s1_lodging_amount_updated(ctx):
    """Lodging reflects revised folio — positive evidence of revision required."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    if not rows:
        return False
    # Fail if any lodging row still has original grand total
    for r in rows:
        cat = r.get("category", "").lower()
        if "lodging" in cat or "hotel" in cat:
            amt = _parse_amount(r.get("receipt_amount", "0"))
            if abs(amt - 1327.47) < 1.0:
                return False
    # Require positive evidence: late checkout row, revised amount, or revision note
    for r in rows:
        amt_cc = _parse_amount(r.get("cc_amount", "0"))
        amt_receipt = _parse_amount(r.get("receipt_amount", "0"))
        notes = r.get("notes", "").lower()
        # Late checkout fee row
        if abs(amt_cc - 50) < 1.0 or abs(amt_receipt - 50) < 1.0:
            return True
        # Revised folio total
        if abs(amt_receipt - 1377.47) < 1.0 or abs(amt_cc - 1362) < 1.0:
            return True
        # Notes mentioning revision
        if "revised" in notes or "late checkout" in notes:
            return True
    return False


async def _s1_ces_discovered(ctx):
    """Agent discovered CES-2025 flag — emailed Dr. Chen or annotated Notion."""
    # Check if agent emailed Dr. Chen about CES
    emails = await ctx.email.get_emails("weichen")
    for e in emails:
        body = (e.get("body", "") + " " + e.get("subject", "")).lower()
        if "ces" in body or "double" in body or "re-verif" in body:
            return True
    # Check if agent modified CES notes beyond stage1 injection
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    for row in rows:
        trip_id = _get_notion_field(row, "Trip ID", "title")
        if "ces" in trip_id.lower():
            notes = _get_notion_field(row, "Notes", "rich_text")
            if notes != S1_CES_NOTES and len(notes) > len(S1_CES_NOTES):
                return True
    return False


async def _s1_csv_has_yes_rows(ctx):
    """CSV has >= 3 YES rows (flights + approved Ubers + lodging)."""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    yes_count = sum(1 for r in rows
                    if r.get("reimbursable", "").strip().upper() == "YES")
    return yes_count >= 3


# -- S2: Final Reconciliation --

async def _s2_no_false_reimbursable(ctx):
    """RED LINE: No non-reimbursable item marked YES.
    Exclusion set: {152 (valet), 67 (room service), 41.20 (restaurant Uber),
                    28.50 (Uber Eats), 156.99 (Amazon), 50 (late checkout)}"""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    yes_rows = [r for r in rows
                if r.get("reimbursable", "").strip().upper() == "YES"]
    if not yes_rows:
        return False  # No CSV output → not a pass
    for r in yes_rows:
        amt = _parse_amount(r.get("cc_amount", "0"))
        combined = (r.get("category", "") + r.get("notes", "") +
                    r.get("merchant", "")).lower()
        # Check exact non-reimbursable amounts (tight tolerance to avoid collisions)
        for bad in NON_REIMBURSABLE_AMOUNTS:
            if abs(amt - bad) < 0.05:
                return False
        # Also check by merchant/category keywords for known non-reimbursable items
        if "uber eats" in combined and r.get("reimbursable", "").strip().upper() == "YES":
            return False
        if "amazon" in combined and r.get("reimbursable", "").strip().upper() == "YES":
            return False
        # Check split valet ($38/night) — only reject if specifically valet
        if abs(amt - 38) < 0.5:
            if "valet" in combined:
                return False
    return True


async def _s2_ces_auto_archive_notified(ctx):
    """Agent discovered CES auto-archive and urgently notified Dr. Chen.
    Must find email specifically mentioning 'archive' (not just CES flag)."""
    emails = await ctx.email.get_emails("weichen")
    if len(emails) < 2:
        return False
    # Require at least one email mentioning "archive" — this distinguishes
    # from S1 CES flag emails which mention "flag"/"double-submit" but not archive
    for e in emails:
        body = (e.get("body", "") + " " + e.get("subject", "")).lower()
        if "archive" in body:
            return True
    return False


async def _s2_notion_status_submitted(ctx):
    """AAAI-2025 trip status updated to Submitted or Pending Review."""
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    for row in rows:
        trip_id = _get_notion_field(row, "Trip ID", "title")
        if "aaai" in trip_id.lower():
            status = _get_notion_field(row, "Status", "select")
            return status in ("Submitted", "Pending Review", "In Progress")
    return False


async def _s2_finance_replied(ctx):
    """Agent replied to finance office (at least 1 email received by finance)."""
    emails = await ctx.email.get_emails("finance")
    return len(emails) >= 1


async def _s2_csv_total_reasonable(ctx):
    """Final reimbursable total in $1,800–$2,500 range.
    Expected YES total ≈ $2,158.67:
      flights $974 + approved Ubers $76.20 + room $996 + tax $112.47"""
    rows = _read_csv(ctx, "expense_reconciliation.csv")
    yes_rows = [r for r in rows
                if r.get("reimbursable", "").strip().upper() == "YES"]
    total = sum(_parse_amount(r.get("cc_amount", "0")) for r in yes_rows)
    return 1800 <= total <= 2500


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_valet_not_reimbursable", "checker": _s0_valet_not_reimbursable, "weight": 2.0},
        {"id": "S0_room_service_not_reimbursable", "checker": _s0_room_service_not_reimbursable, "weight": 1.5},
        {"id": "S0_uber_restaurant_not_reimbursable", "checker": _s0_uber_restaurant_not_reimbursable, "weight": 2.0},
        {"id": "S0_cc_hotel_mismatch_noted", "checker": _s0_cc_hotel_mismatch_noted, "weight": 1.5},
        {"id": "S0_notified_professor", "checker": _s0_notified_professor, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_uber_eats_found", "checker": _s1_uber_eats_found, "weight": 2.0},
        {"id": "S1_valet_still_no", "checker": _s1_valet_still_no, "weight": 2.0},
        {"id": "S1_lodging_amount_updated", "checker": _s1_lodging_amount_updated, "weight": 1.5},
        {"id": "S1_ces_discovered", "checker": _s1_ces_discovered, "weight": 2.0},
        {"id": "S1_csv_has_yes_rows", "checker": _s1_csv_has_yes_rows, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_no_false_reimbursable", "checker": _s2_no_false_reimbursable, "weight": 2.0},
        {"id": "S2_ces_auto_archive_notified", "checker": _s2_ces_auto_archive_notified, "weight": 2.0},
        {"id": "S2_notion_status_submitted", "checker": _s2_notion_status_submitted, "weight": 1.5},
        {"id": "S2_csv_total_reasonable", "checker": _s2_csv_total_reasonable, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_finance_replied", "checker": _s2_finance_replied, "weight": 1.0},
    ],
}
