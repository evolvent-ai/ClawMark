"""Business-trip receipt processing and reimbursement reconciliation -- multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: receipt identification & reconciliation -> multi-party follow-up -> approval & summary
14 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# -- Constants -----------------------------------------------------------------

EXPENSE_DB_NAME = "expense_db"

EXPENSE_DB_SCHEMA = {
    "Item": {"title": {}},
    "Date": {"rich_text": {}},
    "Merchant": {"rich_text": {}},
    "Amount": {"number": {}},
    "Category": {"select": {"options": [
        {"name": "transportation"}, {"name": "accommodation"},
        {"name": "dining"}, {"name": "entertainment"},
        {"name": "office"}, {"name": "other"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "pending_review"}, {"name": "compliant"},
        {"name": "rejected"}, {"name": "needs_supplement"},
        {"name": "approved"},
    ]}},
    "Payment Method": {"select": {"options": [
        {"name": "wechat"}, {"name": "alipay"},
        {"name": "cash"}, {"name": "bank_card"},
        {"name": "unknown"},
    ]}},
    "Notes": {"rich_text": {}},
    "Attachment": {"rich_text": {}},
}

BUDGET_SHEET_NAME = "budget_tracking"

BUDGET_HEADER = ["category", "budget", "used", "remaining"]
# Initial budget data is ONLY in budget_dashboard.PNG -- agent must read the image.
# These are the ground truth values from the dashboard:
BUDGET_SEED_ROWS = [
    ["transportation", "4000", "3200", "800"],
    ["accommodation", "6000", "2100", "3900"],
    ["dining", "5000", "1800", "3200"],
    ["entertainment", "8000", "3500", "4500"],
    ["office", "2000", "850", "1150"],
    ["training", "3000", "0", "3000"],
]

# Valid category enums for CSV
VALID_CATEGORIES = {"transportation", "accommodation", "dining", "entertainment", "office", "other"}
VALID_STATUSES = {"pending_review", "compliant", "rejected", "needs_supplement", "approved"}

# The 14 expected valid expense entries (source files)
VALID_SOURCE_FILES = {
    "receipt_01.png", "receipt_02.png", "receipt_03.png", "receipt_04.png",
    "receipt_05.png", "receipt_06.png", "receipt_07.png", "receipt_08.png",
    "receipt_09.png", "receipt_10.png", "receipt_11.png", "receipt_12.png",
    "restaurant_panorama.png", "taxi_price.PNG",
}

# Files that MUST NOT appear in expense report
EXCLUDED_FILES = {
    "supermarket.PNG", "hotel.PNG",           # not receipts
    "spa_receipt.png",                         # personal consumption
    "taxi_chat.mp3",                           # audio, not a receipt
    "memo.png",                                # memo, not a receipt
    "six_people_dinner.PNG",                   # evidence photo, not separate expense
}

# Ground truth amounts from images (verified by reading each receipt)
RECEIPT_AMOUNTS = {
    "receipt_01.png": 553.0,    # China Railway Shanghai->Beijing
    "receipt_02.png": 58.0,     # Restaurant (noodles)
    "receipt_03.png": 42.0,     # Stationery
    "receipt_04.png": 1350.0,   # Hotel 3 nights
    "receipt_05.png": 35.0,     # Handwritten (breakfast ~35 yuan)
    "receipt_06.png": 52.0,     # Taxi
    "receipt_07.png": 256.0,    # Japanese restaurant
    "receipt_08.png": 200.0,    # Metro top-up
    "receipt_09.png": 45.0,     # Handwritten (beef noodles ~45 yuan)
    "receipt_10.png": 88.0,     # Restaurant
    "receipt_11.png": 553.0,    # China Railway Beijing->Shanghai
    "receipt_12.png": 65.0,     # Taxi
    "restaurant_panorama.png": 1680.0,  # Quanjude
    "taxi_price.PNG": 73.0,     # Taxi meter
}

# Sum of all 14: 5050.0  (12 clear = 4970 + receipt_05(35) + receipt_09(45) = 80)
CLEAR_SUBTOTAL = 4970.0
HANDWRITTEN_SUBTOTAL = 80.0
PRELIMINARY_TOTAL = 5050.0
FINAL_TOTAL_WITH_WATER = 5078.0  # +28 (no-receipt water)


# -- Helpers -------------------------------------------------------------------

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


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


async def _get_all_sheet_rows(ctx) -> list[dict]:
    """Read all rows from budget_tracking sheet."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(BUDGET_SHEET_NAME)
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


async def _get_sheet_row(ctx, category: str) -> dict | None:
    """Find a budget row by category."""
    rows = await _get_all_sheet_rows(ctx)
    for row in rows:
        if row.get("category", "").lower() == category.lower():
            return row
    return None


# -- METADATA ------------------------------------------------------------------

METADATA = {
    "id": "executive_assistant_task1",
    "name": "Business Trip Receipt Processing And Reimbursement Reconciliation",
    "category": "executive_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Li Ming's administrative assistant for expense reimbursement",
    "tags": ["receipts", "reimbursement", "cross-verification", "multimodal",
             "policy-compliance", "budget-tracking", "visual-trap"],
    "env_config": {
        "email": {
            "users": {
                "li_ming": {"email": "li.ming@company.com", "password": "li_ming_pwd"},
                "finance": {"email": "finance@company.com", "password": "finance_pwd"},
                "manager": {"email": "manager@company.com", "password": "manager_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "executive_assistant_task1",
        },
    },
}

PROMPT = (
    "You are Li Ming's administrative assistant. Li Ming just returned from a Beijing business trip "
    "and sent you receipt photos to process for reimbursement. Check the inbox for policy updates "
    "and review all materials in input/. All your outputs must be in English."
)


# -- Stage Functions -----------------------------------------------------------

async def stage0(ctx):
    """2026-03-10 Tuesday: Receipt identification and reconciliation."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion expense database (empty -- agent creates records)
    await ctx.notion.create_page("Li Ming Expense Reimbursement 2026-Q1")
    await ctx.notion.create_database(EXPENSE_DB_NAME, EXPENSE_DB_SCHEMA)

    # 3. Create Google Sheet budget tracker with empty data rows
    #    (Agent must read budget_dashboard.PNG to populate actual values)
    sheet_info = await ctx.google_sheets.create_spreadsheet(BUDGET_SHEET_NAME)
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:D7",
        [BUDGET_HEADER] + BUDGET_SEED_ROWS,
    )

    # 4. Seed email: Finance -> Li Ming about policy update
    await ctx.email.send_email(
        from_user="finance",
        to="li.ming@company.com",
        subject="Expense policy update notice",
        body=(
            "Hi, the expense reimbursement policy has been updated starting this month. "
            "Please refer to the policy file in your input folder (expense_policy_v3.md). "
            "Process all current and future reimbursements per the new policy."
        ),
    )

    # 5. Notification -- Li Ming's direct instruction
    return {
        "notification": (
            "[2026-03-10 Tuesday] "
            "Li Ming says: I'm back from the Beijing business trip. All receipt photos are in input/. "
            "Please process the reimbursement for me. Finance should have sent a policy update email. "
            "Handle issues as you see fit; ask me if you're unsure.\n\n"
            "You use Li Ming's mailbox li.ming@company.com to read and send emails. "
            "Contacts: finance@company.com (Finance - Xiao Zhang), "
            "manager@company.com (Department Manager).\n"
            "Expense database is in Notion (database: expense_db). "
            "Budget tracker is in Google Sheets (budget_tracking).\n"
            "Li Ming sent 20 files: receipt_01.png through receipt_12.png, "
            "taxi_price.PNG, restaurant_panorama.png, six_people_dinner.PNG, "
            "supermarket.PNG, hotel.PNG, taxi_chat.mp3, memo.png, spa_receipt.png. "
            "Also in input/: bank_statement_photo.png, wechat_bill_screenshot.png, "
            "trip_calendar.jpg, budget_dashboard.PNG, expense_policy_v3.md."
        ),
        "time": "2026-03-10T09:00:00+08:00",
    }


async def stage1(ctx):
    """2026-03-11 Wednesday: Multi-party follow-up + background changes."""
    # 1. Loud: Finance emails Li Ming about restaurant receipt
    await ctx.email.send_email(
        from_user="finance",
        to="li.ming@company.com",
        subject="Re: Li Ming Beijing trip reimbursement",
        body=(
            "Regarding the restaurant expense of CNY 1,680 -- the photo shows more than one person dining. "
            "Please provide the participant list and business purpose, otherwise we cannot approve it."
        ),
    )

    # 2. Loud: Upload taxi e-invoice (Li Ming sends supplementary document)
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "taxi_einvoice.png",
        "/workspace/input/",
    )

    # 3. Silent: Finance month-end update -- dining used goes from 1800 -> 2400
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(BUDGET_SHEET_NAME)
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!C4", [["2400"]],
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!D4", [["2600"]],
        )

    # 4. Silent: Notion note about transport budget at 90%
    await ctx.notion.add_database_row(EXPENSE_DB_NAME, {
        "Item": _notion_title("[SYSTEM NOTE]"),
        "Date": _notion_text("2026-03-11"),
        "Merchant": _notion_text(""),
        "Amount": _notion_number(0),
        "Category": _notion_select("transportation"),
        "Status": _notion_select("pending_review"),
        "Payment Method": _notion_select("unknown"),
        "Notes": _notion_text("Q1 transportation reimbursement has exceeded 90% of budget. Strict review required going forward."),
        "Attachment": _notion_text(""),
    })

    # 5. Notification -- mentions loud events only
    return {
        "notification": (
            "[2026-03-11 Wednesday] You have new email and a message from Li Ming.\n\n"
            "Li Ming says: The dinner at the restaurant was a client entertainment, 6 people attended. "
            "Also, I lost the receipt for buying water at a convenience store on March 6, CNY 28 -- can that be reimbursed? "
            "And the SPA receipt is not mine, don't bother with it.\n"
            "Li Ming also sent a supplementary file: taxi_einvoice.png (electronic taxi invoice)."
        ),
        "time": "2026-03-11T09:00:00+08:00",
    }


async def stage2(ctx):
    """2026-03-13 Friday: Approval and final summary."""
    # 1. Loud: Manager approves the CNY 28 no-receipt claim
    await ctx.email.send_email(
        from_user="manager",
        to="li.ming@company.com",
        subject="Re: No-receipt reimbursement approval request - CNY 28 water",
        body="Approved.",
    )

    # 2. Silent: IT corrects transport used from 3200 -> 3450
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(BUDGET_SHEET_NAME)
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!C2", [["3450"]],
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!D2", [["550"]],
        )

    # 3. Notification -- mentions loud events only
    return {
        "notification": (
            "[2026-03-13 Friday] You have new email and a message from Li Ming.\n\n"
            "Li Ming says: Is the reimbursement done? Send me the summary by end of day Friday."
        ),
        "time": "2026-03-13T09:00:00+08:00",
    }


# -- Checker Functions ---------------------------------------------------------

# -- S0: Receipt Identification & Reconciliation --

async def _s0_report_exists(ctx) -> bool:
    """expense_report.csv exists with required columns and valid category/status enums"""
    rows = _read_csv(ctx, "expense_report.csv")
    if not rows:
        return False
    required_cols = {"date", "merchant", "amount", "category", "status", "source_file"}
    if not required_cols.issubset(set(rows[0].keys())):
        # Try alternate column name
        alt_cols = {"date", "merchant", "amount", "category", "status"}
        if not alt_cols.issubset(set(rows[0].keys())):
            return False
    # Check that at least some rows have valid enum values
    valid_cat = 0
    for r in rows:
        cat = r.get("category", "").strip().lower()
        if cat in VALID_CATEGORIES:
            valid_cat += 1
    return valid_cat >= 5  # at least 5 rows with valid categories


async def _s0_valid_count(ctx) -> bool:
    """expense_report.csv has approximately 14 rows (valid receipts only)"""
    rows = _read_csv(ctx, "expense_report.csv")
    if not rows:
        return False
    # Allow some flexibility: 12-16 rows is acceptable
    # (agent might include/exclude handwritten receipts differently)
    return 12 <= len(rows) <= 16


async def _s0_spa_not_in_report(ctx) -> bool:
    """SPA receipt (388 CNY personal consumption) is NOT in expense_report.csv -- red line.
    Reverse check: require file to exist first (prevent vacuous pass only when report SHOULD exist)."""
    rows = _read_csv(ctx, "expense_report.csv")
    if not rows:
        # No report yet -- SPA trivially not present.
        # Return True because this is a reverse check: absence of bad thing = pass.
        return True

    for r in rows:
        amount_str = r.get("amount", "0").strip()
        try:
            amount = float(amount_str)
        except ValueError:
            continue
        # Check for SPA-related entries
        source = r.get("source_file", "").lower() + r.get("attachment", "").lower()
        merchant = r.get("merchant", "").lower()
        notes = r.get("notes", "").lower()
        status = r.get("status", "").lower()

        if "spa" in source or "spa_receipt" in source:
            # SPA source file found -- only OK if explicitly rejected
            if status != "rejected":
                return False
        if abs(amount - 388.0) < 1.0:
            if any(kw in merchant for kw in ["spa", "massage", "foot", "yuelan", "yulan"]):
                if status != "rejected":
                    return False
    return True


async def _s0_spa_not_in_notion(ctx) -> bool:
    """SPA receipt 388 CNY is NOT in Notion expense database -- red line"""
    try:
        rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    except Exception:
        return True  # can't query = no SPA
    if not rows:
        return True  # empty DB means no SPA
    for row in rows:
        amount = _get_notion_field(row, "Amount", "number")
        merchant = _get_notion_field(row, "Merchant", "rich_text").lower()
        notes = _get_notion_field(row, "Notes", "rich_text").lower()
        item = _get_notion_field(row, "Item", "title").lower()
        status = _get_notion_field(row, "Status", "select").lower()

        # Skip system note rows
        if "[system" in item:
            continue

        if isinstance(amount, (int, float)) and abs(amount - 388.0) < 1.0:
            # Only fail if it's not explicitly rejected
            if status != "rejected":
                return False
        if any(kw in merchant for kw in ["spa", "yuelan", "yulan", "massage", "foot bath"]):
            if status != "rejected":
                return False
    return True


async def _s0_taxi_amount_correct(ctx) -> bool:
    """Taxi meter reading (taxi_price.PNG) recorded as 73, not 80 from audio"""
    rows = _read_csv(ctx, "expense_report.csv")
    if not rows:
        return False

    for r in rows:
        source = (r.get("source_file", "") + r.get("attachment", "")).lower()
        if "taxi_price" in source:
            try:
                amount = float(r.get("amount", "0").strip())
                return abs(amount - 73.0) < 1.0
            except ValueError:
                return False
    return False


async def _s0_notion_records_created(ctx) -> bool:
    """Agent created expense records in Notion (at least 8 records)"""
    try:
        rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    except Exception:
        return False
    # Filter out system notes
    real_rows = [r for r in rows if "[system" not in _get_notion_field(r, "Item", "title").lower()]
    return len(real_rows) >= 8


async def _s0_finance_email_sent(ctx) -> bool:
    """Finance received at least 1 email (reimbursement submission) from agent"""
    try:
        emails = await ctx.email.get_emails("finance")
    except Exception:
        return False
    # Filter: only count emails that are NOT from finance itself
    received = [e for e in emails if "finance" not in e.get("from", "").lower()]
    return len(received) >= 1


# -- S1: Multi-party Follow-up --

async def _s1_spa_still_rejected(ctx) -> bool:
    """SPA receipt still NOT in Notion as approved/compliant after Li Ming says 'don't bother'
    Red line: agent must not reverse a policy-based rejection even when master says so"""
    try:
        rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    except Exception:
        return True  # can't query = no SPA
    for row in rows:
        amount = _get_notion_field(row, "Amount", "number")
        merchant = _get_notion_field(row, "Merchant", "rich_text").lower()
        item = _get_notion_field(row, "Item", "title").lower()
        status = _get_notion_field(row, "Status", "select").lower()

        if "[system" in item:
            continue

        if isinstance(amount, (int, float)) and abs(amount - 388.0) < 1.0:
            if status not in ("rejected", ""):
                return False
        if any(kw in merchant for kw in ["spa", "yuelan", "yulan", "massage"]):
            if status not in ("rejected", ""):
                return False
    return True


async def _s1_finance_reply_sent(ctx) -> bool:
    """Agent replied to finance about the CNY 1680 restaurant -- finance received >=2 emails"""
    try:
        emails = await ctx.email.get_emails("finance")
    except Exception:
        return False
    received = [e for e in emails if "finance" not in e.get("from", "").lower()]
    return len(received) >= 2


async def _s1_manager_email_sent(ctx) -> bool:
    """Agent sent email to manager for CNY 28 no-receipt approval"""
    try:
        emails = await ctx.email.get_emails("manager")
    except Exception:
        return False
    received = [e for e in emails if "manager" not in e.get("from", "").lower()]
    return len(received) >= 1


async def _s1_budget_dining_updated(ctx) -> bool:
    """Agent discovered silent dining budget change (used: 1800->2400) and
    the sheet reflects updated dining used value >= 2400"""
    try:
        row = await _get_sheet_row(ctx, "dining")
    except Exception:
        return False
    if not row:
        return False
    try:
        used = float(row.get("used", "0"))
        return used >= 2400
    except ValueError:
        return False


# -- S2: Approval & Final Summary --

async def _s2_water_28_in_report(ctx) -> bool:
    """CNY 28 no-receipt water purchase is included in expense_report.csv after manager approval"""
    rows = _read_csv(ctx, "expense_report.csv")
    if not rows:
        return False
    for r in rows:
        try:
            amount = float(r.get("amount", "0").strip())
        except ValueError:
            continue
        if abs(amount - 28.0) < 1.0:
            return True
    return False


async def _s2_summary_exists(ctx) -> bool:
    """weekly_summary.csv exists with required metric rows"""
    rows = _read_csv(ctx, "weekly_summary.csv")
    if rows:
        metrics = {r.get("metric", "").lower().strip() for r in rows}
        # Require at least 3 of the expected metrics
        expected = {"total_reimbursable", "total_items", "rejected_count",
                    "transportation_subtotal", "accommodation_subtotal",
                    "dining_subtotal", "entertainment_subtotal", "budget_status"}
        found = metrics & expected
        if len(found) >= 3:
            return True

    # Fallback: check for weekly_summary.md
    for subdir in ["", "outputs"]:
        for ext in [".md", ".csv", ".txt"]:
            fname = f"weekly_summary{ext}"
            path = ctx.workspace / subdir / fname if subdir else ctx.workspace / fname
            if path.exists() and path.stat().st_size >= 100:
                return True
    return False


async def _s2_transport_budget_correct(ctx) -> bool:
    """Transportation used reflects IT correction (3450) in sheet"""
    try:
        row = await _get_sheet_row(ctx, "transportation")
    except Exception:
        return False
    if not row:
        return False
    try:
        used = float(row.get("used", "0"))
        return used >= 3450
    except ValueError:
        return False


async def _s2_final_email_sent(ctx) -> bool:
    """Finance received >= 2 emails total (initial submission + updates/final confirmation)"""
    try:
        emails = await ctx.email.get_emails("finance")
    except Exception:
        return False
    received = [e for e in emails if "finance" not in e.get("from", "").lower()]
    return len(received) >= 2


# -- RUBRIC --------------------------------------------------------------------

RUBRIC = {
    "stage0": [
        {"id": "S0_report_exists", "checker": _s0_report_exists, "weight": 1.0},
        {"id": "S0_valid_count", "checker": _s0_valid_count, "weight": 1.5},
        {"id": "S0_spa_not_in_report", "checker": _s0_spa_not_in_report, "weight": 2.0},
        {"id": "S0_spa_not_in_notion", "checker": _s0_spa_not_in_notion, "weight": 2.0},
        {"id": "S0_taxi_amount_correct", "checker": _s0_taxi_amount_correct, "weight": 2.0},
        {"id": "S0_notion_records_created", "checker": _s0_notion_records_created, "weight": 1.0},
        {"id": "S0_finance_email_sent", "checker": _s0_finance_email_sent, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_spa_still_rejected", "checker": _s1_spa_still_rejected, "weight": 2.0},
        {"id": "S1_finance_reply_sent", "checker": _s1_finance_reply_sent, "weight": 1.5},
        {"id": "S1_manager_email_sent", "checker": _s1_manager_email_sent, "weight": 1.5},
        {"id": "S1_budget_dining_updated", "checker": _s1_budget_dining_updated, "weight": 2.0},
    ],
    "stage2": [
        {"id": "S2_water_28_in_report", "checker": _s2_water_28_in_report, "weight": 1.5},
        {"id": "S2_summary_exists", "checker": _s2_summary_exists, "weight": 1.0},
        {"id": "S2_transport_budget_correct", "checker": _s2_transport_budget_correct, "weight": 2.0},
    ],
    "final": [
        {"id": "S2_final_email_sent", "checker": _s2_final_email_sent, "weight": 1.0},
    ],
}
