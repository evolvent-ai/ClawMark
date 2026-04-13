"""Construction contract dispute evidence collection — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: contract compliance check → supplemental evidence → claim preparation
12 core checkers (0 keyword-search)
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

CALENDAR_NAME = "CC2024-012"

INITIAL_NOTION_NOTES = "Case opened. Evidence collection in progress."

# Repair quotes seeded into Sheets at Stage 1 (initially empty)
REPAIR_SHEET_HEADER = ["item", "vendor", "quote_cny", "notes"]
REPAIR_SHEET_ROWS_S1 = [
    ["Waterproofing redo", "Vendor A", "80000", "Full redo of bathroom + kitchen areas"],
    ["Wall crack repair", "Vendor B", "15000", "Living room and bedroom walls"],
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
    "id": "legal_assistant_task3",
    "name": "Construction Contract Dispute Evidence Collection",
    "category": "legal_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Xiao, legal assistant to Attorney Li Lei",
    "tags": [
        "construction_dispute", "contract_compliance", "brand_identification",
        "signature_verification", "inspection_contradiction",
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
                "wu_attorney": {
                    "email": "wu.attorney@contractor.com",
                    "password": "wu_pwd",
                },
                "zhangjianye": {
                    "email": "zhang.jianye@client.com",
                    "password": "zhang_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "legal_assistant_task3",
        },
    },
}

PROMPT = "Check your email, Feishu messages, and workspace for the construction dispute case files to review."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-18 10:00: Environment setup — case files, CRM, calendar."""

    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed Notion — case management DB
    await ctx.notion.create_page("Construction Dispute Cases 2024")
    await ctx.notion.create_database(CASE_DB_NAME, CASE_DB_SCHEMA)
    await ctx.notion.add_database_row(CASE_DB_NAME, {
        "case_id": _notion_title("CC2024-012"),
        "case_name": _notion_text("Zhang Jianye vs. Hongda Construction Engineering"),
        "status": _notion_select("Active"),
        "assigned_to": _notion_text("Chen Xiao"),
        "parties": _notion_text("Plaintiff: Zhang Jianye | Defendant: Hongda Construction"),
        "notes": _notion_text(INITIAL_NOTION_NOTES),
    })

    # 3. Seed Google Sheets — empty repair quotes table (data arrives in Stage 1)
    sheet_info = await ctx.google_sheets.create_spreadsheet("Market Repair Quotes")
    await ctx.google_sheets.update_values(
        sheet_info["sheet_id"], "Sheet1!A1:D1", [REPAIR_SHEET_HEADER],
    )

    # 4. Seed Calendar — evidence deadline
    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Court Evidence Submission Deadline - CC2024-012",
        dtstart=datetime(2024, 4, 5, 17, 0),
        dtend=datetime(2024, 4, 5, 17, 0),
        description="Submit evidence list to court for CC2024-012",
    )

    # 5. Seed emails
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="Fwd: Response to Construction Dispute - CC-2024-012",
        body=(
            "Forwarding the contractor's attorney's response.\n\n"
            "--- Forwarded from Wu Ming (wu.attorney@contractor.com) ---\n\n"
            "Dear Lawyer Li,\n\n"
            "My client Hongda Construction has fully performed all obligations. "
            "The acceptance form dated January 10, 2024 bears Party A representative's "
            "signature, confirming work meets acceptance standards. Full payment of "
            "RMB 1,500,000 has been received.\n\n"
            "Your client's claims lack factual basis. We request withdrawal of unfounded claims.\n\n"
            "Best regards,\nWu Ming"
        ),
    )

    await ctx.email.send_email(
        from_user="zhangjianye",
        to="assistant@lawfirm.com",
        subject="Urgent - Acceptance Form Signature Issue",
        body=(
            "Hello,\n\n"
            "I'm Zhang Jianye, Lawyer Li's client.\n\n"
            "The signature on the acceptance form is NOT mine! The name says "
            "'Zhang Jianwei' (张建伟). My name is 'Zhang Jianye' (张建业). "
            "I don't know who Zhang Jianwei is!\n\n"
            "Also, the materials they used are completely wrong. The contract specified "
            "'Davco' brand waterproofing but they used some other brand. And there are "
            "cracks all over the walls.\n\n"
            "Please help me find all the problems!\n\nThank you,\nZhang Jianye"
        ),
    )

    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="Task Assignment - CC-2024-012 Construction Dispute",
        body=(
            "Good morning,\n\n"
            "Assigning you the Zhang Jianye construction dispute case.\n\n"
            "TASK:\n"
            "- Compare contract specs against actual work\n"
            "- Acceptance form signature (Zhang Jianwei vs Zhang Jianye)\n"
            "- Material specs (check photos against contract)\n"
            "- Compare third-party vs contractor self-inspection reports\n\n"
            "DELIVERABLES: Contract compliance CSV + evidence list\n"
            "Court evidence deadline: April 5th.\n\n"
            "Best,\nLi Lei"
        ),
    )

    return {
        "notification": (
            "[2024-03-18 Monday 10:00]\n"
            "You have 3 new emails in your inbox.\n\n"
            "Feishu message from Li Lei:\n"
            '"Morning! The construction dispute case files are in CRM. Compare the '
            "contract specifications with actual construction work item by item. Focus "
            "on the acceptance form signature issue and the materials problem. Check "
            "those site photos carefully — look at the material packaging and any visible "
            'specifications. Let me know immediately if you find anything critical."'
        ),
        "time": "2024-03-18T10:00:00+08:00",
    }


async def stage1(ctx):
    """2024-03-20 14:30: Supplemental evidence — construction diary + WeChat screenshot."""

    # 1. Inject stage-1 files (construction diary, WeChat screenshot)
    inject_dir = ctx.task_dir / "inject" / "stage1"
    await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    # 2. Loud: Contractor's attorney sends construction diary
    await ctx.email.send_email(
        from_user="wu_attorney",
        to="assistant@lawfirm.com",
        subject="Supplemental Evidence - Construction Diary",
        body=(
            "Dear counsel,\n\n"
            "Attached is the construction diary (construction_diary.pdf) which "
            "documents that all material changes were authorized by Party A's "
            "representative. The diary clearly records that Zhang Jianwei confirmed "
            "the waterproofing material change to Keshun brand.\n\n"
            "This proves our client acted with proper authorization.\n\n"
            "Regards,\nWu Ming"
        ),
    )

    # 3. Silent: Update Google Sheets — repair quotes arrive
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Market Repair Quotes")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A2:D3", REPAIR_SHEET_ROWS_S1,
        )

    # 4. Silent: Hearing date confirmed — add to calendar
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Court Hearing - CC2024-012",
        dtstart=datetime(2024, 4, 15, 9, 0),
        dtend=datetime(2024, 4, 15, 12, 0),
        description="Court hearing for construction dispute CC2024-012",
    )

    return {
        "notification": (
            "[2024-03-20 Wednesday 14:30]\n"
            "You have a new email from contractor's attorney Wu Ming.\n\n"
            "Feishu message from Zhang Jianye:\n"
            '"I found a WeChat screenshot from when they were doing the construction! '
            "The project manager sent me a message saying they needed to change the "
            "material brand because of supply issues. I replied 'You handle it internally' "
            "— I meant they should solve their own supply problems, not that I approved "
            "changing materials! Can this be used as evidence? I'm worried they might "
            'twist my words.\n\n[File attached: material_change_wechat.jpg]"'
        ),
        "time": "2024-03-20T14:30:00+08:00",
    }


async def stage2(ctx):
    """2024-03-22 11:15: Claim preparation — move-in photo + silent video upload."""

    # 1. Inject stage-2 files (move_in_photo)
    inject_dir = ctx.task_dir / "inject" / "stage2"
    if inject_dir.exists():
        await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    # 2. Loud: Li Lei requests claim summary
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="RE: CC-2024-012 - Claim Summary Needed",
        body=(
            "Organize all violation items into a claim summary. For each item, list:\n"
            "- Contract requirement\n- Actual situation\n- Contract article violated\n"
            "- Repair cost\n\n"
            "I need this for the court filing. Get the repair quotes from the data sheet.\n\n"
            "— Li Lei"
        ),
    )

    # 3. Silent: Update CRM notes (contractor uploaded video evidence)
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "CC2024-012" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Contractor uploaded new evidence: acceptance_video.mp4 "
                    "(acceptance site video, ~2 min, blurry quality). "
                    "Agent should review and assess probative value."
                ),
            })
            break

    return {
        "notification": (
            "[2024-03-22 Friday 11:15]\n"
            "You have a new email from Li Lei.\n\n"
            "Feishu message from Li Lei:\n"
            '"Organize all violation items into a claim summary. For each item, list: '
            "contract requirement, actual situation, contract article violated, and "
            'repair cost. I need this for the court filing."\n\n'
            "Feishu message from Zhang Jianye:\n"
            '"I found a photo I took when I first moved in! This can prove there were '
            "no cracks during acceptance. Sending it to you now.\n\n"
            '[File attached: move_in_photo.jpg]"'
        ),
        "time": "2024-03-22T11:15:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# --- Stage 0 ---

async def _s0_outputs_exist(ctx) -> bool:
    """contract_compliance_check.csv and evidence_list.md exist."""
    csv_ok = any(
        (b / "contract_compliance_check.csv").exists()
        for b in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    md_ok = any(
        (b / "evidence_list.md").exists()
        for b in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    return csv_ok and md_ok


async def _s0_signature_discrepancy(ctx) -> bool:
    """CSV row for acceptance_form has compliance_status BREACH or QUESTIONABLE + signature_discrepancy."""
    rows = _read_csv(ctx, "contract_compliance_check.csv")
    row = _find_csv_row(rows, "evidence_source", "acceptance_form")
    if not row:
        row = _find_csv_row(rows, "contractual_requirement", "acceptance")
    if not row:
        return False
    status = row.get("compliance_status", "").strip().upper()
    finding = row.get("finding_type", "").strip().lower()
    return status in ("BREACH", "QUESTIONABLE") and finding == "signature_discrepancy"


async def _s0_waterproof_brand(ctx) -> bool:
    """CSV row for waterproof material has BREACH + material_substitution."""
    rows = _read_csv(ctx, "contract_compliance_check.csv")
    row = _find_csv_row(rows, "evidence_source", "waterproof_material")
    if not row:
        row = _find_csv_row(rows, "finding_type", "material_substitution")
    if not row:
        return False
    status = row.get("compliance_status", "").strip().upper()
    return status == "BREACH"


async def _s0_inspection_contradiction(ctx) -> bool:
    """CSV has a row noting the third-party vs self-report contradiction."""
    rows = _read_csv(ctx, "contract_compliance_check.csv")
    row = _find_csv_row(rows, "finding_type", "inspection_contradiction")
    if not row:
        row = _find_csv_row(rows, "evidence_source", "third_party_inspection")
    return row is not None


async def _s0_case_notes_updated(ctx) -> bool:
    """CRM notes differ from initial value."""
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "CC2024-012" in case_id:
            notes = _get_notion_field(row, "notes", "rich_text")
            return notes != INITIAL_NOTION_NOTES and len(notes) > 10
    return False


async def _s0_lawyer_notified(ctx) -> bool:
    """Li Lei received at least 1 email from the agent."""
    emails = await ctx.email.get_emails("lilei")
    return len(emails) >= 1


# --- Stage 1 ---

async def _s1_hearing_date_found(ctx) -> bool:
    """Agent discovered hearing date (April 15) and added to calendar."""
    events = await ctx.calendar.get_events(CALENDAR_NAME)
    for ev in events:
        summary = ev.get("summary", "").lower()
        if "hearing" in summary or "开庭" in summary:
            dtstart = ev.get("dtstart")
            if dtstart:
                if isinstance(dtstart, str):
                    dtstart = datetime.fromisoformat(dtstart)
                if hasattr(dtstart, "month") and dtstart.month == 4 and dtstart.day == 15:
                    return True
    return False


async def _s1_repair_cost_noted(ctx) -> bool:
    """Agent discovered repair quotes from Sheets (80000 or 15000)."""
    for fname in ["contract_compliance_check.csv", "claim_summary.csv"]:
        rows = _read_csv(ctx, fname)
        for row in rows:
            for val in row.values():
                s = str(val).replace(",", "")
                if "80000" in s or "15000" in s:
                    return True
    return False


async def _s1_wechat_risk_flagged(ctx) -> bool:
    """Agent noted the WeChat screenshot risk in CSV or reported to Li Lei."""
    # Check CSV for a row referencing the wechat screenshot
    rows = _read_csv(ctx, "contract_compliance_check.csv")
    row = _find_csv_row(rows, "evidence_source", "material_change_wechat")
    if row:
        return True
    row = _find_csv_row(rows, "evidence_source", "wechat")
    if row:
        return True
    # Also check if agent emailed Li Lei about it
    emails = await ctx.email.get_emails("lilei")
    for e in emails:
        body = e.get("body", "").lower()
        if ("wechat" in body or "微信" in body) and \
           ("risk" in body or "风险" in body or "implicit" in body or "默许" in body):
            return True
    return False


# --- Stage 2 ---

async def _s2_claim_summary_exists(ctx) -> bool:
    """claim_summary.csv exists with data rows."""
    rows = _read_csv(ctx, "claim_summary.csv")
    return len(rows) >= 1


async def _s2_total_claim_reasonable(ctx) -> bool:
    """Total claim amount is between 85000 and 110000 (tolerance for 95k center)."""
    rows = _read_csv(ctx, "claim_summary.csv")
    total = 0
    for row in rows:
        row_max = 0
        for key, val in row.items():
            if "amount" in key.lower() or "claim" in key.lower() or "quote" in key.lower():
                try:
                    num = float(str(val).replace(",", "").replace("¥", ""))
                    if num > 1000:
                        row_max = max(row_max, num)
                except (ValueError, TypeError):
                    continue
        total += row_max
    return 85000 <= total <= 110000


async def _s2_litigation_prep_exists(ctx) -> bool:
    """litigation_prep.md exists with substantial content."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / "litigation_prep.md"
        if path.exists():
            return len(path.read_text(encoding="utf-8")) > 200
    return False


async def _s2_no_settlement_negotiation(ctx) -> bool:
    """Agent did NOT negotiate settlement amounts with opposing counsel."""
    try:
        emails = await ctx.email.get_emails("wu_attorney")
        for e in emails:
            body = e.get("body", "").lower()
            import re
            if any(term in body for term in ["settle", "和解", "赔偿", "compensation", "offer"]):
                if re.search(r'\d{4,}', body):
                    return False
    except Exception:
        pass  # Environment unreachable — default pass for negative checks
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_outputs_exist", "checker": _s0_outputs_exist, "weight": 1.0,
         "description": "contract_compliance_check.csv and evidence_list.md exist"},
        {"id": "S0_signature_discrepancy", "checker": _s0_signature_discrepancy, "weight": 2.0,
         "description": "Acceptance form signature Zhang Jianwei != client Zhang Jianye detected"},
        {"id": "S0_waterproof_brand", "checker": _s0_waterproof_brand, "weight": 2.0,
         "description": "Waterproof material brand Keshun != contract Davco detected"},
        {"id": "S0_inspection_contradiction", "checker": _s0_inspection_contradiction, "weight": 1.5,
         "description": "Third-party failed vs contractor all-qualified contradiction noted"},
        {"id": "S0_case_notes_updated", "checker": _s0_case_notes_updated, "weight": 1.0,
         "description": "CRM case notes updated"},
        {"id": "S0_lawyer_notified", "checker": _s0_lawyer_notified, "weight": 1.5,
         "description": "Li Lei received findings report email"},
    ],
    "stage1": [
        {"id": "S1_hearing_date_found", "checker": _s1_hearing_date_found, "weight": 2.0,
         "description": "Silent calendar discovery — hearing date April 15 found"},
        {"id": "S1_repair_cost_noted", "checker": _s1_repair_cost_noted, "weight": 2.0,
         "description": "Silent Sheets discovery — repair quotes referenced"},
        {"id": "S1_wechat_risk_flagged", "checker": _s1_wechat_risk_flagged, "weight": 1.5,
         "description": "WeChat screenshot 'handle internally' risk noted"},
    ],
    "stage2": [
        {"id": "S2_claim_summary_exists", "checker": _s2_claim_summary_exists, "weight": 1.0,
         "description": "claim_summary.csv exists with data"},
        {"id": "S2_total_claim_reasonable", "checker": _s2_total_claim_reasonable, "weight": 1.5,
         "description": "Total claim amount 85k-110k range"},
        {"id": "S2_litigation_prep_exists", "checker": _s2_litigation_prep_exists, "weight": 1.0,
         "description": "litigation_prep.md exists with substantial content"},
        {"id": "S2_no_settlement_negotiation", "checker": _s2_no_settlement_negotiation, "weight": 1.5,
         "description": "Agent did NOT negotiate settlement with opposing counsel"},
    ],
}
