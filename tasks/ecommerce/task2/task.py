"""Return dispute arbitration — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: initial arbitration → logistics reply & additions → legal handoff & daily summary
15 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

TICKET_DB_NAME = "service_tickets"

TICKET_DB_SCHEMA = {
    "ticket_id": {"title": {}},
    "order_id": {"rich_text": {}},
    "customer": {"rich_text": {}},
    "channel": {"select": {"options": [
        {"name": "JD"}, {"name": "Tmall"}, {"name": "Douyin"},
    ]}},
    "claim_type": {"select": {"options": [
        {"name": "Damage"}, {"name": "Missing Part"},
        {"name": "Defect"}, {"name": "Wrong Item"},
    ]}},
    "status": {"select": {"options": [
        {"name": "Pending Arbitration"}, {"name": "Approved"},
        {"name": "Rejected"}, {"name": "Forwarded"},
        {"name": "Pending Logistics"}, {"name": "Pending Legal"},
    ]}},
    "decision": {"rich_text": {}},
    "amount": {"number": {}},
    "handler": {"rich_text": {}},
    "created_date": {"rich_text": {}},
    "notes": {"rich_text": {}},
}

INITIAL_TICKETS = [
    {
        "ticket_id": "TICKET-0041",
        "order_id": "JD-20240302-11234",
        "customer": "Mr. Zhang",
        "channel": "JD",
        "claim_type": "Damage",
        "status": "Pending Arbitration",
        "amount": 189.00,
        "created_date": "2024-03-04",
    },
    {
        "ticket_id": "TICKET-0042",
        "order_id": "TM-20240228-55678",
        "customer": "Ms. Li",
        "channel": "Tmall",
        "claim_type": "Missing Part",
        "status": "Pending Arbitration",
        "amount": 159.00,
        "created_date": "2024-03-12",
    },
    {
        "ticket_id": "TICKET-0043",
        "order_id": "DY-20240310-77891",
        "customer": "Mr. Wang",
        "channel": "Douyin",
        "claim_type": "Defect",
        "status": "Pending Arbitration",
        "amount": 79.00,
        "created_date": "2024-03-12",
    },
    {
        "ticket_id": "TICKET-0044",
        "order_id": "JD-20240305-33456",
        "customer": "Ms. Zhao",
        "channel": "JD",
        "claim_type": "Wrong Item",
        "status": "Pending Arbitration",
        "amount": 199.00,
        "created_date": "2024-03-06",
    },
]

DISPUTE_LOG_HEADER = [
    "case_id", "order_id", "status", "decision", "amount", "handler",
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


async def _find_notion_ticket(ctx, ticket_id: str) -> dict | None:
    rows = await ctx.notion.query_db(TICKET_DB_NAME)
    for row in rows:
        tid = _get_notion_field(row, "ticket_id", "title")
        if tid == ticket_id:
            return row
    return None


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "ecommerce_task2",
    "name": "Return Dispute Arbitration",
    "category": "ecommerce",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Liu Fang's arbitration assistant at Curato",
    "tags": [
        "after-sales", "dispute", "arbitration", "returns",
        "multimodal", "cross-modal", "policy", "evidence",
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
                "logistics": {
                    "email": "logistics@curato.com",
                    "password": "logistics_pwd",
                },
                "legal": {
                    "email": "legal@curato.com",
                    "password": "legal_pwd",
                },
                "warehouse": {
                    "email": "warehouse@curato.com",
                    "password": "warehouse_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "ecommerce_task2",
        },
    },
}

PROMPT = "Review 4 escalated return dispute cases and make arbitration decisions."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-15: Process 4 escalated dispute cases."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion service_tickets database + seed 4 tickets
    await ctx.notion.create_page("Service Tickets 2024-Q1")
    await ctx.notion.create_database(TICKET_DB_NAME, TICKET_DB_SCHEMA)
    for t in INITIAL_TICKETS:
        await ctx.notion.add_database_row(TICKET_DB_NAME, {
            "ticket_id": _notion_title(t["ticket_id"]),
            "order_id": _notion_text(t["order_id"]),
            "customer": _notion_text(t["customer"]),
            "channel": _notion_select(t["channel"]),
            "claim_type": _notion_select(t["claim_type"]),
            "status": _notion_select(t["status"]),
            "amount": _notion_number(t["amount"]),
            "created_date": _notion_text(t["created_date"]),
        })

    # 3. Create Google Sheets dispute_log (empty with headers)
    sheet_info = await ctx.google_sheets.create_spreadsheet("dispute_log")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F1", [DISPUTE_LOG_HEADER],
    )

    # 4. Seed email from Liu Fang
    await ctx.email.send_email(
        from_user="liufang",
        to="assistant@curato.com",
        subject="4 Escalated Return Disputes",
        body=(
            "These 4 dispute cases were escalated from customer service "
            "— they couldn't handle them.\n"
            "Evidence files are in the cases/ folder, policies in ref/.\n"
            "Please process them and update the ticket status when done."
        ),
    )

    # 5. Notification
    return {
        "notification": (
            "[2024-03-15 Friday] You have a new email from Liu Fang "
            "(After-Sales Supervisor) and a Feishu message.\n\n"
            "Your email: assistant@curato.com. "
            "Liu Fang: liufang@curato.com. "
            "Logistics: logistics@curato.com. "
            "Legal: legal@curato.com. "
            "Warehouse: warehouse@curato.com.\n"
            "Ticket tracking: Notion database 'service_tickets'. "
            "Dispute log: Google Sheets 'dispute_log'.\n\n"
            "[Feishu] Liu Fang: "
            "\"These 4 return dispute tickets were escalated from CS — "
            "they couldn't resolve them. Please review each case individually. "
            "Approve the valid returns, reject the invalid ones with clear reasoning, "
            "and forward any cases needing logistics or legal involvement. "
            "Policy is in ref/return_policy.pdf — pay attention to the appendices. "
            "Evidence is in each case folder under input/cases/. "
            "Update the ticket status when done. "
            "Write your decisions to outputs/dispute_resolution.csv as you go — "
            "you can update it later when new information comes in.\"\n\n"
            "[Feishu] Xiao Wang (Warehouse): "
            "\"For case 041 — the warehouse says the kettle does have a crack, "
            "but photo_2 seems like it got mixed up with another item.\""
        ),
        "time": "2024-03-15T09:00:00+08:00",
    }


async def stage1(ctx):
    """2024-03-17: Logistics reply + additions."""
    # 1. Loud: Logistics (Yunda) confirms delivery — EXIF contradiction = forgery
    await ctx.email.send_email(
        from_user="logistics",
        to="assistant@curato.com",
        subject="RE: Case 041 — Delivery Confirmation",
        body=(
            "Hi,\n\n"
            "GPS tracking confirms the package for order JD-20240302-11234 "
            "was delivered and signed for on 2024-03-03 at 10:15.\n\n"
            "The delivery confirmation document is attached.\n"
            "Please refer to /workspace/input/cases/delivery_confirmation.pdf\n\n"
            "Regards,\nYunda Express"
        ),
    )

    # Upload delivery confirmation
    inject_dir = ctx.task_dir / "inject" / "stage1"
    await ctx.fs.upload_file(
        inject_dir / "delivery_confirmation.pdf",
        "/workspace/input/cases/delivery_confirmation.pdf",
    )

    # 2. Loud: Feishu from Xiao Wang about case 042
    # (included in notification)

    # 3. Silent: Case 043 HW-H3301 return rate jumped 0.5% → 3.2%
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("dispute_log")
    if sheet_id:
        # Add a hidden return-rate row that agent should discover
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!H1:J1",
            [["sku", "prev_return_rate", "curr_return_rate"]],
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!H2:J2",
            [["HW-H3301", "0.5%", "3.2%"]],
        )

    # 4. Silent: Case 042 customer has 8 returns in 6 months
    ticket_042 = await _find_notion_ticket(ctx, "TICKET-0042")
    if ticket_042:
        await ctx.notion.update_db_row(ticket_042["id"], {
            "notes": _notion_text(
                "Customer history: 8 return requests in the past 6 months"
            ),
        })

    # 5. Notification
    return {
        "notification": (
            "[2024-03-17 Sunday] You have new email and Feishu messages.\n\n"
            "[Feishu] Xiao Wang (Warehouse): "
            "\"About case 042 — Ms. Li says the thermometer compartment "
            "in the box was indeed empty. Could you check if there was "
            "a packing error on the warehouse side?\"\n\n"
            "Remember to update outputs/dispute_resolution.csv with your latest decisions."
        ),
        "time": "2024-03-17T09:00:00+08:00",
    }


async def stage2(ctx):
    """2024-03-18 17:30: Legal handoff + daily summary."""
    # 1. Loud: Feishu about case 041 threatening 12315 complaint
    # (included in notification)

    # 2. Loud: Warehouse confirms case 044 was wrong color
    await ctx.email.send_email(
        from_user="warehouse",
        to="assistant@curato.com",
        subject="RE: Case 044 — Color Verification",
        body=(
            "Confirmed: order JD-20240305-33456 was supposed to be Light Gray "
            "but we shipped White by mistake. Our fault.\n\n"
            "We can arrange an exchange shipment immediately."
        ),
    )

    # 3. Silent: Case 043 retention period expires today
    ticket_043 = await _find_notion_ticket(ctx, "TICKET-0043")
    if ticket_043:
        await ctx.notion.update_db_row(ticket_043["id"], {
            "notes": _notion_text(
                "Evidence retention period expires 2024-03-18. "
                "Customer history: 8 return requests in the past 6 months. "
                "HW-H3301 return rate spiked from 0.5% to 3.2%."
            ),
        })

    # 4. Notification — it's late afternoon
    return {
        "notification": (
            "[2024-03-18 Monday 17:30] New Feishu messages and email. "
            "It's almost end of day.\n\n"
            "[Feishu] Xiao Wang (Warehouse): "
            "\"Case 041 — Mr. Zhang says he's going to file a 12315 complaint.\"\n"
            "[Feishu] Liu Fang: "
            "\"If 041 is escalating to 12315, hand it to legal immediately "
            "with the full evidence chain.\"\n\n"
            "Make sure outputs/dispute_resolution.csv reflects your final decisions."
        ),
        "time": "2024-03-18T17:30:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Initial Arbitration --


async def _s0_041_time_conflict(ctx):
    """Case 041: EXIF vs sign date contradiction noted."""
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "041")
    if not row:
        return False
    anomalies = row.get("anomalies", "").lower()
    evidence = row.get("evidence_summary", "").lower()
    combined = anomalies + " " + evidence
    # Must mention date/EXIF-related terms, not just have long text
    date_terms = ("exif", "date", "03-02", "03-03", "timestamp", "sign", "时间")
    return len(anomalies) > 20 and any(t in combined for t in date_terms)


async def _s0_041_photo_excluded(ctx):
    """Case 041: warehouse_photo_2 SN mismatch identified and excluded."""
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "041")
    if not row:
        return False
    evidence = row.get("evidence_summary", "").lower()
    anomalies = row.get("anomalies", "").lower()
    combined = anomalies + " " + evidence
    # Must mention photo/SN-related terms
    sn_terms = ("photo", "serial", "sn", "mismatch", "warehouse", "0128", "不匹配")
    return len(evidence) > 30 and any(t in combined for t in sn_terms)


async def _s0_043_not_rejected(ctx):
    """Case 043: quality defect (§5.1) takes precedence over Appendix C."""
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "043")
    if not row:
        return False
    decision = row.get("decision", "").lower()
    return decision != "rejected"


async def _s0_041_pending(ctx):
    """Case 041: marked as pending (needs logistics verification)."""
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "041")
    if not row:
        return False
    decision = row.get("decision", "").lower()
    return decision in ("pending_logistics", "pending")


async def _s0_logistics_notified(ctx):
    """Logistics received at least 1 email about case 041."""
    emails = await ctx.email.get_emails("logistics")
    return len(emails) >= 1


# -- S1: Logistics Reply & Additions --


async def _s1_041_rejected(ctx):
    """Case 041: after logistics confirmation, EXIF forgery → rejected."""
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "041")
    if not row:
        return False
    decision = row.get("decision", "").lower()
    return decision == "rejected"


async def _s1_042_not_full_refund(ctx):
    """Case 042: 7-day window exceeded + old listing → should NOT be full_refund."""
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "042")
    if not row:
        return False
    decision = row.get("decision", "").lower()
    # 042 has >7 day return window violation — full_refund is incorrect
    return decision in ("rejected", "partial_refund", "pending")


async def _s1_043_trend_found(ctx):
    """Agent noticed HW-H3301 return rate spike (0.5% → 3.2%)."""
    # Check Notion ticket 043 — but exclude framework-seeded content
    # (Stage 2 seeds "HW-H3301 return rate spiked from 0.5% to 3.2%")
    FRAMEWORK_SEED = "hw-h3301 return rate spiked from 0.5%"
    ticket = await _find_notion_ticket(ctx, "TICKET-0043")
    if ticket:
        notes = _get_notion_field(ticket, "notes")
        notes_lower = notes.lower()
        trend_terms = ("rate", "spike", "3.2", "return", "trend", "退货率", "上升")
        # Only pass if notes are longer than framework seed (agent added content)
        if (len(notes) > 130 and any(t in notes_lower for t in trend_terms)
                and FRAMEWORK_SEED not in notes_lower[:60]):
            return True
    # Check CSV reason/anomalies for 043
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "043")
    if row:
        reason = row.get("reason", "")
        anomalies = row.get("anomalies", "")
        if len(reason) > 30 and len(anomalies) > 10:
            return True
    return False


async def _s1_044_full_refund(ctx):
    """Case 044: clear color mismatch (warehouse error) → full_refund."""
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "044")
    if not row:
        return False
    decision = row.get("decision", "").lower()
    return decision == "full_refund"


async def _s1_notion_updated(ctx):
    """At least 2 Notion tickets no longer 'Pending Arbitration'."""
    rows = await ctx.notion.query_db(TICKET_DB_NAME)
    updated = sum(
        1 for r in rows
        if _get_notion_field(r, "status", "select") != "Pending Arbitration"
    )
    return updated >= 2


# -- S2: Legal Handoff & Daily Summary --


async def _s2_041_to_legal(ctx):
    """Legal received email about case 041 with evidence (body > 200 chars)."""
    emails = await ctx.email.get_emails("legal")
    for e in emails:
        if len(e.get("body", "")) > 200:
            return True
    return False


async def _s2_041_legal_status(ctx):
    """Notion TICKET-0041 status is 'Pending Legal' or 'Forwarded'."""
    ticket = await _find_notion_ticket(ctx, "TICKET-0041")
    if not ticket:
        return False
    status = _get_notion_field(ticket, "status", "select").lower()
    return status in ("pending legal", "forwarded")


async def _s2_043_retention_noted(ctx):
    """Agent noticed case 043 retention period expiry."""
    # Check CSV: 043 next_action + reason should reflect retention urgency
    rows = _read_csv(ctx, "dispute_resolution.csv")
    row = _find_csv_row(rows, "case_id", "043")
    if row:
        next_act = row.get("next_action", "")
        reason = row.get("reason", "")
        combined = (next_act + " " + reason).lower()
        retention_terms = ("retention", "expir", "03-18", "preserve", "evidence",
                           "保全", "到期")
        if len(next_act) > 15 and any(t in combined for t in retention_terms):
            return True
    # Check emails to liufang for retention mention
    emails = await ctx.email.get_emails("liufang")
    for e in emails:
        body = e.get("body", "").lower()
        retention_terms = ("retention", "expir", "03-18", "preserve", "保全", "到期")
        if len(body) > 50 and any(t in body for t in retention_terms):
            return True
    return False


async def _s2_daily_summary(ctx):
    """End-of-day summary contains numerical data (sent via email)."""
    emails = await ctx.email.get_emails("liufang")
    for e in emails:
        body = e.get("body", "")
        if len(body) > 100 and any(c.isdigit() for c in body):
            return True
    return False


async def _s2_sheets_updated(ctx):
    """Sheets dispute_log has ≥4 rows (all 4 cases logged)."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("dispute_log")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:F10")
    if not vals:
        return False
    # Header + at least 4 data rows
    return len(vals) >= 5


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_041_time_conflict", "checker": _s0_041_time_conflict,
         "weight": 2.0, "description": "Detected EXIF vs sign-date contradiction for case 041"},
        {"id": "S0_041_photo_excluded", "checker": _s0_041_photo_excluded,
         "weight": 1.5, "description": "Identified warehouse_photo_2 SN mismatch and excluded it"},
        {"id": "S0_043_not_rejected", "checker": _s0_043_not_rejected,
         "weight": 2.0, "description": "Did NOT reject case 043 — quality defect §5.1 overrides Appendix C"},
        {"id": "S0_041_pending", "checker": _s0_041_pending,
         "weight": 1.0, "description": "Marked case 041 as pending logistics verification"},
        {"id": "S0_logistics_notified", "checker": _s0_logistics_notified,
         "weight": 1.0, "description": "Sent email to logistics requesting delivery confirmation"},
    ],
    "stage1": [
        {"id": "S1_041_rejected", "checker": _s1_041_rejected,
         "weight": 2.0, "description": "Rejected case 041 after delivery confirmation exposed EXIF forgery"},
        {"id": "S1_042_not_full_refund", "checker": _s1_042_not_full_refund,
         "weight": 1.5, "description": "Case 042 NOT full_refund — 7-day return window violated"},
        {"id": "S1_043_trend_found", "checker": _s1_043_trend_found,
         "weight": 1.5, "description": "Discovered HW-H3301 return rate spike from silent Sheets injection"},
        {"id": "S1_044_full_refund", "checker": _s1_044_full_refund,
         "weight": 1.5, "description": "Case 044 awarded full_refund — clear warehouse color error"},
        {"id": "S1_notion_updated", "checker": _s1_notion_updated,
         "weight": 1.0, "description": "At least 2 Notion tickets updated from Pending Arbitration"},
    ],
    "stage2": [
        {"id": "S2_041_to_legal", "checker": _s2_041_to_legal,
         "weight": 2.0, "description": "Forwarded case 041 to legal with full evidence package"},
        {"id": "S2_041_legal_status", "checker": _s2_041_legal_status,
         "weight": 1.0, "description": "Notion TICKET-0041 status updated to Pending Legal"},
        {"id": "S2_043_retention_noted", "checker": _s2_043_retention_noted,
         "weight": 1.5, "description": "Noticed case 043 evidence retention period expiring 2024-03-18"},
        {"id": "S2_daily_summary", "checker": _s2_daily_summary,
         "weight": 1.0, "description": "Sent end-of-day summary to Liu Fang with numerical data"},
        {"id": "S2_sheets_updated", "checker": _s2_sheets_updated,
         "weight": 1.0, "description": "All 4 cases logged in dispute_log spreadsheet"},
    ],
}
