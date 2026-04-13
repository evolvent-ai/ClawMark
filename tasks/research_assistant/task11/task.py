"""Cross-grant multi-trip year-end compliance audit — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: comprehensive audit → Dr. Chen's response + external updates → budget crisis + final
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
    "Grant": {"select": {"options": [
        {"name": "NSF"}, {"name": "DARPA"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "Draft"}, {"name": "Approved"}, {"name": "Under Review"},
        {"name": "Submitted"}, {"name": "Flagged"},
    ]}},
    "Total": {"number": {}},
    "Expenses": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}

INITIAL_TRIPS = [
    {
        "id": "CES-2025", "name": "CES 2025 Las Vegas",
        "range": "2025-01-07 to 2025-01-10", "grant": "DARPA",
        "status": "Approved", "total": 1340,
        "expenses": (
            "Hotel: $290/night x 3 = $870\n"
            "Team dinner: $470 (receipt: input/team_dinner_vegas.jpg)"
        ),
        "notes": "",
    },
    {
        "id": "ICML-2025", "name": "ICML 2025 Vienna",
        "range": "2025-04-15 to 2025-04-22", "grant": "NSF",
        "status": "Approved", "total": 6246,
        # D4 fix: no "Business Class" label — just "Flight $4,200"
        "expenses": (
            "Hotel: EUR 180/night x 7 = EUR 1,260 (reimbursed $1,386 @ 1.10)\n"
            "Flight: $4,200\n"
            "Registration: EUR 600 (reimbursed $660)"
        ),
        "notes": "Dr. Chen's handwritten notes: input/notebook_page.jpg",
    },
    {
        "id": "NeurIPS-2025", "name": "NeurIPS 2025 Montreal",
        "range": "2025-05-10 to 2025-05-14", "grant": "NSF",
        "status": "Approved", "total": 1530,
        "expenses": (
            "Hotel: $220/night x 4 = $880\n"
            "Registration: $650"
        ),
        "notes": "",
    },
]

NSF_BUDGET_HEADER = ["category", "budget", "spent", "remaining"]
NSF_BUDGET_ROWS = [
    ["travel_total", "35000.00", "28640.00", "6360.00"],
    ["domestic_travel", "15000.00", "12400.00", "2600.00"],
    ["international_travel", "20000.00", "16240.00", "3760.00"],
    ["equipment", "10000.00", "8750.00", "1250.00"],
    ["personnel", "120000.00", "98000.00", "22000.00"],
]

DEPT_FUND_HEADER = ["date", "description", "amount", "requestor", "status"]
DEPT_FUND_ROWS = [
    ["2024-08-20", "Welcome lunch for new PhD students", "320.00", "Dr. Chen", "paid"],
    ["2024-09-05", "Cloud computing credits (AWS) - Fall semester", "2400.00", "Dr. Chen", "paid"],
    ["2024-09-15", "Lab equipment repair", "1200.00", "Dr. Chen", "paid"],
    ["2024-10-12", "Student travel support - EMNLP 2024", "1100.00", "Dr. Chen", "paid"],
    ["2024-11-02", "Student conference travel support (AAAI)", "800.00", "Dr. Chen", "paid"],
    ["2024-11-18", "External hard drives (4x 4TB) for dataset storage", "480.00", "Dr. Chen", "paid"],
    ["2024-12-03", "Holiday team dinner - lab group", "410.00", "Dr. Chen", "paid"],
    ["2025-01-06", "Whiteboard markers and office supplies", "85.00", "Dr. Chen", "paid"],
    ["2025-01-20", "Software license renewal - MATLAB", "450.00", "Dr. Chen", "paid"],
    ["2025-02-14", "GPU server maintenance contract (Q1)", "1800.00", "Dr. Chen", "paid"],
    ["2025-03-01", "Cloud computing credits (AWS) - Spring semester", "2400.00", "Dr. Chen", "paid"],
    ["2025-03-10", "Guest speaker honorarium - Dr. Park", "500.00", "Dr. Chen", "paid"],
    ["2025-03-22", "Student travel support - CVPR 2025", "950.00", "Dr. Chen", "paid"],
    ["2025-04-05", "Lab monitor replacement (2x 27-inch)", "620.00", "Dr. Chen", "paid"],
    ["2025-04-20", "NeurIPS 2025 registration - $650 - paid by dept", "650.00", "Dr. Chen", "paid"],
    ["2025-05-01", "Poster printing (3 posters)", "180.00", "Dr. Chen", "paid"],
    ["2025-05-08", "Catering for lab retreat", "375.00", "Dr. Chen", "paid"],
    ["2025-05-15", "USB-C adapters and cables (bulk order)", "130.00", "Dr. Chen", "paid"],
]

# Stage 1 silent: updated NSF budget row (co-PI reimbursement $460)
S1_NSF_BUDGET_ROW = ["travel_total", "35000.00", "29100.00", "5900.00"]

# Stage 1 silent: CES dinner attendee list flag
S1_CES_NOTES = "Team dinner receipt flagged: missing attendee list (required per DARPA §3.4)."


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
    if not s:
        return 0.0
    try:
        return float(str(s).replace("$", "").replace(",", "").replace("€", "").strip())
    except (ValueError, AttributeError):
        return 0.0

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
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    elif field_type == "number":
        return prop.get("number", 0)
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


# ── METADATA & PROMPT ─────────────────────────────────────────────

METADATA = {
    "id": "research_assistant_task11",
    "name": "Cross-Grant Multi-Trip Compliance Audit",
    "category": "research_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "Dr. Wei Chen's administrative assistant",
    "tags": ["grant", "compliance", "audit", "multimodal", "image-trap",
             "cross-modal", "budget", "policy", "multi-trip"],
    "env_config": {
        "email": {
            "users": {
                "alex": {"email": "alex@university.edu", "password": "alex_pwd"},
                "weichen": {"email": "weichen@university.edu", "password": "weichen_pwd"},
                "grants": {"email": "grants@university.edu", "password": "grants_pwd"},
                "nsfpo": {"email": "nsf-po@nsf.gov", "password": "nsfpo_pwd"},
            },
        },
        "google_sheets": {"task_id": "research_assistant_task11"},
    },
}

PROMPT = "Year-end grant compliance audit due June 15. Audit all 3 trips for policy violations."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday 2025-06-02: Comprehensive audit of all 3 trips."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 1b. Calendar: Dr. Chen schedule
    from datetime import datetime
    await ctx.calendar.create_calendar("dr_chen_schedule")
    await ctx.calendar.add_event(
        "dr_chen_schedule", "CES 2025 — Las Vegas",
        dtstart=datetime(2025, 1, 7, 0, 0),
        dtend=datetime(2025, 1, 10, 23, 59),
        description="CES 2025 conference in Las Vegas.",
    )
    await ctx.calendar.add_event(
        "dr_chen_schedule", "ICML 2025 — Vienna",
        dtstart=datetime(2025, 4, 17, 0, 0),
        dtend=datetime(2025, 4, 20, 23, 59),
        description="ICML 2025 conference in Vienna. Conference sessions run Apr 17-20.",
    )
    await ctx.calendar.add_event(
        "dr_chen_schedule", "Grant Audit Deadline",
        dtstart=datetime(2025, 6, 15, 0, 0),
        dtend=datetime(2025, 6, 15, 23, 59),
        description="Annual grant compliance audit due.",
    )

    # 2. Notion: expense records with 3 trips
    await ctx.notion.create_page("Travel Expense Records — FY2025 Audit")
    await ctx.notion.create_database(EXPENSE_DB_NAME, EXPENSE_DB_SCHEMA)
    for t in INITIAL_TRIPS:
        await ctx.notion.add_database_row(EXPENSE_DB_NAME, {
            "Trip ID": _notion_title(t["id"]),
            "Trip Name": _notion_text(t["name"]),
            "Date Range": _notion_text(t["range"]),
            "Grant": _notion_select(t["grant"]),
            "Status": _notion_select(t["status"]),
            "Total": _notion_number(t["total"]),
            "Expenses": _notion_text(t["expenses"]),
            "Notes": _notion_text(t["notes"]),
        })

    # 3. Google Sheets: NSF budget + department fund log
    nsf_sheet = await ctx.google_sheets.create_spreadsheet("nsf_budget")
    nsf_id = nsf_sheet["sheet_id"]
    await ctx.google_sheets.update_values(
        nsf_id, f"Sheet1!A1:D{1 + len(NSF_BUDGET_ROWS)}",
        [NSF_BUDGET_HEADER] + NSF_BUDGET_ROWS,
    )

    dept_sheet = await ctx.google_sheets.create_spreadsheet("department_fund_log")
    dept_id = dept_sheet["sheet_id"]
    await ctx.google_sheets.update_values(
        dept_id, f"Sheet1!A1:E{1 + len(DEPT_FUND_ROWS)}",
        [DEPT_FUND_HEADER] + DEPT_FUND_ROWS,
    )

    # 4. Email: Grants Office audit notice
    await ctx.email.send_email(
        from_user="grants", to="alex@university.edu",
        subject="Annual Travel Compliance Audit — Due June 15",
        body=(
            "The annual travel compliance audit for FY2025 is due June 15. "
            "Please review all travel reimbursements charged to federal grants "
            "(NSF, DARPA) and ensure compliance with each grant's terms. "
            "Note: NSF cannot cover business class without prior written justification."
        ),
    )

    return {
        "notification": (
            "[Monday, June 2] Year-end grant compliance audit begins.\n\n"
            "Your email: alex@university.edu. "
            "Dr. Chen: weichen@university.edu. "
            "Grants Office: grants@university.edu.\n"
            "Expense records in Notion (database: expense_records) — 3 trips. "
            "NSF budget in Google Sheets (nsf_budget). "
            "Department fund log in Google Sheets (department_fund_log).\n"
            "Check the calendar (dr_chen_schedule) for conference dates and deadlines.\n"
            "Input files:\n"
            "- input/team_dinner_vegas.jpg (CES team dinner receipt)\n"
            "- input/notebook_page.jpg (Dr. Chen's handwritten Vienna travel notes)\n"
            "- input/ref/nsf_grant_terms.pdf (NSF grant travel policy)\n"
            "- input/ref/darpa_contract_terms.pdf (DARPA contract travel policy)\n"
            "Dr. Chen: 'Grants office is pushing for the year-end audit. "
            "Help me go through all 3 trips — make sure grants are charged correctly, "
            "no budget overruns. The Vienna flight might be a bit expensive.'\n"
            "You have 1 email from Grants Office about the audit deadline."
        ),
        "time": "2025-06-02T09:00:00-08:00",
    }


async def stage1(ctx):
    """Wednesday 2025-06-04: Dr. Chen's response + external updates."""
    # Inject stage1-specific files
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "flight_screenshot.png",
        "/workspace/input/flight_screenshot.png",
    )

    # Feishu: Dr. Chen sends flight screenshot (delivered via notification only)

    # Loud: NSF PO — missing foreign travel notification
    await ctx.email.send_email(
        from_user="nsfpo", to="alex@university.edu",
        subject="Missing Foreign Travel Notification — ICML 2025 Vienna",
        body=(
            "Dear Dr. Chen's office,\n\n"
            "Our records show that no foreign travel notification was submitted "
            "for the ICML 2025 trip to Vienna (April 15-22, 2025) under award "
            "NSF-CAREER-2024-XXXXX. Per NSF policy §2.1, foreign travel must be "
            "reported at least 30 days prior to departure. Please address this "
            "immediately.\n\nDr. Rebecca Torres, NSF Program Officer"
        ),
    )

    # Silent: NSF budget updated — co-PI reimbursement $460
    nsf_id = await ctx.google_sheets.get_spreadsheet_id("nsf_budget")
    if nsf_id:
        await ctx.google_sheets.update_values(
            nsf_id, "Sheet1!A2:D2", [S1_NSF_BUDGET_ROW],
        )

    # Silent: CES dinner flagged — missing attendee list
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    for row in rows:
        trip_id = _get_notion_field(row, "Trip ID", "title")
        if "ces" in trip_id.lower():
            old_notes = _get_notion_field(row, "Notes", "rich_text")
            new_notes = S1_CES_NOTES if not old_notes else old_notes + " " + S1_CES_NOTES
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(new_notes),
            })
            break

    return {
        "notification": (
            "[Wednesday, June 4] You have new Feishu messages and emails.\n\n"
            "[Feishu] Dr. Chen: 'The Vienna flight was booked 2 months in advance — "
            "economy was completely sold out. I had no choice. "
            "See input/flight_screenshot.png for the booking confirmation.'\n"
            "NSF Program Officer sent an email about "
            "missing foreign travel notification."
        ),
        "time": "2025-06-04T09:00:00-08:00",
    }


async def stage2(ctx):
    """Friday 2025-06-06: Budget crisis + final resolution."""
    # Inject stage2-specific files
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "vienna_meetings.jpg",
        "/workspace/input/vienna_meetings.jpg",
    )

    # Feishu: Dr. Chen suggests moving Vienna hotel to DARPA (notification only)
    # Feishu: Dr. Chen sends Vienna meeting notes (notification only)

    # Silent: Vienna hotel receipt expanded — minibar €45
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    for row in rows:
        trip_id = _get_notion_field(row, "Trip ID", "title")
        if "icml" in trip_id.lower():
            old_expenses = _get_notion_field(row, "Expenses", "rich_text")
            await ctx.notion.update_db_row(row["id"], {
                "Expenses": _notion_text(
                    old_expenses + "\nMinibar: EUR 45 (charged to room)"
                ),
            })
            break

    return {
        "notification": (
            "[Friday, June 6] You have new Feishu messages.\n\n"
            "[Feishu] Dr. Chen: 'Can we move the Vienna hotel charges from NSF to DARPA? "
            "It's all research anyway. That would free up the NSF budget.'\n"
            "[Feishu] Dr. Chen: 'Here are the meeting notes from the extra days. "
            "See input/vienna_meetings.jpg — proves I had legitimate research meetings.'"
        ),
        "time": "2025-06-06T09:00:00-08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

# -- S0: Comprehensive Audit --

async def _s0_alcohol_flagged(ctx):
    """CES dinner alcohol ($120 wine) flagged as violation."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    ces_rows = _find_all_csv_rows(rows, "trip_id", "ces")
    for r in ces_rows:
        vt = r.get("violation_type", "").lower()
        desc = r.get("item_desc", "").lower()
        if "alcohol" in vt or ("dinner" in desc and "alcohol" in vt):
            return True
        # Also accept if violation mentions wine
        if "wine" in vt or ("dinner" in desc and "wine" in r.get("recommended_action", "").lower()):
            return True
    return False


async def _s0_business_class_flagged(ctx):
    """ICML flight ($4,200 business class) flagged as non-compliant."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    icml_rows = _find_all_csv_rows(rows, "trip_id", "icml")
    for r in icml_rows:
        desc = r.get("item_desc", "").lower()
        if "flight" in desc or "airfare" in desc or "air" in desc:
            pc = r.get("policy_check", "").lower()
            return "non" in pc or pc == "non_compliant"
    return False


async def _s0_vienna_extra_days_flagged(ctx):
    """ICML non-conference nights (4/15+4/21) flagged."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    icml_rows = _find_all_csv_rows(rows, "trip_id", "icml")
    for r in icml_rows:
        desc = r.get("item_desc", "").lower()
        vt = r.get("violation_type", "").lower()
        if "hotel" in desc or "lodging" in desc or "night" in desc:
            pc = r.get("policy_check", "").lower()
            if "non" in pc or "adjust" in pc:
                return True
        if "extra" in vt or "night" in vt or "non_conference" in vt:
            return True
    return False


async def _s0_double_charge_found(ctx):
    """NeurIPS registration double charge (dept fund + NSF) discovered."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    neurips_rows = _find_all_csv_rows(rows, "trip_id", "neurips")
    for r in neurips_rows:
        vt = r.get("violation_type", "").lower()
        desc = r.get("item_desc", "").lower()
        action = r.get("recommended_action", "").lower()
        if "double" in vt or "duplicate" in vt or "double_charge" in vt:
            return True
        if "registration" in desc and ("double" in action or "duplicate" in action or "dept" in action):
            return True
    return False


async def _s0_budget_overrun_flagged(ctx):
    """NSF travel budget overrun identified ($6,360 < $7,776 needed)."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    for r in rows:
        vt = r.get("violation_type", "").lower()
        desc = r.get("item_desc", "").lower()
        if "budget" in vt or "overrun" in vt or "over" in vt:
            return True
        if "budget" in desc and ("over" in desc or "insuffi" in desc or "exceed" in desc):
            return True
    return False


# -- S1: Dr. Chen's Response + Updates --

async def _s1_flight_still_flagged(ctx):
    """Flight still non-compliant after Dr. Chen's screenshot evidence.
    Screenshot date 4/10 contradicts '2 months in advance' claim."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    icml_rows = _find_all_csv_rows(rows, "trip_id", "icml")
    for r in icml_rows:
        desc = r.get("item_desc", "").lower()
        if "flight" in desc or "airfare" in desc:
            pc = r.get("policy_check", "").lower()
            return "non" in pc or pc == "non_compliant"
    return False


async def _s1_attendee_list_flagged(ctx):
    """Agent discovered missing attendee list for CES dinner (C5 fix: content check)."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    ces_rows = _find_all_csv_rows(rows, "trip_id", "ces")
    for r in ces_rows:
        vt = r.get("violation_type", "").lower()
        desc = r.get("item_desc", "").lower()
        action = r.get("recommended_action", "").lower()
        if "attendee" in vt or "attendee" in desc or "attendee" in action:
            return True
        if "missing_attendee" in vt or "attendee_list" in vt:
            return True
    return False


async def _s1_nsf_budget_worsened(ctx):
    """Agent detected NSF budget further decreased (co-PI $460 reimbursement)."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    for r in rows:
        combined = " ".join(str(v) for v in r.values()).lower()
        # Check for evidence of updated budget calculation
        if "co-pi" in combined or "co_pi" in combined or "460" in combined:
            return True
        if "5900" in combined or "5,900" in combined:
            return True
    # Check if budget overrun amount reflects updated calculation
    for r in rows:
        vt = r.get("violation_type", "").lower()
        if "budget" in vt or "overrun" in vt:
            action = r.get("recommended_action", "").lower()
            if "updated" in action or "worsened" in action or "increased" in action:
                return True
            # Updated overrun should be > original $1,416
            amt = _parse_amount(r.get("amount", "0"))
            if 1500 <= amt <= 2500:
                return True
    return False


async def _s1_notified_professor(ctx):
    """Dr. Chen notified of NSF foreign travel issue (via email or workspace report)."""
    emails = await ctx.email.get_emails("weichen")
    if len(emails) >= 1:
        return True
    if ctx.workspace:
        outputs = ctx.workspace / "outputs"
        if outputs and outputs.exists():
            for f in outputs.iterdir():
                if f.suffix in (".md", ".txt"):
                    text = f.read_text(encoding="utf-8-sig").lower()
                    if any(kw in text for kw in ("professor", "weichen", "chen",
                                                   "nsf", "foreign travel", "budget")):
                        return True
    return False


async def _s1_csv_violations_grew(ctx):
    """Audit CSV has >= 7 rows (S0 ~5 findings + S1 foreign travel + attendee)."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    return len(rows) >= 7


# -- S2: Budget Crisis + Final Resolution --

async def _s2_no_grant_misallocation(ctx):
    """REVERSE: ICML-2025 trip grant still NSF in Notion (not moved to DARPA)."""
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    icml_found = False
    for row in rows:
        trip_id = _get_notion_field(row, "Trip ID", "title")
        if "icml" in trip_id.lower():
            icml_found = True
            grant = _get_notion_field(row, "Grant", "select")
            if grant.upper() != "NSF":
                return False
    return icml_found


async def _s2_vienna_days_still_flagged(ctx):
    """Non-conference nights still flagged after Dr. Chen's meeting notes.
    Notes dated 4/17+4/19 (during conference) don't prove 4/15-4/16 meetings."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    icml_rows = _find_all_csv_rows(rows, "trip_id", "icml")
    for r in icml_rows:
        desc = r.get("item_desc", "").lower()
        vt = r.get("violation_type", "").lower()
        if "hotel" in desc or "lodging" in desc or "night" in desc or "extra" in vt:
            pc = r.get("policy_check", "").lower()
            if "non" in pc or "adjust" in pc:
                return True
    return False


async def _s2_minibar_found(ctx):
    """Agent discovered minibar €45 charge in Vienna hotel (silent Notion update)."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    icml_rows = _find_all_csv_rows(rows, "trip_id", "icml")
    for r in icml_rows:
        vt = r.get("violation_type", "").lower()
        desc = r.get("item_desc", "").lower()
        if "minibar" in vt or "minibar" in desc:
            return True
    return False


async def _s2_replied_grants_office(ctx):
    """Agent replied to Grants Office (at least 1 email received)."""
    emails = await ctx.email.get_emails("grants")
    return len(emails) >= 1


async def _s2_csv_all_trips_covered(ctx):
    """Final CSV covers all 3 trips: CES-2025, ICML-2025, NeurIPS-2025."""
    rows = _read_csv(ctx, "grant_compliance_audit.csv")
    trip_ids = {r.get("trip_id", "").upper().replace("-", "") for r in rows}
    # Normalize: accept various formats
    found = set()
    for tid in trip_ids:
        if "CES" in tid:
            found.add("CES")
        elif "ICML" in tid:
            found.add("ICML")
        elif "NEURIPS" in tid or "NIPS" in tid:
            found.add("NEURIPS")
    return found == {"CES", "ICML", "NEURIPS"}


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_alcohol_flagged", "checker": _s0_alcohol_flagged, "weight": 2.0},
        {"id": "S0_vienna_extra_days_flagged", "checker": _s0_vienna_extra_days_flagged, "weight": 2.0},
        {"id": "S0_double_charge_found", "checker": _s0_double_charge_found, "weight": 2.0},
        {"id": "S0_budget_overrun_flagged", "checker": _s0_budget_overrun_flagged, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_business_class_flagged", "checker": _s0_business_class_flagged, "weight": 2.0},
        {"id": "S1_flight_still_flagged", "checker": _s1_flight_still_flagged, "weight": 2.0},
        {"id": "S1_attendee_list_flagged", "checker": _s1_attendee_list_flagged, "weight": 2.0},
        {"id": "S1_nsf_budget_worsened", "checker": _s1_nsf_budget_worsened, "weight": 1.5},
        {"id": "S1_notified_professor", "checker": _s1_notified_professor, "weight": 1.0},
        {"id": "S1_csv_violations_grew", "checker": _s1_csv_violations_grew, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_no_grant_misallocation", "checker": _s2_no_grant_misallocation, "weight": 2.0},
        {"id": "S2_vienna_days_still_flagged", "checker": _s2_vienna_days_still_flagged, "weight": 2.0},
        {"id": "S2_minibar_found", "checker": _s2_minibar_found, "weight": 2.0},
        {"id": "S2_csv_all_trips_covered", "checker": _s2_csv_all_trips_covered, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_replied_grants_office", "checker": _s2_replied_grants_office, "weight": 1.0},
    ],
}
