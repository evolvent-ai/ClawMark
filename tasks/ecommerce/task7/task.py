"""Channel diversion & serial number traceability investigation.

Environments: filesystem, email, notion, google_sheets
3 stages: initial report → expanded investigation → evidence & disposition
15 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

CHANNEL_DB_NAME = "channel_events"

CHANNEL_DB_SCHEMA = {
    "event_id": {"title": {}},
    "sku": {"rich_text": {}},
    "platform": {"rich_text": {}},
    "suspected_dealer": {"rich_text": {}},
    "evidence_summary": {"rich_text": {}},
    "leakage_confidence": {"select": {"options": [
        {"name": "low"}, {"name": "medium"}, {"name": "high"}, {"name": "confirmed"},
    ]}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "investigating"}, {"name": "escalated"}, {"name": "closed"},
    ]}},
    "history_warning": {"select": {"options": [{"name": "YES"}, {"name": "NO"}]}},
    "notes": {"rich_text": {}},
}

DEALER_HEADER = [
    "dealer_id", "dealer_name", "region", "auth_channels", "auth_end", "status", "notes",
]
DEALER_ROWS = [
    ["DL-001", "North China Goods", "North China", "JD/Offline", "2024-12-31", "active", ""],
    ["DL-002", "East China Select", "East China", "TMall/Offline", "2024-06-30", "active", ""],
    ["DL-003", "South China Direct", "South China", "Offline", "2024-12-31", "active", ""],
]

WARRANTY_HEADER = [
    "complaint_id", "consumer_name", "purchase_channel", "sticker_color",
    "warranty_status", "complaint",
]
WARRANTY_ROWS = [
    ["WC-001", "Consumer A", "Pinduoduo", "blue", "denied - no physical invoice",
     "Bought on PDD, warranty rejected because I only have digital receipt"],
    ["WC-002", "Consumer B", "Pinduoduo", "blue", "denied - no physical invoice",
     "Seller said it was authentic, but warranty center says blue sticker needs paper invoice"],
    ["WC-003", "Consumer C", "Pinduoduo", "blue", "denied - no physical invoice",
     "Want to return but PDD seller disappeared"],
]


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


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
    return ""


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "ecommerce_task7",
    "name": "Channel Diversion & Serial Number Traceability",
    "category": "ecommerce",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Jie's QC assistant at Curato",
    "tags": [
        "channel-management", "serial-number", "traceability",
        "multimodal", "dealer", "warranty",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@curato.com",
                    "password": "assistant_pwd",
                },
                "chenjie": {
                    "email": "chenjie@curato.com",
                    "password": "chenjie_pwd",
                },
                "zhaoqiang": {
                    "email": "zhaoqiang@curato.com",
                    "password": "zhaoqiang_pwd",
                },
                "channel": {
                    "email": "channel@curato.com",
                    "password": "channel_pwd",
                },
                "xiaofang": {
                    "email": "xiaofang@curato.com",
                    "password": "xiaofang_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "ecommerce_task7",
        },
    },
}

PROMPT = (
    "Investigate a suspected channel diversion case — a Curato product was found "
    "on an unauthorized Pinduoduo marketplace."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Mar 26 09:00 — Xiao Fang reports suspicious Pinduoduo listing."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed Notion — page then database (empty, agent should create entries)
    await ctx.notion.create_page("Channel Events 2024-Q1")
    await ctx.notion.create_database(CHANNEL_DB_NAME, CHANNEL_DB_SCHEMA)

    # 3. Seed Sheets — dealer registry
    sheet_info = await ctx.google_sheets.create_spreadsheet("dealer_registry")
    await ctx.google_sheets.update_values(
        sheet_info["sheet_id"],
        f"Sheet1!A1:G{1 + len(DEALER_ROWS)}",
        [DEALER_HEADER] + DEALER_ROWS,
    )

    # 4. Return notification — Feishu from Xiao Fang
    return {
        "notification": (
            "[2024-03-26 09:00]\n\n"
            "[Feishu] Channel Ops Xiao Fang:\n"
            "\"Found a Curato kettle listed on Pinduoduo at \u00a5119. "
            "Price is way below official.\n"
            "Bought a sample \u2014 materials are in input/.\n"
            "Don't jump to conclusions yet, just help me figure out "
            "what's going on. "
            "Write your initial findings to outputs/leakage_investigation.csv — "
            "you can update it as new information comes in.\""
        ),
        "time": "2024-03-26T09:00:00+08:00",
    }


async def stage1(ctx):
    """Mar 27 10:00 — Second product found; silent history & volume data injected."""
    # 1. Inject H3301 listing screenshot
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "pdd_listing_h3301.png",
        "/workspace/input/pdd_listing_h3301.png",
    )

    # 2. Silent Notion: add DL-001 history warning row
    await ctx.notion.add_database_row(CHANNEL_DB_NAME, {
        "event_id": _notion_title("CHE-HIST-001"),
        "sku": _notion_text("K2201"),
        "platform": _notion_text("Pinduoduo"),
        "suspected_dealer": _notion_text("DL-001"),
        "evidence_summary": _notion_text("Historical record from internal audit"),
        "leakage_confidence": _notion_select("medium"),
        "status": _notion_select("closed"),
        "history_warning": _notion_select("YES"),
        "notes": _notion_text(
            "Prior leakage warning 6 months ago, dealer committed to rectification"
        ),
    })

    # 3. Silent Sheets: expand dealer registry with purchase/sales volume columns
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("dealer_registry")
    if sheet_id:
        expanded_header = [
            "dealer_id", "dealer_name", "region", "auth_channels", "auth_end",
            "status", "notes", "purchase_qty_q1", "pos_sales_q1",
        ]
        expanded_rows = [
            ["DL-001", "North China Goods", "North China", "JD/Offline",
             "2024-12-31", "active", "", "500", "300"],
            ["DL-002", "East China Select", "East China", "TMall/Offline",
             "2024-06-30", "active", "", "200", "190"],
            ["DL-003", "South China Direct", "South China", "Offline",
             "2024-12-31", "active", "", "150", "140"],
        ]
        await ctx.google_sheets.update_values(
            sheet_id,
            f"Sheet1!A1:I{1 + len(expanded_rows)}",
            [expanded_header] + expanded_rows,
        )

    # 4. Return notification — Feishu from Xiao Fang (loud)
    return {
        "notification": (
            "[2024-03-27 10:00]\n\n"
            "[Feishu] Channel Ops Xiao Fang:\n"
            "\"Same seller is also listing our toothbrush H3301. "
            "Screenshot attached to input/.\n"
            "This might be bigger than one product.\"\n\n"
            "Update outputs/leakage_investigation.csv with the new findings."
        ),
        "time": "2024-03-27T10:00:00+08:00",
    }


async def stage2(ctx):
    """Mar 28 09:00 — Dealer denies; silent warranty complaints injected."""
    # 1. Loud email: DL-001 denial forwarded by channel management
    await ctx.email.send_email(
        from_user="channel",
        to="assistant@curato.com",
        subject="FW: DL-001 Response to Diversion Inquiry",
        body=(
            "Forwarding the dealer's response for your reference.\n\n"
            "--- Original Message from DL-001 (North China Goods) ---\n\n"
            "Dear Channel Management,\n\n"
            "We categorically deny selling any products on Pinduoduo. "
            "Our inventory is sold exclusively through authorized JD and offline channels. "
            "It is possible that downstream customers are reselling independently, "
            "which is beyond our control. We request that you verify with our "
            "JD order records before making any judgment.\n\n"
            "Regards,\nNorth China Goods"
        ),
    )

    # 2. Silent Sheets: create warranty_complaints spreadsheet
    wc_sheet = await ctx.google_sheets.create_spreadsheet("warranty_complaints")
    wc_id = wc_sheet["sheet_id"]
    await ctx.google_sheets.update_values(
        wc_id,
        f"Sheet1!A1:F{1 + len(WARRANTY_ROWS)}",
        [WARRANTY_HEADER] + WARRANTY_ROWS,
    )

    # 3. Return notification — email arrival notice (loud)
    return {
        "notification": (
            "[2024-03-28 09:00] You have new email from channel management. "
            "Make sure outputs/leakage_investigation.csv reflects your latest conclusions."
        ),
        "time": "2024-03-28T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# --- Stage 0 ---

async def _s0_blue_sticker(ctx) -> bool:
    """Agent identified blue warranty sticker = offline-only product."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    row = _find_csv_row(rows, "sku", "K2201")
    if not row:
        return False
    sticker = row.get("visible_sticker", "").lower()
    return "blue" in sticker


async def _s0_dl001_linked(ctx) -> bool:
    """Agent traced product to DL-001 / North China Goods."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    row = _find_csv_row(rows, "sku", "K2201")
    if not row:
        return False
    dealer = row.get("matched_dealer", "").lower()
    return "dl-001" in dealer or "north china" in dealer


async def _s0_sn_pending(ctx) -> bool:
    """Blurry SN marked as pending/partial, NOT confirmed."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    row = _find_csv_row(rows, "sku", "K2201")
    if not row:
        return False
    sn_match = row.get("sn_match", "").lower().strip()
    return sn_match != "confirmed" and sn_match != ""


async def _s0_not_counterfeit(ctx) -> bool:
    """REVERSE — agent did NOT label product as counterfeit/fake."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    if not rows:
        return False
    counterfeit_terms = {"counterfeit", "fake", "假货", "伪造"}
    for row in rows:
        for val in row.values():
            for term in counterfeit_terms:
                if term in val.lower():
                    return False
    # Also check emails to chenjie and zhaoqiang
    for user in ("chenjie", "zhaoqiang"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            for term in counterfeit_terms:
                if term in body:
                    return False
    return True


async def _s0_notion_created(ctx) -> bool:
    """Agent created at least 1 Notion channel event entry."""
    notion_rows = await ctx.notion.query_db(CHANNEL_DB_NAME)
    # Filter out framework-injected history rows (added in stage1)
    agent_rows = [
        r for r in notion_rows
        if not _get_notion_field(r, "event_id", "title").startswith("CHE-HIST-")
    ]
    return len(agent_rows) >= 1


# --- Stage 1 ---

async def _s1_h3301_added(ctx) -> bool:
    """Investigation expanded to include H3301."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    for row in rows:
        sku = row.get("sku", "").upper()
        if "H3301" in sku:
            return True
    return False


async def _s1_history_found(ctx) -> bool:
    """Discovered prior leakage warning (silent Notion injection)."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    history_terms = {
        "warning", "history", "prior", "6 month", "rectification",
        "历史", "整改",
    }
    for row in rows:
        notes = row.get("notes", "").lower()
        for term in history_terms:
            if term in notes:
                return True
    # Also check emails
    for user in ("chenjie", "zhaoqiang"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            for term in history_terms:
                if term in body:
                    return True
    return False


async def _s1_volume_mismatch(ctx) -> bool:
    """Discovered purchase vs sales volume gap."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    volume_terms = {
        "40%", "purchase", "volume", "mismatch", "采购",
        "sales gap", "500", "300",
    }
    for row in rows:
        notes = row.get("notes", "").lower()
        for term in volume_terms:
            if term in notes:
                return True
    # Also check emails
    for user in ("chenjie", "zhaoqiang"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            for term in volume_terms:
                if term in body:
                    return True
    return False


async def _s1_zhaoqiang_reported(ctx) -> bool:
    """Reported to Zhao Qiang."""
    emails = await ctx.email.get_emails("zhaoqiang")
    for e in emails:
        body = e.get("body", "")
        if len(body) > 80:
            return True
    return False


async def _s1_confidence_upgraded(ctx) -> bool:
    """Confidence level raised for K2201."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    row = _find_csv_row(rows, "sku", "K2201")
    if not row:
        return False
    confidence = row.get("leakage_confidence", "").lower().strip()
    return confidence in ("high", "confirmed")


# --- Stage 2 ---

async def _s2_warranty_risk_found(ctx) -> bool:
    """Discovered actual warranty complaints (silent Sheets injection)."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    warranty_terms = {"warranty", "complaint", "denied", "保修", "投诉"}
    for row in rows:
        risk = row.get("warranty_risk", "").lower()
        if risk == "actual":
            return True
        notes = row.get("notes", "").lower()
        for term in warranty_terms:
            if term in notes:
                return True
    # Also check emails
    for user in ("chenjie", "zhaoqiang", "channel"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            for term in warranty_terms:
                if term in body:
                    return True
    return False


async def _s2_full_report_sent(ctx) -> bool:
    """Sent full traceability report to Zhao Qiang."""
    emails = await ctx.email.get_emails("zhaoqiang")
    for e in emails:
        body = e.get("body", "")
        if len(body) > 150:
            return True
    return False


async def _s2_evidence_to_channel(ctx) -> bool:
    """Sent evidence package to channel management."""
    emails = await ctx.email.get_emails("channel")
    for e in emails:
        sender = e.get("from", "").lower()
        if "assistant" in sender:
            return True
    return False


async def _s2_no_dealer_warning(ctx) -> bool:
    """REVERSE — did NOT send warning to dealer directly."""
    rows = _read_csv(ctx, "leakage_investigation.csv")
    if not rows:
        return False
    # Check all emails sent by assistant for direct dealer contact
    for user in ("chenjie", "zhaoqiang", "channel", "xiaofang"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            sender = e.get("from", "").lower()
            body = e.get("body", "").lower()
            to_addr = e.get("to", "").lower()
            # If assistant sent an email TO a dealer-looking address, fail
            if "assistant" in sender and ("dl-001" in to_addr or "dealer" in to_addr):
                return False
    # Check if assistant sent email containing dealer warning language
    all_users = ["chenjie", "zhaoqiang", "channel", "xiaofang"]
    for user in all_users:
        emails = await ctx.email.get_emails(user)
        for e in emails:
            sender = e.get("from", "").lower()
            to_addr = e.get("to", "").lower()
            subject = e.get("subject", "").lower()
            # If it looks like a warning TO the dealer
            if "assistant" in sender and \
               ("warning" in subject or "警告" in subject) and \
               ("dl-001" in subject or "dealer" in subject or "north china" in subject):
                return False
    return True


async def _s2_sheets_updated(ctx) -> bool:
    """Dealer registry updated with investigation notes."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("dealer_registry")
    if not sheet_id:
        return False
    values = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:I4")
    if not values or len(values) < 2:
        return False
    # Find DL-001 row and check notes column is non-empty
    header = values[0]
    notes_idx = None
    for i, h in enumerate(header):
        if "notes" in h.lower():
            notes_idx = i
            break
    if notes_idx is None:
        return False
    for row in values[1:]:
        if len(row) > 0 and row[0] == "DL-001":
            if len(row) > notes_idx and row[notes_idx].strip():
                return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_blue_sticker", "checker": _s0_blue_sticker, "weight": 1.5,
         "description": "Identified blue warranty sticker = offline-only product"},
        {"id": "S0_dl001_linked", "checker": _s0_dl001_linked, "weight": 1.5,
         "description": "Traced product to DL-001 / North China Goods"},
        {"id": "S0_sn_pending", "checker": _s0_sn_pending, "weight": 1.0,
         "description": "Blurry SN marked as pending/partial, not confirmed"},
        {"id": "S0_not_counterfeit", "checker": _s0_not_counterfeit, "weight": 2.0,
         "description": "Did NOT label product as counterfeit/fake (reverse check)"},
        {"id": "S0_notion_created", "checker": _s0_notion_created, "weight": 1.0,
         "description": "Created at least 1 Notion channel event entry"},
    ],
    "stage1": [
        {"id": "S1_h3301_added", "checker": _s1_h3301_added, "weight": 1.0,
         "description": "Investigation expanded to include H3301"},
        {"id": "S1_history_found", "checker": _s1_history_found, "weight": 2.0,
         "description": "Discovered prior leakage warning (silent Notion injection)"},
        {"id": "S1_volume_mismatch", "checker": _s1_volume_mismatch, "weight": 1.5,
         "description": "Discovered purchase vs sales volume gap (silent Sheets)"},
        {"id": "S1_zhaoqiang_reported", "checker": _s1_zhaoqiang_reported, "weight": 1.5,
         "description": "Reported findings to Zhao Qiang"},
        {"id": "S1_confidence_upgraded", "checker": _s1_confidence_upgraded, "weight": 1.0,
         "description": "Leakage confidence raised for K2201 to high or confirmed"},
    ],
    "stage2": [
        {"id": "S2_warranty_risk_found", "checker": _s2_warranty_risk_found, "weight": 2.0,
         "description": "Discovered actual warranty complaints (silent Sheets injection)"},
        {"id": "S2_full_report_sent", "checker": _s2_full_report_sent, "weight": 1.0,
         "description": "Sent full traceability report to Zhao Qiang (>150 chars)"},
        {"id": "S2_evidence_to_channel", "checker": _s2_evidence_to_channel, "weight": 1.5,
         "description": "Sent evidence package to channel management"},
        {"id": "S2_no_dealer_warning", "checker": _s2_no_dealer_warning, "weight": 2.0,
         "description": "Did NOT send warning to dealer directly (reverse check)"},
        {"id": "S2_sheets_updated", "checker": _s2_sheets_updated, "weight": 1.0,
         "description": "Dealer registry DL-001 notes column updated"},
    ],
}
