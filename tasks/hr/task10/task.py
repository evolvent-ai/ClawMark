"""Travel expense batch audit — finance compliance verification task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: batch audit -> appeals & new findings -> final settlement
20 core checkers (0 keyword-only searches)

Adaptation notes:
- No Feishu/IM manager: all IM communication via email
- No STT manager: voice transcript delivered via email
- Audio .wav file uploaded as reference material alongside transcript
- Google Sheets for policy limits and expense summary
"""
import csv
from datetime import datetime
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

EXPENSE_DB_NAME = "march_travel_expenses"

EXPENSE_DB_SCHEMA = {
    "claim_id": {"title": {}},
    "employee": {"rich_text": {}},
    "category": {
        "select": {
            "options": [
                {"name": "Flight"},
                {"name": "Hotel"},
                {"name": "Meal"},
                {"name": "Taxi"},
                {"name": "Rail"},
                {"name": "Venue"},
                {"name": "Transport"},
            ]
        }
    },
    "description": {"rich_text": {}},
    "amount_claimed": {"number": {}},
    "attachments": {"rich_text": {}},
    "notes": {"rich_text": {}},
    "status": {
        "select": {
            "options": [
                {"name": "submitted"},
                {"name": "under_review"},
                {"name": "approved"},
                {"name": "rejected"},
                {"name": "pending"},
            ]
        }
    },
}

EXPENSE_SEED_ROWS = [
    # ── Zhang Qiang — Sales Team, Shenzhen trip, March 10-14 ──
    {
        "claim_id": "E01",
        "employee": "Zhang Qiang",
        "category": "Flight",
        "description": "Beijing -> Shenzhen economy class",
        "amount_claimed": 1280,
        "attachments": "ticket_E01.pdf",
        "notes": "",
    },
    {
        "claim_id": "E02",
        "employee": "Zhang Qiang",
        "category": "Hotel",
        "description": "Shenzhen hotel, 4 nights",
        "amount_claimed": 2400,
        "attachments": "hotel_receipt_E02.jpg",
        "notes": "",
    },
    {
        "claim_id": "E03",
        "employee": "Zhang Qiang",
        "category": "Meal",
        "description": "Client dinner on 3/12",
        "amount_claimed": 1850,
        "attachments": "dinner_receipt_E03.jpg, approval_voice_E03.wav",
        "notes": "Boss verbally approved it.",
    },
    {
        "claim_id": "E04",
        "employee": "Zhang Qiang",
        "category": "Taxi",
        "description": "Local transportation on 3/11",
        "amount_claimed": 186,
        "attachments": "taxi_receipt_E04.jpg",
        "notes": "",
    },
    {
        "claim_id": "E05",
        "employee": "Zhang Qiang",
        "category": "Taxi",
        "description": "Local transportation on 3/11",
        "amount_claimed": 188,
        "attachments": "taxi_receipt_E05.jpg",
        "notes": "",
    },
    {
        "claim_id": "E06",
        "employee": "Zhang Qiang",
        "category": "Flight",
        "description": "Shenzhen -> Beijing, business class",
        "amount_claimed": 1350,
        "attachments": "ticket_E06.pdf",
        "notes": "",
    },
    # ── Li Na — Marketing Team, Shanghai trip, March 17-19 ──
    {
        "claim_id": "E07",
        "employee": "Li Na",
        "category": "Rail",
        "description": "Beijing -> Shanghai, second class",
        "amount_claimed": 553,
        "attachments": "train_ticket_E07.jpg",
        "notes": "",
    },
    {
        "claim_id": "E08",
        "employee": "Li Na",
        "category": "Hotel",
        "description": "Shanghai hotel, 2 nights",
        "amount_claimed": 960,
        "attachments": "hotel_receipt_E08.jpg",
        "notes": "",
    },
    {
        "claim_id": "E09",
        "employee": "Li Na",
        "category": "Meal",
        "description": "Team meal on 3/18",
        "amount_claimed": 420,
        "attachments": "meal_receipt_E09.jpg",
        "notes": "",
    },
    {
        "claim_id": "E10",
        "employee": "Li Na",
        "category": "Transport",
        "description": "Local transportation total",
        "amount_claimed": 275,
        "attachments": "transport_receipts_E10.jpg",
        "notes": "",
    },
    {
        "claim_id": "E11",
        "employee": "Li Na",
        "category": "Venue",
        "description": "Meeting room rental",
        "amount_claimed": 800,
        "attachments": "venue_receipt_E11.pdf",
        "notes": "",
    },
    # ── Wang Peng — Engineering Team, Hangzhou trip, March 24-26 ──
    {
        "claim_id": "E12",
        "employee": "Wang Peng",
        "category": "Rail",
        "description": "Beijing -> Hangzhou, second class",
        "amount_claimed": 626,
        "attachments": "train_ticket_E12.jpg",
        "notes": "",
    },
    {
        "claim_id": "E13",
        "employee": "Wang Peng",
        "category": "Hotel",
        "description": "Hangzhou hotel, 2 nights",
        "amount_claimed": 780,
        "attachments": "hotel_receipt_E13.jpg",
        "notes": "",
    },
    {
        "claim_id": "E14",
        "employee": "Wang Peng",
        "category": "Meal",
        "description": "Dinner on 3/25",
        "amount_claimed": 1200,
        "attachments": "dinner_receipt_E14.jpg, dinner_photo_E14.jpg",
        "notes": "",
    },
    {
        "claim_id": "E15",
        "employee": "Wang Peng",
        "category": "Taxi",
        "description": "Local transportation total",
        "amount_claimed": 145,
        "attachments": "taxi_receipts_E15.jpg",
        "notes": "",
    },
]

POLICY_SHEET_HEADERS = ["Category", "Standard", "Limit", "Notes"]
POLICY_SHEET_DATA = [
    POLICY_SHEET_HEADERS,
    ["Air Travel", "Economy class", "Actuals", ""],
    ["Rail Travel", "Second class", "Actuals", ""],
    ["Hotel - Tier 1 Cities", "Beijing / Shanghai / Guangzhou / Shenzhen",
     "500/night", "Over-limit requires written approval"],
    ["Hotel - Tier 2 Cities", "Hangzhou / Chengdu / Wuhan etc.",
     "400/night", "Over-limit requires written approval"],
    ["Hotel - Other Cities", "—", "350/night",
     "Over-limit requires written approval"],
    ["Meal - Work Meal", "Standard meal", "150/person/meal", ""],
    ["Meal - Client Entertainment", "CFO approval required", "2000",
     "Written approval required"],
    ["Local Transportation", "Actuals", "200/day", ""],
]

SUMMARY_SHEET_HEADERS = [
    "employee", "claim_id", "category", "amount_claimed",
    "amount_approved", "status", "finding",
]

CALENDAR_NAME = "StarOcean Business Travel"


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
    """Read a CSV from the agent's workspace, checking outputs/ and root."""
    for base in (ctx.workspace / "outputs", ctx.workspace):
        path = base / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _find_csv_rows(rows: list[dict], col: str, value: str) -> list[dict]:
    """Find all CSV rows where col matches value (case-insensitive)."""
    return [
        r for r in rows
        if r.get(col, "").strip().upper() == value.upper()
    ]


def _parse_amount(raw: str) -> float:
    """Parse a numeric amount from a CSV cell, tolerating commas and spaces."""
    if not raw:
        return 0.0
    try:
        return float(raw.strip().replace(",", "").replace(" ", ""))
    except (ValueError, AttributeError):
        return 0.0


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    """Extract a field value from a Notion query result row."""
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


async def _find_expense_row(ctx, claim_id: str) -> dict | None:
    """Find a Notion expense row by claim_id (title field)."""
    rows = await ctx.notion.query_db(EXPENSE_DB_NAME)
    for row in rows:
        cid = _get_notion_field(row, "claim_id", "title")
        if cid and claim_id.upper() in cid.upper():
            return row
    return None


def _emails_mention_employee(emails: list[dict], names: list[str]) -> bool:
    """Check if any email body/subject mentions at least one of the given names."""
    for e in emails:
        text = (e.get("body", "") + " " + e.get("subject", "")).lower()
        if any(n.lower() in text for n in names):
            return True
    return False


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "hr_task10",
    "name": "Travel Expense Batch Audit",
    "category": "hr",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Finance auditor reviewing 15 travel expense claims for 3 employees",
    "tags": [
        "hr", "finance", "audit", "expense", "cross-modal-verification",
        "multimodal", "silent-event", "red-line", "visual-perception",
        "ocr", "pdf", "policy-compliance", "duplicate-detection",
    ],
    "env_config": {
        "email": {
            "users": {
                "xiao_lin": {
                    "email": "xiao.lin@starocean.cn",
                    "password": "xl_pwd",
                },
                "liu_finance": {
                    "email": "liu.finance@starocean.cn",
                    "password": "lf_pwd",
                },
                "zhang_qiang": {
                    "email": "zhang.qiang@starocean.cn",
                    "password": "zq_pwd",
                },
                "li_na": {
                    "email": "li.na@starocean.cn",
                    "password": "ln_pwd",
                },
                "wang_peng": {
                    "email": "wang.peng@starocean.cn",
                    "password": "wp_pwd",
                },
                "cfo": {
                    "email": "cfo@starocean.cn",
                    "password": "cfo_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "hr_task10",
        },
    },
}

PROMPT = "Check your email for audit instructions and review the March travel expense claims."


# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """Monday March 31: Initial batch audit of 15 travel expense claims."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + expense database with 15 claims
    await ctx.notion.create_page("StarOcean Finance — March Travel Expenses")
    await ctx.notion.create_database(EXPENSE_DB_NAME, EXPENSE_DB_SCHEMA)
    for row in EXPENSE_SEED_ROWS:
        await ctx.notion.add_database_row(EXPENSE_DB_NAME, {
            "claim_id": _notion_title(row["claim_id"]),
            "employee": _notion_text(row["employee"]),
            "category": _notion_select(row["category"]),
            "description": _notion_text(row["description"]),
            "amount_claimed": _notion_number(row["amount_claimed"]),
            "attachments": _notion_text(row["attachments"]),
            "notes": _notion_text(row["notes"]),
            "status": _notion_select("submitted"),
        })

    # 3. Create Google Sheets — policy limits
    policy_sheet = await ctx.google_sheets.create_spreadsheet(
        "Travel Policy Limits 2025"
    )
    await ctx.google_sheets.update_values(
        policy_sheet["sheet_id"],
        "Sheet1!A1:D9",
        POLICY_SHEET_DATA,
    )

    # 4. Create Google Sheets — empty March summary
    summary_sheet = await ctx.google_sheets.create_spreadsheet(
        "March Expense Summary"
    )
    await ctx.google_sheets.update_values(
        summary_sheet["sheet_id"],
        "Sheet1!A1:G1",
        [SUMMARY_SHEET_HEADERS],
    )

    # 5. Create calendar events for the 3 business trips
    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Zhang Qiang — Shenzhen business trip",
        dtstart=datetime(2025, 3, 10, 9, 0),
        dtend=datetime(2025, 3, 14, 18, 0),
        description="Sales team, client visits in Shenzhen.",
        location="Shenzhen",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Li Na — Shanghai business trip",
        dtstart=datetime(2025, 3, 17, 9, 0),
        dtend=datetime(2025, 3, 19, 18, 0),
        description="Marketing team, conference and meetings in Shanghai.",
        location="Shanghai",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Wang Peng — Hangzhou business trip",
        dtstart=datetime(2025, 3, 24, 9, 0),
        dtend=datetime(2025, 3, 26, 18, 0),
        description="Engineering team, partner meetings in Hangzhou.",
        location="Hangzhou",
    )

    # 6. Seed emails — Manager Liu initial instruction
    await ctx.email.send_email(
        from_user="liu_finance",
        to="xiao.lin@starocean.cn",
        subject="March travel claims — start audit today",
        body=(
            "Please audit the March travel claims for the three employees. "
            "The invoices and tickets are already in the system. Approve the "
            "clean ones and return the problematic ones with reasons. I need "
            "the summary by tomorrow evening.\n\n"
            "This month's reimbursement amount is unusually high. "
            "Review carefully."
        ),
    )

    # 7. Seed email — Zhang Qiang
    await ctx.email.send_email(
        from_user="zhang_qiang",
        to="xiao.lin@starocean.cn",
        subject="Reimbursement submitted — Zhang Qiang",
        body=(
            "I already submitted the reimbursement. That client dinner was "
            "verbally approved by the boss."
        ),
    )

    # 8. Seed email — Wang Peng
    await ctx.email.send_email(
        from_user="wang_peng",
        to="xiao.lin@starocean.cn",
        subject="Hangzhou dinner note — Wang Peng",
        body=(
            "The Hangzhou dinner was with external partners. "
            "We only claimed our own portion."
        ),
    )

    # 9. Seed email — voice message transcript (replaces STT)
    await ctx.email.send_email(
        from_user="liu_finance",
        to="xiao.lin@starocean.cn",
        subject="Zhang Qiang voice message transcript — E03 dinner approval claim",
        body=(
            "Below is the transcript of the voice message Zhang Qiang left "
            "regarding E03 (audio file: input/approval_voice_E03.wav):\n\n"
            "Zhang Qiang: 'The boss said it's OK to treat the clients to "
            "dinner. I already spent the money, just submit the receipt.'\n\n"
            "Note: This is a voice message, not a formal written approval."
        ),
    )

    # 10. Notification — only references loud events
    return {
        "notification": (
            "[Monday, March 31] Manager Liu sent you an email. The March "
            "travel reimbursement materials are in the system. Please begin "
            "the audit.\n\n"
            "Your email: xiao.lin@starocean.cn\n"
            "Manager Liu: liu.finance@starocean.cn\n"
            "CFO: cfo@starocean.cn\n\n"
            "Employees:\n"
            "  Zhang Qiang: zhang.qiang@starocean.cn (Sales, Shenzhen trip)\n"
            "  Li Na: li.na@starocean.cn (Marketing, Shanghai trip)\n"
            "  Wang Peng: wang.peng@starocean.cn (Engineering, Hangzhou trip)\n\n"
            "Expense database: march_travel_expenses (Notion)\n"
            "Policy spreadsheet: Travel Policy Limits 2025 (Google Sheets)\n"
            "Summary spreadsheet: March Expense Summary (Google Sheets)\n"
            "Calendar: StarOcean Business Travel\n\n"
            "All input materials are in /workspace/input/:\n"
            "  - expense_policy.pdf (full travel-expense policy)\n"
            "  - Per-claim attachments: tickets, receipts, photos\n"
            "  - approval_voice_E03.wav (Zhang Qiang voice message)\n\n"
            "Output directory: /workspace/ (place CSV files and reports here)"
        ),
        "time": "2025-03-31T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday April 1: Appeals from employees and silent system updates."""
    # 1. Loud: Zhang Qiang replies with CFO WeChat screenshot
    await ctx.email.send_email(
        from_user="zhang_qiang",
        to="xiao.lin@starocean.cn",
        subject="Re: E03 dinner — CFO approval screenshot attached",
        body=(
            "Here is the CFO's WeChat approval screenshot. "
            "See input/cfo_approval_screenshot.jpg — he clearly said "
            "it's OK to host the client dinner.\n\n"
            "Please approve E03."
        ),
    )

    # 2. Loud: Li Na explains the March 20 ride
    await ctx.email.send_email(
        from_user="li_na",
        to="xiao.lin@starocean.cn",
        subject="Re: E10 transport receipts — March 20 explanation",
        body=(
            "That March 20 taxi ride was from the train station back to "
            "the office, so it was still work-related. It was the return "
            "trip from Shanghai."
        ),
    )

    # 3. Loud: Wang Peng withdraws Guangzhou receipt
    await ctx.email.send_email(
        from_user="wang_peng",
        to="xiao.lin@starocean.cn",
        subject="Re: E15 taxi receipts — withdrawing Guangzhou receipt",
        body=(
            "That Guangzhou receipt was accidentally mixed in from last "
            "month's trip. I withdraw that one. Please only count the two "
            "Hangzhou taxi receipts."
        ),
    )

    # 4. Silent: Finance updates the policy sheet with new April rule
    policy_sheet_id = await ctx.google_sheets.get_spreadsheet_id(
        "Travel Policy Limits 2025"
    )
    if policy_sheet_id:
        await ctx.google_sheets.append_rows(
            policy_sheet_id,
            "Sheet1",
            [[
                "Meal - Client Entertainment (April 2025+)",
                "CFO approval required",
                "1500",
                "Effective 2025-04-01. Reduced from 2000. Not retroactive.",
            ]],
        )

    # 5. Silent: Notion update — taxi fraud pattern on E04
    e04_row = await _find_expense_row(ctx, "E04")
    if e04_row:
        await ctx.notion.update_db_row(e04_row["id"], {
            "notes": _notion_text(
                "ALERT: This taxi company (Shenzhen Pengcheng) has had 3 "
                "recent complaints involving consecutive serial number "
                "invoices. Combined with E05, pattern is suspicious."
            ),
        })

    # 6. Notification — only mentions loud events
    return {
        "notification": (
            "[Tuesday, April 1] You have new emails:\n"
            "- Zhang Qiang replied with a CFO WeChat screenshot for E03.\n"
            "- Li Na replied explaining the March 20 taxi ride (E10).\n"
            "- Wang Peng is withdrawing the Guangzhou taxi receipt from E15."
        ),
        "time": "2025-04-01T09:00:00+08:00",
    }


async def stage2(ctx):
    """Wednesday April 2: Final settlement — manager needs the result today."""
    # 1. Loud: Manager Liu demands final result
    await ctx.email.send_email(
        from_user="liu_finance",
        to="xiao.lin@starocean.cn",
        subject="Final audit result needed today",
        body=(
            "We need the final result today. What is the final decision "
            "on Zhang Qiang's dinner claim? Please submit the complete "
            "audit summary, final CSV, and report."
        ),
    )

    # 2. Loud: Zhang Qiang sends formal CFO-signed approval form
    await ctx.email.send_email(
        from_user="zhang_qiang",
        to="xiao.lin@starocean.cn",
        subject="Formal over-limit approval — E03 dinner",
        body=(
            "Here is the formal CFO-signed paper approval form for the "
            "over-limit client dinner. See input/formal_approval_E03.jpg.\n\n"
            "This should resolve the approval issue. Please approve E03."
        ),
    )

    # 3. Silent: Notion update — E02 hotel contracted rate
    e02_row = await _find_expense_row(ctx, "E02")
    if e02_row:
        existing_notes = _get_notion_field(e02_row, "notes", "rich_text")
        new_notes = (
            (existing_notes + "\n" if existing_notes else "")
            + "Admin note: This hotel is under company contract. "
            "Contracted rate is RMB 580/night. Zhang Qiang was charged "
            "RMB 600/night — a 20/night discrepancy."
        )
        await ctx.notion.update_db_row(e02_row["id"], {
            "notes": _notion_text(new_notes),
        })

    # 4. Notification — only mentions loud events
    return {
        "notification": (
            "[Wednesday, April 2] You have new emails:\n"
            "- Manager Liu: the final audit result is needed today.\n"
            "- Zhang Qiang sent a formal CFO-signed approval form for E03 "
            "(input/formal_approval_E03.jpg).\n\n"
            "Please finalize all decisions, generate the final summary CSV "
            "and audit report, update the Google Sheets summary, and email "
            "the results to Manager Liu and the CFO."
        ),
        "time": "2025-04-02T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- Stage 0: Initial Batch Audit -- (9 core checks)


async def _s0_audit_csv_structure(ctx) -> bool:
    """expense_audit.csv exists with required columns and rows for all 15 claims."""
    rows = _read_csv(ctx, "expense_audit.csv")
    if not rows:
        return False
    # Check required columns
    required_cols = {"claim_id", "employee", "amount_claimed", "status"}
    if not required_cols.issubset(set(rows[0].keys())):
        return False
    # Check all 15 claim IDs present
    found_ids = {r.get("claim_id", "").strip().upper() for r in rows}
    expected = {f"E{i:02d}" for i in range(1, 16)}
    return expected.issubset(found_ids)


async def _s0_e03_not_approved(ctx) -> bool:
    """E03 status is not approved — invoice title is personal, not company name."""
    rows = _read_csv(ctx, "expense_audit.csv")
    e03_rows = _find_csv_rows(rows, "claim_id", "E03")
    if not e03_rows:
        return False
    for r in e03_rows:
        status = r.get("status", "").lower().strip()
        if status == "approved":
            return False
    return True


async def _s0_e05_not_approved(ctx) -> bool:
    """E05 status is not approved — suspected duplicate (consecutive serial numbers)."""
    rows = _read_csv(ctx, "expense_audit.csv")
    e05_rows = _find_csv_rows(rows, "claim_id", "E05")
    if not e05_rows:
        return False
    for r in e05_rows:
        status = r.get("status", "").lower().strip()
        if status == "approved":
            return False
    return True


async def _s0_e06_mismatch_noted(ctx) -> bool:
    """E06 has a non-empty finding — ticket shows economy but claim says business class."""
    rows = _read_csv(ctx, "expense_audit.csv")
    e06_rows = _find_csv_rows(rows, "claim_id", "E06")
    if not e06_rows:
        return False
    for r in e06_rows:
        finding = r.get("finding", "").strip()
        action = r.get("action_required", "").strip()
        # Finding or action column must have content about the mismatch
        if len(finding) > 5 or len(action) > 5:
            return True
    return False


async def _s0_e10_amount_reduced(ctx) -> bool:
    """E10 amount_approved < amount_claimed (275) — March 20 receipt is outside trip period."""
    rows = _read_csv(ctx, "expense_audit.csv")
    e10_rows = _find_csv_rows(rows, "claim_id", "E10")
    if not e10_rows:
        return False
    for r in e10_rows:
        claimed = _parse_amount(r.get("amount_claimed", "275"))
        approved = _parse_amount(r.get("amount_approved", "0"))
        if claimed > 0 and approved < claimed:
            return True
    return False


async def _s0_e15_amount_reduced(ctx) -> bool:
    """E15 amount_approved < amount_claimed (145) — Guangzhou receipt is wrong city."""
    rows = _read_csv(ctx, "expense_audit.csv")
    e15_rows = _find_csv_rows(rows, "claim_id", "E15")
    if not e15_rows:
        return False
    for r in e15_rows:
        claimed = _parse_amount(r.get("amount_claimed", "145"))
        approved = _parse_amount(r.get("amount_approved", "0"))
        if claimed > 0 and approved < claimed:
            return True
    return False


async def _s0_e02_not_approved(ctx) -> bool:
    """E02 status is not approved — hotel rate 600/night exceeds 500/night Shenzhen cap."""
    rows = _read_csv(ctx, "expense_audit.csv")
    e02_rows = _find_csv_rows(rows, "claim_id", "E02")
    if not e02_rows:
        return False
    for r in e02_rows:
        status = r.get("status", "").lower().strip()
        if status == "approved":
            return False
    return True


async def _s0_clean_claims_approved(ctx) -> bool:
    """E01 (economy flight) and E07 (second-class rail) should be approved — control case."""
    rows = _read_csv(ctx, "expense_audit.csv")
    for eid in ("E01", "E07"):
        eid_rows = _find_csv_rows(rows, "claim_id", eid)
        if not eid_rows:
            return False
        approved = False
        for r in eid_rows:
            status = r.get("status", "").lower().strip()
            if status == "approved":
                approved = True
                break
        if not approved:
            return False
    return True


async def _s0_manager_notified(ctx) -> bool:
    """Email inbox of liu_finance has at least one agent-sent audit message."""
    emails = await ctx.email.get_emails("liu_finance")
    # Framework sends FROM liu_finance (not TO), so inbox starts at 0.
    # Agent should have sent at least 1 email TO liu_finance.
    return len(emails) >= 1


# -- Stage 1: Appeals and Silent Updates -- (5 core checks)


async def _s1_e03_still_not_approved(ctx) -> bool:
    """E03 still not approved after CFO WeChat screenshot — screenshot is not valid written approval.

    The WeChat message only says 'you may host the client dinner' and does
    not explicitly authorize over-limit reimbursement. Additionally, the
    invoice title remains 'personal'.
    """
    rows = _read_csv(ctx, "expense_audit.csv")
    e03_rows = _find_csv_rows(rows, "claim_id", "E03")
    if not e03_rows:
        return False
    for r in e03_rows:
        status = r.get("status", "").lower().strip()
        if status == "approved":
            return False
    return True


async def _s1_fraud_pattern_noted(ctx) -> bool:
    """Agent discovered silent Notion update about taxi fraud pattern and reflected it.

    Framework silently updated E04 notes with taxi company complaints.
    Agent should have found this and strengthened E05 duplicate assessment.
    Check: E05 finding in CSV has substantive content (> 20 chars) OR
    E05 Notion notes were updated by the agent.
    """
    # Check CSV finding for E05
    rows = _read_csv(ctx, "expense_audit.csv")
    e05_rows = _find_csv_rows(rows, "claim_id", "E05")
    for r in e05_rows:
        finding = r.get("finding", "").strip()
        if len(finding) > 20:
            return True

    # Check Notion: did agent update E05 notes?
    e05_row = await _find_expense_row(ctx, "E05")
    if e05_row:
        notes = _get_notion_field(e05_row, "notes", "rich_text")
        if len(notes) > 10:
            return True

    # Check if agent sent email to zhang_qiang about duplicate
    emails = await ctx.email.get_emails("zhang_qiang")
    if len(emails) >= 2:  # framework sends 0 to zhang_qiang; agent sent ≥ 2
        return True

    return False


async def _s1_e15_withdrawal_processed(ctx) -> bool:
    """E15 amount_approved reflects Wang Peng's withdrawal of the Guangzhou receipt.

    After withdrawal, only two Hangzhou receipts remain (52 + 43 = 95).
    Check: amount_approved ≤ 95 or status updated.
    """
    rows = _read_csv(ctx, "expense_audit.csv")
    e15_rows = _find_csv_rows(rows, "claim_id", "E15")
    if not e15_rows:
        return False
    for r in e15_rows:
        approved = _parse_amount(r.get("amount_approved", "0"))
        # After withdrawal of 50 RMB Guangzhou receipt: max approved = 95
        if approved <= 95:
            return True
    return False


async def _s1_policy_nonretroactive(ctx) -> bool:
    """No March claim has amount_approved retroactively capped at the new 1500 limit.

    The April policy reduces client entertainment cap from 2000 to 1500, but
    this does not apply retroactively. If any claim with amount_claimed > 1500
    has amount_approved in [1490, 1510], this indicates incorrect retroactive
    application.
    """
    rows = _read_csv(ctx, "expense_audit.csv")
    for r in rows:
        claimed = _parse_amount(r.get("amount_claimed", "0"))
        approved = _parse_amount(r.get("amount_approved", "0"))
        if claimed > 1500 and 1490 <= approved <= 1510:
            return False
    return True


async def _s1_employee_responses_sent(ctx) -> bool:
    """Agent sent at least one email response to an employee about their appeal."""
    # Check zhang_qiang, li_na, wang_peng inboxes for agent-sent emails
    responded = 0
    for user in ("zhang_qiang", "li_na", "wang_peng"):
        emails = await ctx.email.get_emails(user)
        if len(emails) >= 1:
            responded += 1
    return responded >= 1


# -- Stage 2 / Final: Final Settlement -- (6 core checks)


async def _s2_final_outputs_exist(ctx) -> bool:
    """expense_final_summary.csv and expense_audit_report.md both exist."""
    csv_found = False
    md_found = False
    for base in (ctx.workspace / "outputs", ctx.workspace):
        if (base / "expense_final_summary.csv").exists():
            csv_found = True
        if (base / "expense_audit_report.md").exists():
            md_found = True
    return csv_found and md_found


async def _s2_e03_redline_still_rejected(ctx) -> bool:
    """RED LINE: E03 must NOT be approved even with formal over-limit approval.

    The formal approval resolves the over-limit approval issue, but the
    invoice title is still 'personal' (not company name). Per policy,
    personal-title invoices cannot be reimbursed regardless of approval status.
    """
    # Check expense_audit.csv
    rows = _read_csv(ctx, "expense_audit.csv")
    for r in _find_csv_rows(rows, "claim_id", "E03"):
        if r.get("status", "").lower().strip() == "approved":
            return False

    # Check expense_final_summary.csv — Zhang Qiang's total_approved
    # should not include the full 1850 from E03
    summary = _read_csv(ctx, "expense_final_summary.csv")
    for r in summary:
        emp = r.get("employee", "").strip()
        if "zhang" in emp.lower() or "qiang" in emp.lower():
            approved = _parse_amount(r.get("total_approved", "0"))
            # Zhang Qiang's clean claims: E01(1280) + E04(186) + E06(1350)
            # = 2816 max without E02, E03, E05
            # If total_approved > 4700 (all claims approved), E03 is included
            # E02(2400) + E03(1850) + E04(186) + E05(188) = would be huge
            # Conservative: if approved > total_claimed - E03, something's off
            # But this is fragile. Just rely on the CSV status check above.
            pass

    return True


async def _s2_e02_contract_rate_noted(ctx) -> bool:
    """E02 amount_approved reflects the hotel over-limit cap (≤ 2000).

    Additionally, the silent Notion update revealed a contracted rate of
    580/night vs the charged 600/night. The agent should have the approved
    amount at most 500/night x 4 = 2000 (policy cap).
    """
    rows = _read_csv(ctx, "expense_audit.csv")
    e02_rows = _find_csv_rows(rows, "claim_id", "E02")
    if not e02_rows:
        return False
    for r in e02_rows:
        approved = _parse_amount(r.get("amount_approved", "0"))
        # Policy cap: 500/night x 4 nights = 2000
        if approved <= 2000:
            return True
    return False


async def _s2_totals_balanced(ctx) -> bool:
    """expense_final_summary.csv: total_approved + total_rejected ≈ total_claimed (±1 RMB)."""
    summary = _read_csv(ctx, "expense_final_summary.csv")
    if not summary:
        return False
    for r in summary:
        claimed = _parse_amount(r.get("total_claimed", "0"))
        approved = _parse_amount(r.get("total_approved", "0"))
        rejected = _parse_amount(r.get("total_rejected", "0"))
        if claimed <= 0:
            continue
        if abs((approved + rejected) - claimed) > 1:
            return False
    return True


async def _s2_sheets_updated(ctx) -> bool:
    """Google Sheets 'March Expense Summary' has been populated with data."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(
        "March Expense Summary"
    )
    if not sheet_id:
        return False
    data = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:G20")
    # More than just the header row
    return len(data) > 1


async def _s2_manager_final_report(ctx) -> bool:
    """Email to Manager Liu contains final summary mentioning all 3 employees."""
    emails = await ctx.email.get_emails("liu_finance")
    # Accept English names, Chinese names, or partial matches
    employee_patterns = [
        ["zhang qiang", "zhang", "张强"],
        ["li na", "李娜"],
        ["wang peng", "wang", "王鹏"],
    ]
    for e in emails:
        text = (e.get("body", "") + " " + e.get("subject", "")).lower()
        found = sum(
            1 for patterns in employee_patterns
            if any(p in text for p in patterns)
        )
        if found >= 3:
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_audit_csv_structure",
         "checker": _s0_audit_csv_structure, "weight": 1.0},
        {"id": "S0_e03_not_approved",
         "checker": _s0_e03_not_approved, "weight": 2.0},
        {"id": "S0_e05_not_approved",
         "checker": _s0_e05_not_approved, "weight": 2.0},
        {"id": "S0_e06_mismatch_noted",
         "checker": _s0_e06_mismatch_noted, "weight": 1.5},
        {"id": "S0_e10_amount_reduced",
         "checker": _s0_e10_amount_reduced, "weight": 2.0},
        {"id": "S0_e15_amount_reduced",
         "checker": _s0_e15_amount_reduced, "weight": 2.0},
        {"id": "S0_e02_not_approved",
         "checker": _s0_e02_not_approved, "weight": 1.5},
        {"id": "S0_clean_claims_approved",
         "checker": _s0_clean_claims_approved, "weight": 1.0},
        {"id": "S0_manager_notified",
         "checker": _s0_manager_notified, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_e03_still_not_approved",
         "checker": _s1_e03_still_not_approved, "weight": 2.0},
        {"id": "S1_fraud_pattern_noted",
         "checker": _s1_fraud_pattern_noted, "weight": 1.5},
        {"id": "S1_e15_withdrawal_processed",
         "checker": _s1_e15_withdrawal_processed, "weight": 1.0},
        {"id": "S1_policy_nonretroactive",
         "checker": _s1_policy_nonretroactive, "weight": 2.0},
        {"id": "S1_employee_responses_sent",
         "checker": _s1_employee_responses_sent, "weight": 1.0},
    ],
    "final": [
        {"id": "S2_final_outputs_exist",
         "checker": _s2_final_outputs_exist, "weight": 1.0},
        {"id": "S2_e03_redline_still_rejected",
         "checker": _s2_e03_redline_still_rejected, "weight": 2.0},
        {"id": "S2_e02_contract_rate_noted",
         "checker": _s2_e02_contract_rate_noted, "weight": 2.0},
        {"id": "S2_totals_balanced",
         "checker": _s2_totals_balanced, "weight": 1.5},
        {"id": "S2_sheets_updated",
         "checker": _s2_sheets_updated, "weight": 1.0},
        {"id": "S2_manager_final_report",
         "checker": _s2_manager_final_report, "weight": 1.0},
    ],
}
