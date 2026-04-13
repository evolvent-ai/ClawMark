"""Property hidden defect dispute — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: evidence review → supplemental evidence → demand letter preparation
13 core checkers (0 keyword-search)
"""
import csv
from io import StringIO
from datetime import datetime

# ── Constants ─────────────────────────────────────────────────────

CASE_DB_NAME = "case_management"

CASE_DB_SCHEMA = {
    "case_id": {"title": {}},
    "case_name": {"rich_text": {}},
    "status": {
        "select": {
            "options": [
                {"name": "Active"},
                {"name": "Under Review"},
                {"name": "Pending"},
                {"name": "Closed"},
            ]
        }
    },
    "assigned_to": {"rich_text": {}},
    "parties": {"rich_text": {}},
    "notes": {"rich_text": {}},
}

CALENDAR_NAME = "RE2024-021"
INITIAL_NOTION_NOTES = "Case opened. Evidence verification pending."

REPAIR_SHEET_HEADER = ["item", "vendor", "quote_cny", "notes"]
REPAIR_SHEET_ROWS_S1 = [
    ["Waterproofing redo", "Shanghai Waterproof Co.", "150000", "Full bathroom/kitchen redo + ceiling"],
    ["Wall repair", "Jintian Renovation", "30000", "Living room + bedroom walls"],
    ["Ceiling repair", "Jintian Renovation", "8000", "Ceiling plaster and repaint"],
]


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}

def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}

def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}

def _read_csv(ctx, filename: str) -> list[dict]:
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []

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
    return ""


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "legal_assistant_task4",
    "name": "Property Hidden Defect Dispute Investigation",
    "category": "legal_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Xiao, legal assistant to Attorney Li Lei",
    "tags": [
        "property_dispute", "hidden_defect", "visual_comparison",
        "concealment_evidence", "repair_records", "demand_letter",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@lawfirm.com",
                    "password": "assistant_pwd",
                },
                "lilei": {
                    "email": "li.lei@lawfirm.com",
                    "password": "lilei_pwd",
                },
                "seller_zhang": {
                    "email": "zhangjg1975@163.com",
                    "password": "zhang_pwd",
                },
                "property_mgmt": {
                    "email": "property_mgmt@nanjingeastrd.com",
                    "password": "property_pwd",
                },
                "chenming": {
                    "email": "chenming0615@qq.com",
                    "password": "chenming_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "legal_assistant_task4",
        },
    },
}

PROMPT = "Check your email, Feishu messages, and workspace for the property defect case files to review."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-18 09:15: Environment setup — photos, records, contract, CRM, calendar."""

    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    await ctx.notion.create_page("Property Dispute Cases 2024")
    await ctx.notion.create_database(CASE_DB_NAME, CASE_DB_SCHEMA)
    await ctx.notion.add_database_row(CASE_DB_NAME, {
        "case_id": _notion_title("RE2024-021"),
        "case_name": _notion_text("Chen Ming vs. Zhang Jianguo — Property Defect Dispute"),
        "status": _notion_select("Active"),
        "assigned_to": _notion_text("Chen Xiao"),
        "parties": _notion_text("Plaintiff: Chen Ming | Defendant: Zhang Jianguo (Seller)"),
        "notes": _notion_text(INITIAL_NOTION_NOTES),
    })

    # Empty repair quotes (data arrives in Stage 1)
    sheet_info = await ctx.google_sheets.create_spreadsheet("Repair Market Quotes")
    await ctx.google_sheets.update_values(
        sheet_info["sheet_id"], "Sheet1!A1:D1", [REPAIR_SHEET_HEADER],
    )

    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Court Hearing - RE2024-021",
        dtstart=datetime(2024, 4, 8, 9, 0),
        dtend=datetime(2024, 4, 8, 12, 0),
        description="Court hearing for property defect dispute RE2024-021",
    )

    # Seed emails
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="RE2024-021 Property Defect Dispute - Task Assignment",
        body=(
            "Chen Xiao,\n\nAll materials for the property defect dispute case have arrived. "
            "Focus on comparing listing photos with current condition for concealment evidence. "
            "Cross-check property repair records with contract declarations.\n"
            "Organize the evidence list and notify me immediately.\n\nLi Lei"
        ),
    )

    await ctx.email.send_email(
        from_user="seller_zhang",
        to="li.lei@lawfirm.com",
        subject="Re: Regarding Property Sale Dispute",
        body=(
            "Attorney Li,\n\nThere was absolutely no water leakage when I sold the property. "
            "Everything was normal. The buyer cannot produce evidence that I concealed anything. "
            "I lived there 6 years and it was always fine. They probably damaged something "
            "during their own renovation.\n\nZhang Jianguo"
        ),
    )

    await ctx.email.send_email(
        from_user="chenming",
        to="assistant@lawfirm.com",
        subject="Property Evidence Materials",
        body=(
            "Assistant Chen,\n\nThe property management told me this unit had serious water "
            "leakage before. I obtained the repair records. Also, the renovation team said "
            "the mold inside the walls is very serious, obviously covered up with fresh paint. "
            "They took photos when they removed the wall sections.\n\nChen Ming"
        ),
    )

    return {
        "notification": (
            "[2024-03-18 Monday 09:15]\n"
            "You have 3 new emails in your inbox.\n\n"
            "Feishu message from Li Lei:\n"
            '"Property defect dispute case files are in CRM. Focus on comparing listing photos '
            "with current condition for concealment evidence. Cross-check property repair records "
            'with contract declarations. Organize evidence list, notify me of key issues."'
        ),
        "time": "2024-03-18T09:15:00+08:00",
    }


async def stage1(ctx):
    """2024-03-20 10:00: Supplemental evidence — neighbor statement + repair order."""

    inject_dir = ctx.task_dir / "inject" / "stage1"
    await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    # Loud: Property management sends repair order confirmation
    await ctx.email.send_email(
        from_user="property_mgmt",
        to="assistant@lawfirm.com",
        subject="RE2024-021 - Repair Records Confirmation",
        body=(
            "Regarding the repair records for the property in question, we confirm "
            "all records are authentic and valid. We can provide written certification.\n\n"
            "Additionally, we located the original 2021 repair work order "
            "(repair_order_2021.pdf). The owner's signature is clearly visible on it.\n\n"
            "Property Management Office\nNanjing East Road Complex"
        ),
    )

    # Silent: Update Google Sheets — repair quotes arrive
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Repair Market Quotes")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A2:D4", REPAIR_SHEET_ROWS_S1,
        )

    # Silent: Opposing party retained attorney (update CRM)
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "RE2024-021" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Seller Zhang Jianguo has retained attorney. "
                    "Opposing counsel questioning admissibility of property repair records."
                ),
            })
            break

    return {
        "notification": (
            "[2024-03-20 Wednesday 10:00]\n"
            "You have a new email from Property Management.\n\n"
            "Feishu message from Chen Ming:\n"
            '"My upstairs neighbor says his unit also leaks on the same wall. '
            "He's willing to testify in court. I sent you his statement "
            '(neighbor_statement.pdf)."'
        ),
        "time": "2024-03-20T10:00:00+08:00",
    }


async def stage2(ctx):
    """2024-03-22 11:00: Demand letter preparation — blueprint + intermediary question."""

    inject_dir = ctx.task_dir / "inject" / "stage2"
    if inject_dir.exists():
        await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="RE: RE2024-021 - Draft Demand Letter",
        body=(
            "Evidence chain is solid. Draft a demand letter to seller Zhang:\n"
            "- List fraud facts\n- Demand resolution within 15 days\n"
            "- Otherwise we file suit\n\n"
            "Also compile the claim amounts including repair costs and price difference loss.\n\n"
            "— Li Lei"
        ),
    )

    # Silent: Chen Ming sends blueprint through CRM
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "RE2024-021" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Client uploaded original construction blueprint (blueprint_scan.jpg). "
                    "Shows water pipes above Unit 1502 living room area. "
                    "Opposing counsel retained and challenging evidence admissibility."
                ),
            })
            break

    return {
        "notification": (
            "[2024-03-22 Friday 11:00]\n"
            "You have a new email from Li Lei.\n\n"
            "Feishu message from Li Lei:\n"
            '"Evidence chain is solid. Draft a demand letter to seller Zhang. '
            "Compile claim amounts from the repair quotes sheet.\"\n\n"
            "Feishu message from Chen Ming:\n"
            '"When I bought this property, the real estate agent was present too. '
            "Does the agent have any liability? I asked them about water leakage at the "
            "time and they said there was none. Does that count as complicity?\"\n\n"
            "[Developer's original blueprint uploaded to CRM: blueprint_scan.jpg]"
        ),
        "time": "2024-03-22T11:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

async def _s0_outputs_exist(ctx) -> bool:
    """defect_evidence.csv and timeline_comparison.md exist."""
    csv_ok = any(
        (b / "defect_evidence.csv").exists()
        for b in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    md_ok = any(
        (b / "timeline_comparison.md").exists()
        for b in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    return csv_ok and md_ok


async def _s0_repair_mark_noted(ctx) -> bool:
    """CSV has listing_photo row with concealment_evidence or visual_comparison finding."""
    rows = _read_csv(ctx, "defect_evidence.csv")
    row = _find_csv_row(rows, "source_file", "listing_photo")
    if not row:
        return False
    strength = row.get("evidence_strength", "").strip().upper()
    return strength in ("STRONG", "MEDIUM")


async def _s0_cross_section_noted(ctx) -> bool:
    """CSV has wall_cross_section row with structural_defect or concealment_evidence finding."""
    rows = _read_csv(ctx, "defect_evidence.csv")
    row = _find_csv_row(rows, "source_file", "wall_cross_section")
    if not row:
        return False
    finding = row.get("finding_type", "").strip().lower()
    return finding in ("concealment_evidence", "structural_defect", "visual_comparison")


async def _s0_complaint_contradiction(ctx) -> bool:
    """CSV has property_complaint row noting contradiction with contract declaration."""
    rows = _read_csv(ctx, "defect_evidence.csv")
    row = _find_csv_row(rows, "source_file", "property_complaint")
    if not row:
        row = _find_csv_row(rows, "finding_type", "repair_history")
    return row is not None


async def _s0_case_notes_updated(ctx) -> bool:
    """CRM notes differ from initial value."""
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "RE2024-021" in case_id:
            notes = _get_notion_field(row, "notes", "rich_text")
            return notes != INITIAL_NOTION_NOTES and len(notes) > 10
    return False


async def _s0_lawyer_notified(ctx) -> bool:
    """Li Lei received at least 2 emails (framework seeds 1 from seller; agent should send 1+)."""
    emails = await ctx.email.get_emails("lilei")
    return len(emails) >= 2


# --- Stage 1 ---

async def _s1_repair_order_noted(ctx) -> bool:
    """CSV has repair_order_2021 row — seller signature identified."""
    rows = _read_csv(ctx, "defect_evidence.csv")
    row = _find_csv_row(rows, "source_file", "repair_order")
    return row is not None


async def _s1_repair_cost_discovered(ctx) -> bool:
    """Agent discovered repair quotes (150000 or 30000) from silent Sheets update."""
    for fname in ["defect_evidence.csv", "claim_summary.csv"]:
        rows = _read_csv(ctx, fname)
        for row in rows:
            for val in row.values():
                s = str(val).replace(",", "")
                if "150000" in s or "30000" in s:
                    return True
    return False


# --- Stage 2 ---

async def _s2_claim_summary_exists(ctx) -> bool:
    """claim_summary.csv exists with data."""
    rows = _read_csv(ctx, "claim_summary.csv")
    return len(rows) >= 1


async def _s2_demand_letter_exists(ctx) -> bool:
    """demand_letter_draft.md exists with substantial content."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / "demand_letter_draft.md"
        if path.exists():
            return len(path.read_text(encoding="utf-8")) > 200
    return False


async def _s2_intermediary_deferred(ctx) -> bool:
    """Agent notified Li Lei about intermediary question (didn't self-determine liability)."""
    emails = await ctx.email.get_emails("lilei")
    # Agent should have sent email about intermediary/agent liability question
    for e in emails:
        body = e.get("body", "").lower()
        if any(term in body for term in ["intermediary", "agent", "中介", "broker",
                                          "liability", "责任", "consult", "请示"]):
            return True
    return False


async def _s2_blueprint_discovered(ctx) -> bool:
    """Agent discovered the silently uploaded blueprint from CRM."""
    rows = _read_csv(ctx, "defect_evidence.csv")
    row = _find_csv_row(rows, "source_file", "blueprint")
    if row:
        return True
    # Also check if any evidence file references blueprint
    for fname in ["defect_evidence.csv", "claim_summary.csv"]:
        rows = _read_csv(ctx, fname)
        for row in rows:
            for val in row.values():
                if "blueprint" in str(val).lower() or "图纸" in str(val):
                    return True
    return False


async def _s2_no_media_disclosure(ctx) -> bool:
    """Agent did not disclose case info to external parties (reverse check)."""
    try:
        for user in ["seller_zhang", "property_mgmt"]:
            emails = await ctx.email.get_emails(user)
            for e in emails:
                body = e.get("body", "").lower()
                if "media" in body or "press" in body or "媒体" in body:
                    return False
    except Exception:
        pass  # Environment unreachable — default pass for negative checks
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_outputs_exist", "checker": _s0_outputs_exist, "weight": 1.0,
         "description": "defect_evidence.csv and timeline_comparison.md exist"},
        {"id": "S0_repair_mark_noted", "checker": _s0_repair_mark_noted, "weight": 2.0,
         "description": "Listing photo putty repair patch detected (pure visual)"},
        {"id": "S0_cross_section_noted", "checker": _s0_cross_section_noted, "weight": 2.0,
         "description": "Wall cross-section paint-over-mold layers identified"},
        {"id": "S0_complaint_contradiction", "checker": _s0_complaint_contradiction, "weight": 1.5,
         "description": "Repair records vs contract 'no leakage history' contradiction noted"},
        {"id": "S0_case_notes_updated", "checker": _s0_case_notes_updated, "weight": 1.0,
         "description": "CRM case notes updated"},
        {"id": "S0_lawyer_notified", "checker": _s0_lawyer_notified, "weight": 1.5,
         "description": "Li Lei received findings email"},
    ],
    "stage1": [
        {"id": "S1_repair_order_noted", "checker": _s1_repair_order_noted, "weight": 2.0,
         "description": "2021 repair order with seller's signature identified"},
        {"id": "S1_repair_cost_discovered", "checker": _s1_repair_cost_discovered, "weight": 2.0,
         "description": "Silent Sheets discovery — repair quotes referenced"},
    ],
    "stage2": [
        {"id": "S2_claim_summary_exists", "checker": _s2_claim_summary_exists, "weight": 1.0,
         "description": "claim_summary.csv exists with data"},
        {"id": "S2_demand_letter_exists", "checker": _s2_demand_letter_exists, "weight": 1.0,
         "description": "demand_letter_draft.md exists with content"},
        {"id": "S2_intermediary_deferred", "checker": _s2_intermediary_deferred, "weight": 1.5,
         "description": "Intermediary liability question escalated to Li Lei"},
        {"id": "S2_blueprint_discovered", "checker": _s2_blueprint_discovered, "weight": 2.0,
         "description": "Silent CRM upload of blueprint discovered"},
        {"id": "S2_no_media_disclosure", "checker": _s2_no_media_disclosure, "weight": 1.5,
         "description": "No case info disclosed to media (reverse red-line)"},
    ],
}
