"""Recall scope assessment & inventory freeze — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: scope assessment & freeze → supplier & lab follow-up → warehouse feedback
15 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

RECALL_DB_NAME = "recall_events"

RECALL_DB_SCHEMA = {
    "event_id": {"title": {}},
    "trigger": {"rich_text": {}},
    "affected_lots": {"rich_text": {}},
    "affected_skus": {"rich_text": {}},
    "supplier": {"rich_text": {}},
    "scope": {"select": {"options": [
        {"name": "warehouse"}, {"name": "shipped"}, {"name": "both"},
    ]}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "investigating"},
        {"name": "closed"},
    ]}},
    "freeze_status": {"select": {"options": [
        {"name": "pending"}, {"name": "frozen"}, {"name": "released"},
    ]}},
    "warehouse_status": {"select": {"options": [
        {"name": "none"}, {"name": "hold"}, {"name": "pulled"},
    ]}},
    "total_affected": {"number": {}},
    "total_shipped": {"number": {}},
    "created_date": {"rich_text": {}},
    "notes": {"rich_text": {}},
}

INVENTORY_HEADER = [
    "lot_id", "warehouse", "in_stock", "shipped", "frozen", "last_updated",
]
INVENTORY_ROWS = [
    ["lot-2024-03-A1", "wh-east", "120", "480", "0", "2024-03-18"],
    ["lot-2024-03-A1", "wh-south", "85", "315", "0", "2024-03-18"],
    ["lot-2024-03-A2", "wh-east", "200", "200", "0", "2024-03-18"],
    ["lot-2024-03-A2", "wh-south", "150", "250", "0", "2024-03-18"],
    ["lot-2024-03-A3", "wh-north", "300", "100", "0", "2024-03-18"],
    ["lot-2024-03-B1", "wh-east", "180", "220", "0", "2024-03-18"],
    ["lot-2024-03-B1", "wh-south", "160", "240", "0", "2024-03-18"],
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


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "ecommerce_task3",
    "name": "Recall Scope Assessment & Inventory Freeze",
    "category": "ecommerce",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhao Qiang's operations assistant at Curato",
    "tags": [
        "recall", "inventory", "freeze", "supplier",
        "multimodal", "lab-report", "cross-modal", "bom",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@curato.com",
                    "password": "assistant_pwd",
                },
                "zhaoqiang": {
                    "email": "zhaoqiang@curato.com",
                    "password": "zhaoqiang_pwd",
                },
                "supplier_a": {
                    "email": "supplier-a@curato.com",
                    "password": "supplier_a_pwd",
                },
                "lab": {
                    "email": "lab@curato.com",
                    "password": "lab_pwd",
                },
                "operations": {
                    "email": "operations@curato.com",
                    "password": "operations_pwd",
                },
                "wh_east": {
                    "email": "wh-east@curato.com",
                    "password": "wh_east_pwd",
                },
                "wh_south": {
                    "email": "wh-south@curato.com",
                    "password": "wh_south_pwd",
                },
                "wh_north": {
                    "email": "wh-north@curato.com",
                    "password": "wh_north_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "ecommerce_task3",
        },
    },
}

PROMPT = "Assess which product lots are affected by the lab findings and coordinate freeze actions."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-20: Scope assessment & freeze requests."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create empty Notion recall_events database
    await ctx.notion.create_page("Recall Events 2024-Q1")
    await ctx.notion.create_database(RECALL_DB_NAME, RECALL_DB_SCHEMA)

    # 3. Create Google Sheets inventory_status + seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet("inventory_status")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F8",
        [INVENTORY_HEADER] + INVENTORY_ROWS,
    )

    # 4. Notification — Feishu from Zhao Qiang + Slack context
    return {
        "notification": (
            "[2024-03-20 Wednesday 09:00] "
            "You have a Feishu message from Zhao Qiang.\n\n"
            "Your email: assistant@curato.com. "
            "Zhao Qiang: zhaoqiang@curato.com. "
            "Supplier A (Mingfeng): supplier-a@curato.com. "
            "Lab: lab@curato.com. "
            "Operations: operations@curato.com.\n"
            "Warehouse East: wh-east@curato.com. "
            "Warehouse South: wh-south@curato.com. "
            "Warehouse North: wh-north@curato.com.\n"
            "Recall tracking: Notion database 'recall_events'. "
            "Inventory: Google Sheets 'inventory_status'.\n\n"
            "[Feishu] Zhao Qiang: "
            "\"The lab report is in. There may be an issue with one of our "
            "products. Help me figure out which batches are affected — "
            "freeze what needs freezing, notify who needs notifying. "
            "Be careful not to over-scope or miss anything. "
            "Write your initial assessment to outputs/recall_scope.csv now — "
            "you can update it as new information comes in.\n"
            "Report is at input/lab_report.pdf, BOM specs at "
            "input/bom_spec.pdf. Dig through the rest of the data yourself.\"\n\n"
            "[Slack #quality-alerts] QC System (2024-03-15): "
            "\"lot-240302 return rate trending up — QC team is monitoring.\""
        ),
        "time": "2024-03-20T09:00:00+08:00",
    }


async def stage1(ctx):
    """2024-03-21 15:00: Supplier & lab follow-up."""
    # 1. Loud: Supplier A sends production log email
    await ctx.email.send_email(
        from_user="supplier_a",
        to="assistant@curato.com",
        subject="RE: Recall Inquiry — Production Records for A-Series",
        body=(
            "Hi,\n\n"
            "We've checked our records. The connector issue only affects "
            "the batch produced on 2024-03-07 on Line 3.\n\n"
            "Attached is the full production log.\n"
            "Please refer to /workspace/input/production_log.xlsx\n\n"
            "Regards,\nMingfeng Supply Chain"
        ),
    )

    # 2. Loud: Lab sends addendum email
    await ctx.email.send_email(
        from_user="lab",
        to="assistant@curato.com",
        subject="Addendum: Sample A3 S-004 — Transport Damage Assessment",
        body=(
            "Hi,\n\n"
            "Upon re-examination, sample A3 S-004 shows impact patterns "
            "consistent with transport damage rather than manufacturing defect. "
            "We recommend expanding the sample size for A3 before concluding.\n\n"
            "The addendum document is attached.\n"
            "Please refer to /workspace/input/addendum.pdf\n\n"
            "Regards,\nCurato Testing Lab"
        ),
    )

    # Upload injected files
    inject_dir = ctx.task_dir / "inject" / "stage1"
    await ctx.fs.upload_file(
        inject_dir / "production_log.xlsx",
        "/workspace/input/production_log.xlsx",
    )
    await ctx.fs.upload_file(
        inject_dir / "addendum.pdf",
        "/workspace/input/addendum.pdf",
    )

    # 3. Silent: A1 wh-east inventory changed (120 → 108, some shipped)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("inventory_status")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!C2", [["108"]],
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!D2", [["492"]],
        )

    # 4. Notification
    return {
        "notification": (
            "You have new emails from a supplier and the lab. "
            "Update outputs/recall_scope.csv with any new findings."
        ),
        "time": "2024-03-21T15:00:00+08:00",
    }


async def stage2(ctx):
    """2024-03-22 10:00: Warehouse feedback."""
    # 1. Loud: wh-east confirms freeze but 50 units already shipped
    await ctx.email.send_email(
        from_user="wh_east",
        to="assistant@curato.com",
        subject="RE: Freeze Request — A1 East Warehouse",
        body=(
            "Freeze completed for lot-2024-03-A1 and lot-2024-03-A2.\n\n"
            "However, 50 units of A1 were already dispatched yesterday "
            "before the freeze took effect.\n"
            "The shipped list is attached.\n"
            "Please refer to /workspace/input/shipped_list.csv\n\n"
            "Regards,\nEast Warehouse Team"
        ),
    )

    # 2. Loud: wh-south confirms freeze + mixed A2/B1 isolated
    await ctx.email.send_email(
        from_user="wh_south",
        to="assistant@curato.com",
        subject="RE: Freeze Request — South Warehouse",
        body=(
            "All A-series lots are frozen.\n"
            "Note: A2 and B1 were stored adjacent and some pallets got mixed. "
            "We've separated them with red tape markers. "
            "Both groups are now isolated.\n\n"
            "Regards,\nSouth Warehouse Team"
        ),
    )

    # 3. Silent: wh-north confirms A3 freeze (agent should discover)
    await ctx.email.send_email(
        from_user="wh_north",
        to="assistant@curato.com",
        subject="RE: Freeze Request — North Warehouse",
        body=(
            "A3 freeze completed. No anomalies observed.\n\n"
            "Regards,\nNorth Warehouse Team"
        ),
    )

    # Upload shipped_list.csv
    inject_dir = ctx.task_dir / "inject" / "stage2"
    await ctx.fs.upload_file(
        inject_dir / "shipped_list.csv",
        "/workspace/input/shipped_list.csv",
    )

    # 4. Notification — only mentions 2 loud emails
    return {
        "notification": (
            "You have new emails from the East and South warehouses. "
            "Update outputs/recall_scope.csv with the latest status."
        ),
        "time": "2024-03-22T10:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Scope Assessment & Freeze --


async def _s0_lab_scope(ctx):
    """A2 marked as lab_tested=NO in recall_scope.csv (conclusion vs table gap)."""
    rows = _read_csv(ctx, "recall_scope.csv")
    row = _find_csv_row(rows, "lot_id", "A2")
    if not row:
        return False
    return row.get("lab_tested", "").upper() == "NO"


async def _s0_ocr(ctx):
    """A1 lot_id correctly standardized (not 'l0t' OCR artifact)."""
    rows = _read_csv(ctx, "recall_scope.csv")
    row = _find_csv_row(rows, "lot_id", "A1")
    if not row:
        return False
    lot = row.get("lot_id", "")
    # Should contain "lot" (correct) not "l0t" (OCR error)
    return "l0t" not in lot.lower()


async def _s0_b1_excluded(ctx):
    """B1 marked as affected=NO (v2.0, interface looseness ≠ fracture)."""
    rows = _read_csv(ctx, "recall_scope.csv")
    row = _find_csv_row(rows, "lot_id", "B1")
    if not row:
        return False
    return row.get("affected", "").upper() == "NO"


async def _s0_snapshot_staleness(ctx):
    """Agent noted data staleness (inventory 48h old) and contacted warehouses."""
    # Agent should have contacted at least one warehouse to verify current stock
    east = await ctx.email.get_emails("wh_east")
    south = await ctx.email.get_emails("wh_south")
    if len(east) >= 1 or len(south) >= 1:
        return True
    # Or: CSV notes mention staleness substantially
    rows = _read_csv(ctx, "recall_scope.csv")
    for r in rows:
        if len(r.get("notes", "")) > 40:
            return True
    return False


async def _s0_freeze_requested(ctx):
    """Warehouses received freeze request emails for affected lots."""
    east = await ctx.email.get_emails("wh_east")
    south = await ctx.email.get_emails("wh_south")
    # A1+A2 are at east and south — both must receive freeze requests
    return len(east) >= 1 and len(south) >= 1


# -- S1: Supplier & Lab Follow-up --


async def _s1_mold_contradiction(ctx):
    """Agent identified mold contradiction: updated assessment AND challenged supplier."""
    # 1. CSV: A-series lot notes must be substantially updated
    rows = _read_csv(ctx, "recall_scope.csv")
    csv_updated = False
    for row in rows:
        lot = row.get("lot_id", "").upper()
        if "A1" in lot or "A2" in lot:
            if len(row.get("notes", "")) > 60:
                csv_updated = True
                break
    # 2. Email: supplier received substantive challenge (not just initial)
    emails = await ctx.email.get_emails("supplier_a")
    email_sent = any(len(e.get("body", "")) > 80 for e in emails)
    return csv_updated and email_sent


async def _s1_a3_reassessed(ctx):
    """A3 reassessed in CSV after lab addendum (affected ≠ YES)."""
    rows = _read_csv(ctx, "recall_scope.csv")
    row = _find_csv_row(rows, "lot_id", "A3")
    if not row:
        return False
    affected = row.get("affected", "").upper()
    return affected in ("PENDING", "NO")


async def _s1_inventory_change(ctx):
    """Agent noticed A1 wh-east inventory change (120→108)."""
    rows = _read_csv(ctx, "recall_scope.csv")
    row = _find_csv_row(rows, "lot_id", "A1")
    if row:
        try:
            qty = int(row.get("in_stock_qty", "0"))
            # If qty reflects the updated value (not original 120+85=205 or 120)
            if 100 <= qty <= 115:  # ~108 expected
                return True
        except (ValueError, TypeError):
            pass
        # Notes must be substantial (reflecting inventory change analysis)
        notes = row.get("notes", "")
        if len(notes) > 60:
            return True
    # Check Notion for inventory-related update mentioning A1
    notion_rows = await ctx.notion.query_db(RECALL_DB_NAME)
    for r in notion_rows:
        notes = _get_notion_field(r, "notes")
        lots = _get_notion_field(r, "affected_lots")
        if "A1" in lots.upper() and len(notes) > 60:
            return True
    return False


async def _s1_supplier_challenged(ctx):
    """Supplier A received ≥1 email from agent (pointing out contradiction)."""
    emails = await ctx.email.get_emails("supplier_a")
    for e in emails:
        if len(e.get("body", "")) > 50:
            return True
    return False


async def _s1_zhaoqiang_updated(ctx):
    """Zhao Qiang received at least 1 status update email."""
    emails = await ctx.email.get_emails("zhaoqiang")
    return len(emails) >= 1


# -- S2: Warehouse Feedback --


async def _s2_shipped_50(ctx):
    """Notion records the 50 already-shipped A1 units."""
    notion_rows = await ctx.notion.query_db(RECALL_DB_NAME)
    for row in notion_rows:
        lots = _get_notion_field(row, "affected_lots")
        notes = _get_notion_field(row, "notes")
        shipped = _get_notion_field(row, "total_shipped", "number")
        if "A1" in lots.upper() or "A1" in notes.upper():
            if shipped and shipped >= 50:
                return True
            if len(notes) > 20:
                return True
    # Or check recall_scope.csv
    rows = _read_csv(ctx, "recall_scope.csv")
    row = _find_csv_row(rows, "lot_id", "A1")
    if row:
        try:
            shipped = int(row.get("shipped_qty", "0"))
            if shipped >= 50:
                return True
        except ValueError:
            pass
    return False


async def _s2_proactive_recall(ctx):
    """Agent recommended proactive recall for shipped units."""
    # Check email to zhaoqiang or operations about recall recommendation
    for mailbox in ("zhaoqiang", "operations"):
        emails = await ctx.email.get_emails(mailbox)
        if len(emails) >= 1:
            for e in emails:
                if len(e.get("body", "")) > 100:
                    return True
    return False


async def _s2_all_warehouses(ctx):
    """All 3 warehouses accounted for in CSV or Notion."""
    rows = _read_csv(ctx, "recall_scope.csv")
    warehouses_csv = set()
    for r in rows:
        wh = r.get("warehouses", "").lower()
        if "east" in wh:
            warehouses_csv.add("east")
        if "south" in wh:
            warehouses_csv.add("south")
        if "north" in wh:
            warehouses_csv.add("north")
    if len(warehouses_csv) >= 3:
        return True
    # Check Notion
    notion_rows = await ctx.notion.query_db(RECALL_DB_NAME)
    warehouses_notion = set()
    for r in notion_rows:
        notes = _get_notion_field(r, "notes").lower()
        lots = _get_notion_field(r, "affected_lots").lower()
        for wh in ("east", "south", "north"):
            if wh in notes or wh in lots:
                warehouses_notion.add(wh)
    return len(warehouses_csv | warehouses_notion) >= 3


async def _s2_sheets_flow(ctx):
    """Sheets inventory_status reflects shipped/outflow data."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("inventory_status")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:F10")
    if not vals:
        return False
    # Check if frozen column or rows were updated from initial state
    for row in vals[1:]:
        if len(row) >= 5:
            try:
                frozen = int(row[4])
                if frozen > 0:
                    return True
            except (ValueError, IndexError):
                pass
    # Or check if new rows were added
    return len(vals) > 8


async def _s2_comprehensive_update(ctx):
    """Notion recall_events has comprehensive records (≥1 with notes)."""
    notion_rows = await ctx.notion.query_db(RECALL_DB_NAME)
    for r in notion_rows:
        notes = _get_notion_field(r, "notes")
        if len(notes) > 50:
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_lab_scope",
         "checker": _s0_lab_scope, "weight": 2.0},
        {"id": "S0_ocr",
         "checker": _s0_ocr, "weight": 1.0},
        {"id": "S0_b1_excluded",
         "checker": _s0_b1_excluded, "weight": 2.0},
        {"id": "S0_snapshot_staleness",
         "checker": _s0_snapshot_staleness, "weight": 1.5},
        {"id": "S0_freeze_requested",
         "checker": _s0_freeze_requested, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_mold_contradiction",
         "checker": _s1_mold_contradiction, "weight": 2.0},
        {"id": "S1_a3_reassessed",
         "checker": _s1_a3_reassessed, "weight": 1.5},
        {"id": "S1_inventory_change",
         "checker": _s1_inventory_change, "weight": 1.5},
        {"id": "S1_supplier_challenged",
         "checker": _s1_supplier_challenged, "weight": 1.0},
        {"id": "S1_zhaoqiang_updated",
         "checker": _s1_zhaoqiang_updated, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_shipped_50",
         "checker": _s2_shipped_50, "weight": 2.0},
        {"id": "S2_proactive_recall",
         "checker": _s2_proactive_recall, "weight": 1.5},
        {"id": "S2_all_warehouses",
         "checker": _s2_all_warehouses, "weight": 1.0},
        {"id": "S2_sheets_flow",
         "checker": _s2_sheets_flow, "weight": 1.0},
        {"id": "S2_comprehensive_update",
         "checker": _s2_comprehensive_update, "weight": 1.0},
    ],
}
