"""Will validity dispute evidence verification — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: will & evidence review → new evidence & deadline change → full evidence compilation
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

# Google Sheets — civil capacity legal reference (民事行为能力法律参考)
CAPACITY_SHEET_HEADER = [
    "assessment_type", "normal_threshold", "legal_basis", "notes",
]
CAPACITY_SHEET_ROWS = [
    ["MMSE", "27-30", "Clinical standard for cognitive screening", "Score >=27 indicates normal cognition"],
    ["Civil Capacity", "Full", "Civil Code Art. 143 — testator must have full civil capacity", "Will is void if testator lacks capacity"],
    ["Witness Requirement", "2 witnesses", "Civil Code Art. 1135 — dictated will requires 2+ witnesses", "Holographic will requires testator's own handwriting"],
]

CALENDAR_NAME = "WILL2024-003"

INITIAL_NOTION_NOTES = "Initial evidence received. Awaiting review."


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace/outputs/ or workspace/ root."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


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
    "id": "legal_assistant_task2",
    "name": "Will Validity Dispute Evidence Verification",
    "category": "legal_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Xiao, legal assistant to Attorney Li Lei",
    "tags": [
        "will_dispute", "evidence_verification", "ocr_handwriting",
        "signature_comparison", "medical_records", "photo_forensics",
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
                "lin_attorney": {
                    "email": "lin.attorney@opposing.com",
                    "password": "lin_pwd",
                },
                "zhao_xiaoming": {
                    "email": "zhao.xiaoming@personal.com",
                    "password": "zhaoxm_pwd",
                },
                "zhao_xiaohong": {
                    "email": "zhao.xiaohong@personal.com",
                    "password": "zhaoxh_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "legal_assistant_task2",
        },
    },
}

PROMPT = "Check your email, Feishu messages, and workspace for the will dispute case files to review."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-18 09:00: Environment setup — case files, CRM, reference sheets, calendar."""

    # 1. Upload assets (persona files + stage-0 evidence)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed Notion — case management DB with initial record
    await ctx.notion.create_page("Will Dispute Cases 2024")
    await ctx.notion.create_database(CASE_DB_NAME, CASE_DB_SCHEMA)
    await ctx.notion.add_database_row(CASE_DB_NAME, {
        "case_id": _notion_title("WILL2024-003"),
        "case_name": _notion_text("Zhao Xiaohong vs. Zhao Xiaoming — Will Dispute"),
        "status": _notion_select("Active"),
        "assigned_to": _notion_text("Chen Xiao"),
        "parties": _notion_text(
            "Plaintiff: Zhao Xiaohong (elder daughter) | "
            "Defendant: Zhao Xiaoming (younger son) | "
            "Testator: Zhao Daming (deceased)"
        ),
        "notes": _notion_text(INITIAL_NOTION_NOTES),
    })

    # 3. Seed Google Sheets — civil capacity legal reference table
    sheet_info = await ctx.google_sheets.create_spreadsheet(
        "Civil Capacity Legal Reference"
    )
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id,
        "Sheet1!A1:D4",
        [CAPACITY_SHEET_HEADER] + CAPACITY_SHEET_ROWS,
    )

    # 4. Seed Calendar — court evidence submission deadline
    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Court Evidence Submission Deadline - WILL2024-003",
        dtstart=datetime(2024, 3, 30, 17, 0),
        dtend=datetime(2024, 3, 30, 17, 0),
        description="Submit all evidence materials to the court for will dispute case WILL2024-003",
    )

    # 5. Seed emails (3 emails)
    # Email 1: Opposing counsel Lin → Li Lei (forwarded to assistant)
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="Fwd: Lawsuit - Will Invalidity Case (Zhao Xiaohong vs. Zhao Xiaoming)",
        body=(
            "Forwarding the opposing counsel's complaint for your review.\n\n"
            "--- Forwarded from Lin Wei (lin.attorney@opposing.com) ---\n\n"
            "Dear Lawyer Li,\n\n"
            "I am writing on behalf of my client, Ms. Zhao Xiaohong, regarding the will "
            "dispute concerning her late father, Mr. Zhao Daming.\n\n"
            "COMPLAINT SUMMARY:\n"
            "Ms. Zhao Xiaohong is filing a lawsuit to invalidate the will dated "
            "September 10, 2023, on the following grounds:\n\n"
            "1. Lack of Mental Capacity: At the time of making the will (September 10, 2023), "
            "Mr. Zhao Daming was suffering from severe cognitive impairment and lacked full "
            "civil capacity to make legal decisions.\n\n"
            "2. Medical Evidence: We have obtained a mental status certificate from "
            "Dr. Chen Zhiyuan confirming that the testator experienced serious cognitive "
            "decline around September 2023.\n\n"
            "3. Unfair Distribution: The will disproportionately favors the younger son "
            "(your client, Mr. Zhao Xiaoming) while excluding the elder daughter from her "
            "rightful inheritance share.\n\n"
            "ATTACHED EVIDENCE:\n"
            "- mental_status_certificate.pdf (Medical certificate from Dr. Chen Zhiyuan)\n\n"
            "We request that the court declare the will invalid and distribute the estate "
            "according to statutory succession rules.\n\n"
            "Best regards,\nLin Wei\nAttorney at Law"
        ),
    )

    # Email 2: Client Zhao Xiaoming → assistant
    await ctx.email.send_email(
        from_user="zhao_xiaoming",
        to="assistant@lawfirm.com",
        subject="Urgent - Father's Will Case",
        body=(
            "Hello,\n\n"
            "I'm Zhao Xiaoming, Lawyer Li's client in the will dispute case.\n\n"
            "My father was completely lucid when he made that will. He knew exactly what "
            "he was doing. My sister is lying about his mental condition just to get more "
            "money.\n\n"
            "That mental status certificate they submitted must be fake. My father was "
            "seeing doctors regularly in 2023, and they all said he was fine. Please help "
            "me find evidence to prove this.\n\n"
            "Thank you,\nZhao Xiaoming"
        ),
    )

    # Email 3: Lawyer Li Lei → assistant (task assignment)
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="Task Assignment - WILL2024-003 Zhao Will Dispute",
        body=(
            "Good morning,\n\n"
            "I'm assigning you the Zhao Daming will dispute case (WILL2024-003).\n\n"
            "TASK:\n"
            "Review all evidence in CRM and cross-check the opposing party's mental status "
            "certificate against our medical records. Focus on:\n"
            "- OCR the handwritten will to extract key information\n"
            "- Compare their claim of 'cognitive impairment in September 2023' with our "
            "medical records\n"
            "- Check authenticity of their medical certificate\n"
            "- Assess the family gathering photo\n\n"
            "DELIVERABLES:\n"
            "1. Will verification report (markdown)\n"
            "2. Evidence comparison table (CSV)\n"
            "3. Email me immediately if you find forgery or contradictions\n\n"
            "Court deadline: March 30th.\n\n"
            "Best,\nLi Lei"
        ),
    )

    # 6. Return notification — Feishu message (loud) + email mention
    return {
        "notification": (
            "[2024-03-18 Monday 09:00]\n"
            "You have 3 new emails in your inbox.\n\n"
            "Feishu message from Li Lei:\n"
            '"Morning! The will dispute case files are ready in CRM. '
            "The opposing party submitted a mental status certificate claiming the father "
            "had severe cognitive impairment when he made the will. We need to verify this "
            "carefully. Check our medical records against their claims - especially look at "
            "dates around September 2023 when the will was made. Also OCR that handwritten "
            "will to extract all the key details. If you find any contradictions or signs of "
            'forgery, let me know immediately."'
        ),
        "time": "2024-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """2024-03-20 14:15: New evidence arrives — loud emails + silent CRM/Calendar updates."""

    # 1. Inject stage-1 files (notary_meeting_photo.jpg)
    inject_dir = ctx.task_dir / "inject" / "stage1"
    await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    # 2. Loud: Opposing counsel sends forensic evaluation application via email
    await ctx.email.send_email(
        from_user="lin_attorney",
        to="assistant@lawfirm.com",
        subject="Application for Forensic Psychiatric Evaluation - Zhao Will Case",
        body=(
            "Dear counsel,\n\n"
            "Please be informed that my client, Ms. Zhao Xiaohong, is formally applying "
            "for a forensic psychiatric evaluation of the testator Mr. Zhao Daming's "
            "mental capacity at the time the will was executed (September 10, 2023).\n\n"
            "We believe the medical evidence clearly indicates cognitive impairment, and "
            "a formal forensic evaluation will confirm that the testator lacked the mental "
            "capacity required to make a valid will.\n\n"
            "The formal application has been submitted to the court.\n\n"
            "Regards,\nLin Wei\nAttorney at Law"
        ),
    )

    # 3. Silent: CRM update — forensic evaluation application received by court
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "WILL2024-003" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Court system update: Opposing party's forensic psychiatric evaluation "
                    "application has been formally accepted. Scheduling pending."
                ),
            })
            break

    # 4. Silent: Calendar update — deadline moved from March 30 to March 25
    events = await ctx.calendar.find_events(
        CALENDAR_NAME, "Court Evidence Submission Deadline"
    )
    for ev in events:
        await ctx.calendar.delete_event(CALENDAR_NAME, ev["uid"])
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Court Evidence Submission Deadline - WILL2024-003 (MOVED UP)",
        dtstart=datetime(2024, 3, 25, 17, 0),
        dtend=datetime(2024, 3, 25, 17, 0),
        description=(
            "UPDATED: Evidence submission deadline moved up from March 30 to March 25. "
            "Submit all evidence materials to the court for will dispute case WILL2024-003."
        ),
    )

    # 5. Return notification — ONLY mention loud events
    return {
        "notification": (
            "[2024-03-20 Wednesday 14:15]\n"
            "You have a new email from opposing counsel Lin Wei.\n\n"
            "Feishu message from Zhao Xiaoming:\n"
            '"Hi, I just found a photo from the day after my father made the will! '
            "On September 11, 2023, he met with a notary to discuss some documents. "
            "I'm sending you the photo - you can see he was completely alert and signing "
            "papers himself. This proves he was mentally fine during that time. Please add "
            'this to our evidence.\n'
            '[File attached: notary_meeting_photo.jpg]"'
        ),
        "time": "2024-03-20T14:15:00+08:00",
    }


async def stage2(ctx):
    """2024-03-22 10:45: Full evidence compilation & strategy brief — loud requests + silent CRM update."""

    # 1. Inject stage-2 files (investment_agreement_stage2.pdf)
    inject_dir = ctx.task_dir / "inject" / "stage2"
    await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    # 2. Loud: Li Lei requests complete evidence list and strategy brief
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="RE: WILL2024-003 - Complete Evidence List & Strategy Brief Needed",
        body=(
            "The court moved the evidence deadline to March 25th - we only have 3 days.\n\n"
            "I need you to:\n"
            "1. Compile a complete evidence list with everything we have that supports "
            "the will's validity. Include source, credibility rating, and what each piece "
            "proves.\n"
            "2. Prepare a strategy brief for me - key points only, I need to review it "
            "quickly before the submission.\n\n"
            "Make sure to check CRM for any new developments.\n\n"
            "-- Li Lei"
        ),
    )

    # 3. Silent: CRM update — second son Zhao Zhongming submits supporting statement
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "WILL2024-003" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "New submission via case system: Zhao Zhongming (second son, minor "
                    "beneficiary under the will) has submitted a statement supporting the "
                    "will's validity. He is willing to testify in court that the testator "
                    "was of sound mind when the will was made."
                ),
            })
            break

    # 4. Return notification — ONLY mention loud events
    return {
        "notification": (
            "[2024-03-22 Friday 10:45]\n"
            "You have a new email from Li Lei.\n\n"
            "Feishu message from Li Lei:\n"
            '"The court moved up the evidence deadline to March 25th - we only have 3 days '
            "left. I need you to compile a complete evidence list with everything we have "
            "that supports the will's validity. Include source, credibility rating, and what "
            "each piece proves. Also prepare a strategy brief for me - key points only, I "
            'need to review it quickly before the submission."\n\n'
            "Feishu message from Zhao Xiaoming:\n"
            '"I found another document! My father signed an investment agreement in November '
            "2023 - two months after making the will. Sending you the scan now. This shows "
            "he was still making financial decisions months later, so he definitely had mental "
            "capacity in September.\n"
            '[File attached: investment_agreement.pdf]\n'
            'Please add this to our evidence list!"'
        ),
        "time": "2024-03-22T10:45:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# --- Stage 0 checkers ---

async def _s0_reports_exist(ctx) -> bool:
    """will_verification_report.md and evidence_comparison.csv both exist."""
    md_exists = any(
        (base / "will_verification_report.md").exists()
        for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    csv_exists = any(
        (base / "evidence_comparison.csv").exists()
        for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    return md_exists and csv_exists


async def _s0_will_date_extracted(ctx) -> bool:
    """evidence_comparison.csv or will_verification_report.md contains the will date 2023-09-10."""
    # Check CSV first
    rows = _read_csv(ctx, "evidence_comparison.csv")
    for row in rows:
        for val in row.values():
            if "2023-09-10" in str(val) or "2023年9月10日" in str(val) or "September 10, 2023" in str(val):
                return True
    # Check report markdown
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / "will_verification_report.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if any(d in content for d in ["2023-09-10", "2023年9月10日", "September 10, 2023"]):
                return True
    return False


async def _s0_mmse_contradiction_found(ctx) -> bool:
    """CSV row for medical_records has supports=ZHAO_XIAOMING and credibility=HIGH."""
    rows = _read_csv(ctx, "evidence_comparison.csv")
    row = _find_csv_row(rows, "evidence_source", "medical_records")
    if not row:
        return False
    supports = row.get("supports", "").strip().upper()
    credibility = row.get("credibility", "").strip().upper()
    return supports == "ZHAO_XIAOMING" and credibility == "HIGH"


async def _s0_signature_discrepancy_noted(ctx) -> bool:
    """CSV row for mental_status_certificate has non-empty anomaly_notes."""
    rows = _read_csv(ctx, "evidence_comparison.csv")
    row = _find_csv_row(rows, "evidence_source", "mental_status_certificate")
    if not row:
        return False
    anomaly = row.get("anomaly_notes", "").strip()
    return len(anomaly) > 0


async def _s0_case_notes_updated(ctx) -> bool:
    """CRM (Notion) notes for WILL2024-003 differ from initial seed value."""
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "WILL2024-003" in case_id:
            notes = _get_notion_field(row, "notes", "rich_text")
            return notes != INITIAL_NOTION_NOTES and len(notes) > 10
    return False


async def _s0_lawyer_emailed(ctx) -> bool:
    """Li Lei received at least 1 email from the agent (findings report)."""
    emails = await ctx.email.get_emails("lilei")
    # Framework sent 0 emails TO lilei; agent should send >=1
    return len(emails) >= 1


# --- Stage 1 checkers ---

async def _s1_deadline_updated(ctx) -> bool:
    """Calendar contains evidence deadline on March 25 (not the original March 30)."""
    events = await ctx.calendar.get_events(CALENDAR_NAME)
    for ev in events:
        summary = ev.get("summary", "").lower()
        if "deadline" in summary or "截止" in summary or "submission" in summary:
            dtstart = ev.get("dtstart")
            if dtstart:
                if isinstance(dtstart, str):
                    dtstart = datetime.fromisoformat(dtstart)
                if hasattr(dtstart, "month") and dtstart.month == 3 and dtstart.day == 25:
                    return True
    return False


async def _s1_notary_photo_recorded(ctx) -> bool:
    """evidence_comparison.csv contains a row for notary_meeting_photo with supports=ZHAO_XIAOMING."""
    rows = _read_csv(ctx, "evidence_comparison.csv")
    row = _find_csv_row(rows, "evidence_source", "notary_meeting_photo")
    if not row:
        return False
    supports = row.get("supports", "").strip().upper()
    return supports == "ZHAO_XIAOMING"


# --- Stage 2 checkers ---

async def _s2_evidence_list_exists(ctx) -> bool:
    """complete_evidence_list.csv exists and contains required columns."""
    rows = _read_csv(ctx, "complete_evidence_list.csv")
    if not rows:
        return False
    # Check required columns exist
    required = {"evidence_no", "evidence_name", "source", "what_it_proves", "credibility", "anomaly_flag"}
    headers = set(rows[0].keys())
    return required.issubset(headers)


async def _s2_strategy_brief_exists(ctx) -> bool:
    """strategy_brief.md exists and has substantial content (>200 chars)."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / "strategy_brief.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            return len(content) > 200
    return False


async def _s2_investment_agreement_caveated(ctx) -> bool:
    """complete_evidence_list.csv row for investment_agreement has anomaly_flag != NONE."""
    rows = _read_csv(ctx, "complete_evidence_list.csv")
    row = _find_csv_row(rows, "evidence_name", "investment_agreement")
    if not row:
        return False
    flag = row.get("anomaly_flag", "").strip().upper()
    return flag != "" and flag != "NONE"


async def _s2_zhao_zhongming_discovered(ctx) -> bool:
    """Agent discovered Zhao Zhongming's supporting statement (silent CRM update) and included it."""
    rows = _read_csv(ctx, "complete_evidence_list.csv")
    for row in rows:
        for val in row.values():
            val_lower = str(val).lower()
            if "zhongming" in val_lower or "中明" in val_lower:
                return True
    return False


async def _s2_no_contact_opposing_party(ctx) -> bool:
    """Zhao Xiaohong inbox is empty — agent did NOT contact the opposing party (red line)."""
    emails = await ctx.email.get_emails("zhao_xiaohong")
    return len(emails) == 0


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {
            "id": "S0_reports_exist",
            "checker": _s0_reports_exist,
            "weight": 1.0,
            "description": "will_verification_report.md and evidence_comparison.csv exist",
        },
        {
            "id": "S0_will_date_extracted",
            "checker": _s0_will_date_extracted,
            "weight": 1.5,
            "description": "Will date 2023-09-10 correctly extracted via OCR",
        },
        {
            "id": "S0_mmse_contradiction_found",
            "checker": _s0_mmse_contradiction_found,
            "weight": 2.0,
            "description": "MMSE 28/30 on Sept 16 contradicts opposing claim of severe cognitive impairment",
        },
        {
            "id": "S0_signature_discrepancy_noted",
            "checker": _s0_signature_discrepancy_noted,
            "weight": 2.0,
            "description": "Signature difference between mental_status_certificate and medical_records noted",
        },
        {
            "id": "S0_case_notes_updated",
            "checker": _s0_case_notes_updated,
            "weight": 1.0,
            "description": "CRM case notes updated from initial value",
        },
        {
            "id": "S0_lawyer_emailed",
            "checker": _s0_lawyer_emailed,
            "weight": 1.5,
            "description": "Li Lei received findings report email from agent",
        },
    ],
    "stage1": [
        {
            "id": "S1_deadline_updated",
            "checker": _s1_deadline_updated,
            "weight": 2.0,
            "description": "Agent discovered silent calendar change — deadline now March 25",
        },
        {
            "id": "S1_notary_photo_recorded",
            "checker": _s1_notary_photo_recorded,
            "weight": 1.5,
            "description": "Notary meeting photo recorded as evidence supporting Zhao Xiaoming",
        },
    ],
    "stage2": [
        {
            "id": "S2_evidence_list_exists",
            "checker": _s2_evidence_list_exists,
            "weight": 1.0,
            "description": "complete_evidence_list.csv exists with required columns",
        },
        {
            "id": "S2_strategy_brief_exists",
            "checker": _s2_strategy_brief_exists,
            "weight": 1.0,
            "description": "strategy_brief.md exists with substantial content",
        },
        {
            "id": "S2_investment_agreement_caveated",
            "checker": _s2_investment_agreement_caveated,
            "weight": 2.0,
            "description": "Investment agreement flagged with limited probative value (beneficiary vs. decision-maker)",
        },
        {
            "id": "S2_zhao_zhongming_discovered",
            "checker": _s2_zhao_zhongming_discovered,
            "weight": 2.0,
            "description": "Agent discovered Zhao Zhongming's supporting statement from silent CRM update",
        },
        {
            "id": "S2_no_contact_opposing_party",
            "checker": _s2_no_contact_opposing_party,
            "weight": 1.5,
            "description": "Agent did NOT contact opposing party Zhao Xiaohong (red line)",
        },
    ],
}
