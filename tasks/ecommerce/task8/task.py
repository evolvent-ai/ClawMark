"""Supplier claim evidence collection & compensation proposal.

Environments: filesystem, email, notion, google_sheets
3 stages: data cleanup → rebuttal & scrap updates → final deduction & internal review
15 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

CLAIM_DB_NAME = "claim_events"

CLAIM_DB_SCHEMA = {
    "claim_id": {"title": {}},
    "supplier": {"rich_text": {}},
    "lot_id": {"rich_text": {}},
    "total_rma_qty": {"number": {}},
    "excluded_qty": {"number": {}},
    "claimable_qty": {"number": {}},
    "status": {"select": {"options": [
        {"name": "draft"}, {"name": "under_review"}, {"name": "submitted"},
        {"name": "approved"}, {"name": "closed"},
    ]}},
    "approval_needed": {"select": {"options": [{"name": "YES"}, {"name": "NO"}]}},
    "notes": {"rich_text": {}},
}

CLAIM_HEADER = [
    "rma_id", "order_id", "sku", "lot_id", "return_reason",
    "logistics_damage_flag", "customer_misuse_flag", "qty",
    "received_date", "scrap_confirmed",
]

CLAIM_ROWS = [
    ["RMA-0001", "ORD-1009", "SKU-A001", "LOT-2024-01", "Defective unit - no power", "0", "0", "1", "2024-11-03", ""],
    ["RMA-0007", "ORD-1010", "SKU-B002", "LOT-2024-01", "Screen flickering issue", "0", "0", "1", "2024-11-10", ""],
    ["RMA-0012", "ORD-1002", "SKU-B003", "LOT-2024-02", "Package crushed in transit", "1", "0", "3", "2024-10-15", ""],
    ["RMA-0018", "ORD-1011", "SKU-C003", "LOT-2024-02", "Missing components in package", "0", "0", "1", "2024-11-10", ""],
    ["RMA-0023", "ORD-1003", "SKU-C001", "LOT-2024-02", "Water damage from shipping", "1", "0", "1", "2024-10-15", ""],
    ["RMA-0031", "ORD-1004", "SKU-A003", "LOT-2024-03", "Item broken in transit", "1", "0", "2", "2024-10-15", ""],
    ["RMA-0040", "ORD-1012", "SKU-D001", "LOT-2024-03", "Firmware failure", "0", "0", "2", "2024-11-10", ""],
    ["RMA-0045", "ORD-1001", "SKU-A001", "LOT-2024-01", "Damaged on arrival", "1", "0", "2", "2024-11-03", ""],
    ["RMA-0055", "ORD-1006", "SKU-B001", "LOT-2024-02", "Improper installation by customer", "0", "1", "1", "2024-10-15", ""],
    ["RMA-0061", "ORD-1013", "SKU-A002", "LOT-2024-03", "Cosmetic defect - scratched surface", "0", "0", "1", "2024-11-10", ""],
    ["RMA-0067", "ORD-1001", "SKU-A002", "LOT-2024-01", "Wrong item received", "0", "0", "1", "2024-11-10", ""],
    ["RMA-0072", "ORD-1007", "SKU-C002", "LOT-2024-04", "Used beyond rated capacity", "0", "1", "1", "2024-10-15", ""],
    ["RMA-0083", "ORD-1008", "SKU-A004", "LOT-2024-04", "Exposed to moisture against guidelines", "0", "1", "2", "2024-10-15", ""],
    ["RMA-0089", "ORD-1005", "SKU-D002", "LOT-2024-03", "Outer carton severely damaged", "1", "0", "1", "2024-10-15", ""],
    ["RMA-0095", "ORD-1014", "SKU-B004", "LOT-2024-04", "Battery drains too fast", "0", "0", "1", "2024-11-10", ""],
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
    "id": "ecommerce_task8",
    "name": "Supplier Claim Evidence Collection & Compensation Proposal",
    "category": "ecommerce",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Liu Fang's after-sales assistant at Curato",
    "tags": [
        "supplier-claim", "evidence", "compensation",
        "multimodal", "data-cleaning", "financial",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@curato.com",
                    "password": "assistant_pwd",
                },
                "liufang": {
                    "email": "liufang@curato.com",
                    "password": "liufang_pwd",
                },
                "zhaoqiang": {
                    "email": "zhaoqiang@curato.com",
                    "password": "zhaoqiang_pwd",
                },
                "finance": {
                    "email": "finance@curato.com",
                    "password": "finance_pwd",
                },
                "supplier_a": {
                    "email": "supplier-a@curato.com",
                    "password": "supplier_a_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "ecommerce_task8",
        },
    },
}

PROMPT = "Clean up the supplier A claim data, exclude ineligible items, and produce a compensation proposal."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Mar 26 09:00 — Liu Fang asks agent to clean claim data and produce proposal."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed Notion
    await ctx.notion.create_page("Supplier Claims 2024-Q1")
    await ctx.notion.create_database(CLAIM_DB_NAME, CLAIM_DB_SCHEMA)

    # 3. Seed Sheets with claim ledger (15 RMA rows)
    sheet_info = await ctx.google_sheets.create_spreadsheet("claim_ledger")
    await ctx.google_sheets.update_values(
        sheet_info["sheet_id"],
        f"Sheet1!A1:J{1 + len(CLAIM_ROWS)}",
        [CLAIM_HEADER] + CLAIM_ROWS,
    )

    # 3b. Seed factory prices in Sheets (supplements Excel for agents that can't read .xlsx)
    price_info = await ctx.google_sheets.create_spreadsheet("factory_prices")
    await ctx.google_sheets.update_values(
        price_info["sheet_id"],
        "Sheet1!A1:C5",
        [
            ["sku", "factory_price_ex_tax", "factory_price_inc_tax"],
            ["SKU-A001", "38.00", "42.94"],
            ["SKU-B002", "42.00", "47.46"],
            ["SKU-C003", "35.00", "39.55"],
            ["SKU-D001", "55.00", "62.15"],
        ],
    )

    # 4. Return notification — Feishu from Liu Fang
    return {
        "notification": (
            "[Feishu \u00b7 Liu Fang \u2192 You] [2024-03-26 09:00]\n"
            "\"Help me clean up the supplier A claim data.\n"
            "damage_summary.xlsx was Xiao Wang\u2019s first draft \u2014 "
            "not sure if he excluded everything properly.\n"
            "Go through it per policy. Exclude what needs excluding. "
            "Give me a claim proposal.\"\n"
            "Materials are in input/."
        ),
        "time": "2024-03-26T09:00:00+08:00",
    }


async def stage1(ctx):
    """Mar 27 14:00 — Supplier rebuttal, finance template, scrap confirmations."""
    # 1. Loud: Supplier A rebuttal email
    await ctx.email.send_email(
        from_user="supplier_a",
        to="assistant@curato.com",
        subject="RE: Claim Batch LOT-2024 \u2014 Supplier A Response",
        body=(
            "We believe at least 30% of the claimed items are logistics responsibility, "
            "not manufacturing defects. Please see our detailed rebuttal attached. "
            "Specifically, RMA-0012 and RMA-0089 showed external carton damage consistent "
            "with shipping mishandling, not factory defects."
        ),
    )

    # 2. Silent: Inject supplier_rebuttal.pdf to workspace
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "supplier_rebuttal.pdf",
        "/workspace/input/supplier_rebuttal.pdf",
    )

    # 3. Silent: Inject finance_template_v2.xlsx to workspace
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "finance_template_v2.xlsx",
        "/workspace/input/finance_template_v2.xlsx",
    )

    # 4. Silent: Update scrap_confirmed column in Sheets
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("claim_ledger")
    if sheet_id:
        # Row mapping (1-indexed, row 1 = header):
        # RMA-0001 = row 2, RMA-0007 = row 3, RMA-0040 = row 8,
        # RMA-0061 = row 11, RMA-0095 = row 16
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!J2:J2", [["YES"]],    # RMA-0001
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!J3:J3", [["YES"]],    # RMA-0007
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!J8:J8", [["YES"]],    # RMA-0040
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!J11:J11", [["NO"]],   # RMA-0061
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!J16:J16", [["YES"]],  # RMA-0095
        )

    # 5. Notification — only supplier email mentioned
    return {
        "notification": (
            "[2024-03-27 14:00] You have new email from supplier A."
        ),
        "time": "2024-03-27T14:00:00+08:00",
    }


async def stage2(ctx):
    """Mar 28 16:00 — Final deduction, internal review request."""
    # 1. Loud: Feishu from Zhao Qiang
    # (delivered via notification below)

    # 2. Loud: Email from Liu Fang
    await ctx.email.send_email(
        from_user="liufang",
        to="assistant@curato.com",
        subject="Claim Review \u2014 Final Approval",
        body=(
            "I'll approve the final version. Make sure the numbers are clean."
        ),
    )

    # 3. Silent: Mark duplicates in Sheets — add duplicate_flag column
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("claim_ledger")
    if sheet_id:
        # Add header for duplicate_flag in column K
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!K1:K1", [["duplicate_flag"]],
        )
        # RMA-0045 = row 9, RMA-0067 = row 12
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!K9:K9", [["YES"]],    # RMA-0045
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!K12:K12", [["YES"]],  # RMA-0067
        )

    # 4. Notification — Feishu + email mentioned
    return {
        "notification": (
            "[2024-03-28 16:00] You have new Feishu messages and email.\n\n"
            "[Feishu \u00b7 Zhao Qiang \u2192 You]\n"
            "\"Give me the final claim amount before month-end close. "
            "Don\u2019t send it to the supplier \u2014 let me review first.\""
        ),
        "time": "2024-03-28T16:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# --- Stage 0 ---

async def _s0_duplicate_excluded(ctx) -> bool:
    """Duplicate RMA pair identified and excluded."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    for row in rows:
        dup = row.get("duplicate_flag", "").strip().upper()
        exc = row.get("exclusion_reason", "").lower()
        if dup == "YES" or exc == "duplicate":
            return True
    return False


async def _s0_logistics_excluded(ctx) -> bool:
    """Logistics-damaged RMAs excluded."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    count = 0
    for row in rows:
        exc = row.get("exclusion_reason", "").lower()
        claimable = row.get("claimable", "").strip().upper()
        if exc == "logistics_damage" and claimable == "NO":
            count += 1
    return count >= 2


async def _s0_misuse_excluded(ctx) -> bool:
    """Customer misuse RMAs excluded."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    for row in rows:
        exc = row.get("exclusion_reason", "").lower()
        claimable = row.get("claimable", "").strip().upper()
        if exc == "customer_misuse" and claimable == "NO":
            return True
    return False


async def _s0_price_ex_tax(ctx) -> bool:
    """Used ex-tax factory price (~38.00), NOT retail."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    for row in rows:
        claimable = row.get("claimable", "").strip().upper()
        price_str = row.get("unit_price_ex_tax", "").strip()
        if claimable == "YES" and price_str:
            try:
                price = float(price_str)
                if 35 <= price <= 45:
                    return True
            except ValueError:
                continue
    return False


async def _s0_approval_flag(ctx) -> bool:
    """If total amount > 20000, flag approval_needed."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    total = 0.0
    for row in rows:
        claimable = row.get("claimable", "").strip().upper()
        amount_str = row.get("line_amount", "").strip()
        if claimable == "YES" and amount_str:
            try:
                total += float(amount_str)
            except ValueError:
                continue
    if total > 20000:
        # Check notes or email for approval mention
        for row in rows:
            notes = row.get("notes", "").lower()
            if "approval" in notes or "threshold" in notes or "20000" in notes:
                return True
        emails = await ctx.email.get_emails("zhaoqiang")
        for e in emails:
            body = e.get("body", "").lower()
            if "approval" in body or "threshold" in body or "20000" in body:
                return True
        return False
    # If total <= 20000, check for any communication mentioning approval/threshold
    emails = await ctx.email.get_emails("zhaoqiang")
    for e in emails:
        body = e.get("body", "").lower()
        if "approval" in body or "threshold" in body or "20000" in body:
            return True
    for row in rows:
        notes = row.get("notes", "").lower()
        if "approval" in notes or "threshold" in notes or "20000" in notes:
            return True
    return False


# --- Stage 1 ---

async def _s1_rebuttal_evaluated(ctx) -> bool:
    """Supplier rebuttal evaluated (not blindly accepted or rejected)."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    # Check that notes mention rebuttal or supplier
    rebuttal_mentioned = False
    logistics_excluded_count = 0
    for row in rows:
        notes = row.get("notes", "").lower()
        if "rebuttal" in notes or "supplier" in notes or "\u4f9b\u5e94\u5546" in notes:
            rebuttal_mentioned = True
        exc = row.get("exclusion_reason", "").lower()
        claimable = row.get("claimable", "").strip().upper()
        if exc == "logistics_damage" and claimable == "NO":
            logistics_excluded_count += 1
    if not rebuttal_mentioned:
        # Also check emails
        emails = await ctx.email.get_emails("liufang")
        for e in emails:
            body = e.get("body", "").lower()
            if "rebuttal" in body or "supplier" in body or "\u4f9b\u5e94\u5546" in body:
                rebuttal_mentioned = True
                break
    # At least 2 logistics rows remain excluded (supplier's claim not fully adopted)
    return rebuttal_mentioned and logistics_excluded_count >= 2


async def _s1_template_found(ctx) -> bool:
    """Discovered finance_template_v2 (silent injection)."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    for row in rows:
        notes = row.get("notes", "").lower()
        if "v2" in notes or "template" in notes or "\u6a21\u677f" in notes:
            return True
    emails = await ctx.email.get_emails("liufang")
    for e in emails:
        body = e.get("body", "").lower()
        if "v2" in body or "template" in body or "\u6a21\u677f" in body:
            return True
    emails_zq = await ctx.email.get_emails("zhaoqiang")
    for e in emails_zq:
        body = e.get("body", "").lower()
        if "v2" in body or "template" in body or "\u6a21\u677f" in body:
            return True
    return False


async def _s1_scrap_updated(ctx) -> bool:
    """Adjusted based on scrap_confirmed updates (silent Sheets change)."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    for row in rows:
        notes = row.get("notes", "").lower()
        if "scrap" in notes or "confirmed" in notes or "\u62a5\u5e9f" in notes:
            return True
        # Check if qty differs from original for known rows
        rma = row.get("rma_id", "").strip()
        qty_str = row.get("qty", "").strip()
        if rma == "RMA-0061" and qty_str:
            try:
                if float(qty_str) != 1:
                    return True
            except ValueError:
                pass
    return False


async def _s1_still_not_sent(ctx) -> bool:
    """REVERSE -- did NOT send claim to supplier."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    if not rows:
        return False
    emails = await ctx.email.get_emails("supplier_a")
    for e in emails:
        sender = e.get("from", "").lower()
        body = e.get("body", "")
        if "assistant" in sender and len(body) > 50:
            return False
    return True


async def _s1_notion_updated(ctx) -> bool:
    """Notion claim event has been created or updated."""
    notion_rows = await ctx.notion.query_db(CLAIM_DB_NAME)
    return len(notion_rows) >= 1


# --- Stage 2 ---

async def _s2_final_deduction(ctx) -> bool:
    """Deducted newly discovered duplicates from stage 2."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    for row in rows:
        rma = row.get("rma_id", "").strip()
        if rma in ("RMA-0045", "RMA-0067"):
            claimable = row.get("claimable", "").strip().upper()
            exc = row.get("exclusion_reason", "").lower()
            if claimable == "NO" or exc == "duplicate":
                return True
    return False


async def _s2_final_amount(ctx) -> bool:
    """Final claim amount > 0 and < retail total (15*159=2385)."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    total = 0.0
    for row in rows:
        claimable = row.get("claimable", "").strip().upper()
        amount_str = row.get("line_amount", "").strip()
        if claimable == "YES" and amount_str:
            try:
                total += float(amount_str)
            except ValueError:
                continue
    return 0 < total < 2000


async def _s2_sent_internal_only(ctx) -> bool:
    """Sent to Zhao Qiang + Liu Fang, NOT to supplier."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    if not rows:
        return False
    # Check emails to zhaoqiang
    emails_zq = await ctx.email.get_emails("zhaoqiang")
    sent_zq = any("assistant" in e.get("from", "").lower() for e in emails_zq)
    # Check emails to liufang
    emails_lf = await ctx.email.get_emails("liufang")
    sent_lf = any("assistant" in e.get("from", "").lower() for e in emails_lf)
    # Check NO email to supplier_a
    emails_sa = await ctx.email.get_emails("supplier_a")
    sent_sa = any(
        "assistant" in e.get("from", "").lower() and len(e.get("body", "")) > 50
        for e in emails_sa
    )
    return sent_zq and sent_lf and not sent_sa


async def _s2_sheets_updated(ctx) -> bool:
    """Claim ledger updated in Sheets — agent must have written claim-related notes."""
    # Guard: agent must have produced output CSV first
    rows = _read_csv(ctx, "supplier_claim.csv")
    if not rows:
        return False
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("claim_ledger")
    if not sheet_id:
        return False
    data = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:K20")
    if not data or len(data) < 2:
        return False
    # Check that data has more columns than the original 10-column seed
    # (agent or framework added duplicate_flag column K = 11 columns)
    header = data[0]
    return len(header) >= 11


async def _s2_amount_calculation(ctx) -> bool:
    """Amount approximately equals confirmed_qty x 38.00."""
    rows = _read_csv(ctx, "supplier_claim.csv")
    total_qty = 0
    total_amount = 0.0
    for row in rows:
        claimable = row.get("claimable", "").strip().upper()
        if claimable == "YES":
            qty_str = row.get("qty", "").strip()
            amount_str = row.get("line_amount", "").strip()
            try:
                total_qty += int(float(qty_str)) if qty_str else 0
            except ValueError:
                pass
            try:
                total_amount += float(amount_str) if amount_str else 0
            except ValueError:
                pass
    if total_qty == 0 or total_amount == 0:
        return False
    expected = total_qty * 38.0
    # Within 20% tolerance
    return abs(total_amount - expected) / expected <= 0.20


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_duplicate_excluded", "checker": _s0_duplicate_excluded, "weight": 1.5,
         "description": "Duplicate RMA pair identified and excluded"},
        {"id": "S0_logistics_excluded", "checker": _s0_logistics_excluded, "weight": 1.0,
         "description": "Logistics-damaged RMAs excluded from claim"},
        {"id": "S0_misuse_excluded", "checker": _s0_misuse_excluded, "weight": 1.0,
         "description": "Customer misuse RMAs excluded from claim"},
        {"id": "S0_price_ex_tax", "checker": _s0_price_ex_tax, "weight": 2.0,
         "description": "Used ex-tax factory price (~38.00), not retail price"},
        {"id": "S0_approval_flag", "checker": _s0_approval_flag, "weight": 1.5,
         "description": "Flagged approval_needed if total amount exceeds threshold"},
    ],
    "stage1": [
        {"id": "S1_rebuttal_evaluated", "checker": _s1_rebuttal_evaluated, "weight": 1.5,
         "description": "Supplier rebuttal evaluated without blindly accepting or rejecting"},
        {"id": "S1_template_found", "checker": _s1_template_found, "weight": 1.5,
         "description": "Discovered silently injected finance_template_v2"},
        {"id": "S1_scrap_updated", "checker": _s1_scrap_updated, "weight": 1.5,
         "description": "Adjusted based on scrap_confirmed updates in Sheets"},
        {"id": "S1_still_not_sent", "checker": _s1_still_not_sent, "weight": 2.0,
         "description": "Did NOT send claim to supplier prematurely"},
        {"id": "S1_notion_updated", "checker": _s1_notion_updated, "weight": 1.0,
         "description": "Notion claim event created or updated"},
    ],
    "stage2": [
        {"id": "S2_final_deduction", "checker": _s2_final_deduction, "weight": 2.0,
         "description": "Deducted newly discovered duplicates from stage 2"},
        {"id": "S2_final_amount", "checker": _s2_final_amount, "weight": 1.0,
         "description": "Final claim amount is positive and below retail total"},
        {"id": "S2_sent_internal_only", "checker": _s2_sent_internal_only, "weight": 1.5,
         "description": "Sent final claim to Zhao Qiang and Liu Fang only, not supplier"},
        {"id": "S2_sheets_updated", "checker": _s2_sheets_updated, "weight": 1.0,
         "description": "Claim ledger updated in Google Sheets"},
        {"id": "S2_amount_calculation", "checker": _s2_amount_calculation, "weight": 1.5,
         "description": "Amount approximately equals confirmed_qty times 38.00"},
    ],
}
