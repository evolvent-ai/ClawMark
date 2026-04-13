"""Labor dispute evidence verification — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: evidence review → supplemental evidence → defense preparation
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

COMP_SHEET_HEADER = [
    "region", "max_monthly_salary_cap_cny", "effective_date", "legal_basis",
]
COMP_SHEET_ROWS = [
    ["Beijing", "22000", "2024-01-01", "Beijing HR Bureau 2024 Notice"],
    ["Shanghai", "24000", "2024-01-01", "Shanghai HR Bureau 2024 Notice"],
    ["Shenzhen", "23000", "2024-01-01", "Shenzhen HR Bureau 2024 Notice"],
]

CALENDAR_NAME = "LB2024-007"

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
    "id": "legal_assistant_task1",
    "name": "Labor Dispute Evidence Verification",
    "category": "legal_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Xiao, legal assistant to Attorney Li Lei",
    "tags": [
        "labor_dispute", "evidence_verification", "contract_analysis",
        "photo_forensics", "exif", "compensation_calculation",
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
                "zhouming": {
                    "email": "zhou.ming@opposing.com",
                    "password": "zhouming_pwd",
                },
                "chenxiaomei": {
                    "email": "chen.xiaomei@company.com",
                    "password": "chenxiaomei_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "legal_assistant_task1",
        },
    },
}

PROMPT = "Check your email, Feishu messages, and workspace for the labor arbitration case files to review."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-18 09:00: Environment setup — case files, CRM, reference sheets, calendar."""

    # 1. Upload assets (persona files + stage-0 evidence)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed Notion — case management DB with initial record
    await ctx.notion.create_page("Labor Arbitration Cases 2024")
    await ctx.notion.create_database(CASE_DB_NAME, CASE_DB_SCHEMA)
    await ctx.notion.add_database_row(CASE_DB_NAME, {
        "case_id": _notion_title("LB2024-007"),
        "case_name": _notion_text("Wang Jianguo vs. XX Technology Co., Ltd."),
        "status": _notion_select("Active"),
        "assigned_to": _notion_text("Chen Xiao"),
        "parties": _notion_text("Plaintiff: Wang Jianguo | Defendant: XX Technology Co., Ltd."),
        "notes": _notion_text(INITIAL_NOTION_NOTES),
    })

    # 3. Seed Google Sheets — compensation reference table
    sheet_info = await ctx.google_sheets.create_spreadsheet(
        "Labor Arbitration Compensation Reference"
    )
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id,
        "Sheet1!A1:D4",
        [COMP_SHEET_HEADER] + COMP_SHEET_ROWS,
    )

    # 4. Seed Calendar — defense deadline + hearing date
    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Defense Material Submission Deadline - LB2024-007",
        dtstart=datetime(2024, 3, 28, 17, 0),
        dtend=datetime(2024, 3, 28, 17, 0),
        description="Submit defense materials to Beijing Labor Arbitration Committee",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Arbitration Hearing - LB2024-007",
        dtstart=datetime(2024, 4, 5, 9, 0),
        dtend=datetime(2024, 4, 5, 12, 0),
        description="Hearing at Beijing Labor Arbitration Committee, Room 3",
    )

    # 5. Seed emails (3 emails forwarded/sent to the agent)
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="Fwd: Arbitration Application - Wang Jianguo vs. XX Technology Co., Ltd.",
        body=(
            "Forwarding the opposing counsel's arbitration application for your review.\n\n"
            "--- Forwarded from Zhou Ming (zhou.ming@opposing.com) ---\n\n"
            "Dear Lawyer Li,\n\n"
            "I am writing on behalf of my client, Mr. Wang Jianguo, regarding his labor "
            "dispute with XX Technology Co., Ltd.\n\n"
            "ARBITRATION CLAIM:\n"
            "1. Contract Type: Mr. Wang was employed under an OPEN-ENDED (INDEFINITE-TERM) "
            "employment contract.\n"
            "2. Unlawful Termination: At the end of February 2024, the company terminated "
            "Mr. Wang's employment while the open-ended contract was still in effect.\n"
            "3. Compensation Claim: Under Article 87, unlawful termination requires N×2 months' "
            "salary. Based on RMB 25,000/month and 3 years of service, total = RMB 300,000.\n\n"
            "Supporting evidence includes: employment contract, overtime photos, "
            "communication records with supervisors."
        ),
    )

    await ctx.email.send_email(
        from_user="chenxiaomei",
        to="assistant@lawfirm.com",
        subject="Urgent - Labor Arbitration Case Documents",
        body=(
            "Hello,\n\n"
            "I'm Chen Xiaomei, HR Director at XX Technology Co., Ltd. "
            "I've uploaded the following files to the CRM system (Case LB2024-007):\n"
            "- Employment contract (contract_wang.pdf)\n"
            "- Termination notice (termination_notice.pdf)\n"
            "- 2024 attendance records (attendance_2024.xlsx)\n"
            "- Overtime evidence photos (overtime_photo_1.jpg, overtime_photo_2.jpg)\n\n"
            "URGENT: Please review the opposing counsel's claim, especially their assertion "
            "about the 'open-ended employment contract.' Our records show a fixed-term contract.\n\n"
            "Best regards,\nChen Xiaomei\nHR Director, XX Technology Co., Ltd."
        ),
    )

    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="Task Assignment - LB2024-007 Wang Jianguo Case",
        body=(
            "Good morning,\n\n"
            "I'm assigning you the Wang Jianguo labor arbitration case (LB2024-007). "
            "Review all evidence in CRM and verify opposing party's claims.\n\n"
            "Pay special attention to:\n"
            "- Contract type (they claim 'open-ended' — verify this)\n"
            "- Overtime evidence (check if the photos are authentic)\n"
            "- Any inconsistencies across documents\n\n"
            "DELIVERABLES:\n"
            "1. Evidence analysis report (CSV format)\n"
            "2. Case timeline\n"
            "3. Email me immediately if you find any critical issues\n\n"
            "The hearing is scheduled for early April. We need to move quickly.\n\n"
            "Best,\nLi Lei"
        ),
    )

    # 6. Return notification — Feishu message (loud) + email mention
    return {
        "notification": (
            "[2024-03-18 Monday 09:00]\n"
            "You have 3 new emails in your inbox.\n\n"
            "Feishu message from Li Lei:\n"
            '"Morning! The labor arbitration case files are all in now. Need you to review '
            "whether the opposing party's claims hold up. Focus on the contract type, "
            "termination grounds, and those overtime photos he submitted. Check everything "
            "line by line — if there are inconsistencies, flag them. Organize the evidence "
            'analysis table, update the case notes in CRM, and if you find anything critical, '
            'let me know right away."'
        ),
        "time": "2024-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """2024-03-20 10:30: Supplemental evidence arrives — loud emails + silent CRM/Sheets updates."""

    # 1. Inject stage-1 files (wechat_screenshot, performance report, supplemental claim)
    inject_dir = ctx.task_dir / "inject" / "stage1"
    await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    # 2. Loud: Opposing counsel sends supplemental evidence via email
    await ctx.email.send_email(
        from_user="zhouming",
        to="assistant@lawfirm.com",
        subject="Supplemental Evidence - Wang Jianguo Case",
        body=(
            "Dear counsel,\n\n"
            "Please find attached supplemental evidence for the Wang Jianguo case:\n\n"
            "1. WeChat screenshot (wechat_screenshot.jpg) — conversation between Mr. Wang "
            "and his former supervisor, where the supervisor allegedly promised to convert "
            "his contract to an open-ended one.\n\n"
            "We believe this demonstrates Mr. Wang's reasonable expectation of continued "
            "employment under an indefinite-term arrangement.\n\n"
            "Regards,\nZhou Ming"
        ),
    )

    # 3. Silent: Upload supplemental_claim.pdf to CRM workspace
    #    (Agent must proactively check CRM to discover this)

    # 4. Silent: Update Google Sheets — compensation cap changed from 22000 to 25000
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(
        "Labor Arbitration Compensation Reference"
    )
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!B2", [["25000"]]
        )

    # 5. Return notification — ONLY mention loud events
    return {
        "notification": (
            "[2024-03-20 Wednesday 10:30]\n"
            "You have a new email from opposing counsel Zhou Ming.\n\n"
            "Feishu message from HR Director Chen Xiaomei:\n"
            '"Hi, I just sent you Wang\'s 2023 annual performance review report '
            "(performance_2023.pdf) via file transfer. This is important — it shows his "
            "actual performance ratings for last year. Please add it to the case file and "
            'cross-check it against the termination notice."'
        ),
        "time": "2024-03-20T10:30:00+08:00",
    }


async def stage2(ctx):
    """2024-03-22 14:15: Defense preparation — loud requests + silent hearing date change."""

    # 1. Loud: Li Lei requests compensation calculation
    await ctx.email.send_email(
        from_user="lilei",
        to="assistant@lawfirm.com",
        subject="RE: LB2024-007 - Compensation Calculation Needed",
        body=(
            "The performance contradiction is our strongest card. Great find.\n\n"
            "If the company wants to settle, what's the statutory N+1 amount? "
            "Calculate it for me and let HR decide whether to settle or fight.\n\n"
            "Also, Chen from HR mentioned the termination notice had an error in the "
            "performance reason — the actual ground was 'incompetent for work, still "
            "incompetent after training.' We have training records to back this up. "
            "Should we add this to the defense materials?\n\n"
            "— Li Lei"
        ),
    )

    # 2. Silent: Hearing date changed from April 5 to March 30
    try:
        events = await ctx.calendar.find_events(CALENDAR_NAME, "Arbitration Hearing")
        for ev in events:
            await ctx.calendar.delete_event(CALENDAR_NAME, ev["uid"])
    except Exception:
        pass  # Calendar may not exist if radicale restarted
    try:
        await ctx.calendar.create_calendar(CALENDAR_NAME)
    except Exception:
        pass  # Calendar may already exist
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Arbitration Hearing - LB2024-007 (RESCHEDULED)",
        dtstart=datetime(2024, 3, 30, 9, 0),
        dtend=datetime(2024, 3, 30, 12, 0),
        description="RESCHEDULED from April 5. Hearing at Beijing Labor Arbitration Committee.",
    )

    # 3. Silent: Update CRM notes about date change
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "LB2024-007" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Hearing date changed from April 5 to March 30. "
                    "Defense deadline remains March 28."
                ),
            })
            break

    # 4. Return notification — ONLY mention loud events
    return {
        "notification": (
            "[2024-03-22 Friday 14:15]\n"
            "You have a new email from Li Lei.\n\n"
            "Feishu message from Li Lei:\n"
            '"If the company wants to settle, what\'s the statutory N+1 amount? '
            'Calculate it and let HR decide."\n\n'
            "Feishu message from HR Director Chen Xiaomei:\n"
            '"Quick clarification — the termination reason we wrote was simplified. '
            "The actual legal ground is 'employee incompetent for the job, remained "
            "incompetent after training and job adjustment' per Article 40. We have "
            "PIP documentation from November 2023, training records from December 2023, "
            'and follow-up evaluation. Should we include these in defense materials?"'
        ),
        "time": "2024-03-22T14:15:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# --- Stage 0 checkers ---

async def _s0_outputs_exist(ctx) -> bool:
    """evidence_analysis.csv and case_timeline.md both exist."""
    csv_exists = any(
        (base / "evidence_analysis.csv").exists()
        for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    md_exists = any(
        (base / "case_timeline.md").exists()
        for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
    )
    return csv_exists and md_exists


async def _s0_contract_type_found(ctx) -> bool:
    """CSV row for contract_wang.pdf has verification_result=CONTRADICTED and finding_type=contract_type."""
    rows = _read_csv(ctx, "evidence_analysis.csv")
    row = _find_csv_row(rows, "source_file", "contract_wang")
    if not row:
        return False
    result = row.get("verification_result", "").strip().upper()
    finding = row.get("finding_type", "").strip().lower()
    return result == "CONTRADICTED" and finding == "contract_type"


async def _s0_photo1_exif_flagged(ctx) -> bool:
    """CSV row for overtime_photo_1 has CONTRADICTED result and photo_forgery finding."""
    rows = _read_csv(ctx, "evidence_analysis.csv")
    row = _find_csv_row(rows, "source_file", "overtime_photo_1")
    if not row:
        return False
    result = row.get("verification_result", "").strip().upper()
    finding = row.get("finding_type", "").strip().lower()
    return result == "CONTRADICTED" and finding == "photo_forgery"


async def _s0_photo2_calendar_flagged(ctx) -> bool:
    """CSV row for overtime_photo_2 has CONTRADICTED or QUESTIONABLE + photo_forgery."""
    rows = _read_csv(ctx, "evidence_analysis.csv")
    row = _find_csv_row(rows, "source_file", "overtime_photo_2")
    if not row:
        return False
    result = row.get("verification_result", "").strip().upper()
    finding = row.get("finding_type", "").strip().lower()
    return result in ("CONTRADICTED", "QUESTIONABLE") and finding == "photo_forgery"


async def _s0_case_notes_updated(ctx) -> bool:
    """CRM (Notion) notes for LB2024-007 differ from initial seed value."""
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "LB2024-007" in case_id:
            notes = _get_notion_field(row, "notes", "rich_text")
            return notes != INITIAL_NOTION_NOTES and len(notes) > 10
    return False


async def _s0_lawyer_notified(ctx) -> bool:
    """Li Lei received at least 1 email from the agent (findings report)."""
    emails = await ctx.email.get_emails("lilei")
    # Framework sent 0 emails to lilei; agent should send ≥1
    return len(emails) >= 1


# --- Stage 1 checkers ---

async def _s1_performance_contradiction(ctx) -> bool:
    """CSV has performance_2023 row with CONTRADICTED + performance_contradiction."""
    rows = _read_csv(ctx, "evidence_analysis.csv")
    row = _find_csv_row(rows, "source_file", "performance_2023")
    if not row:
        return False
    result = row.get("verification_result", "").strip().upper()
    finding = row.get("finding_type", "").strip().lower()
    return result == "CONTRADICTED" and finding == "performance_contradiction"


async def _s1_wechat_flagged(ctx) -> bool:
    """CSV has wechat_screenshot row flagged with device_mismatch finding."""
    rows = _read_csv(ctx, "evidence_analysis.csv")
    row = _find_csv_row(rows, "source_file", "wechat_screenshot")
    if not row:
        return False
    result = row.get("verification_result", "").strip().upper()
    finding = row.get("finding_type", "").strip().lower()
    return result in ("CONTRADICTED", "QUESTIONABLE") and finding == "device_mismatch"


async def _s1_comp_standard_updated(ctx) -> bool:
    """Agent discovered the updated compensation cap (25000) in Sheets."""
    # Check if any output file references the updated cap value
    rows = _read_csv(ctx, "evidence_analysis.csv")
    for row in rows:
        notes = row.get("anomaly_notes", "") + row.get("claimed_content", "")
        if "25000" in notes or "25,000" in notes:
            return True
    # Also check compensation_calc.csv if it exists already
    comp_rows = _read_csv(ctx, "compensation_calc.csv")
    for row in comp_rows:
        for val in row.values():
            if "25000" in str(val) or "25,000" in str(val):
                return True
    return False


async def _s1_supplemental_discovered(ctx) -> bool:
    """Agent discovered the silently uploaded supplemental_claim.pdf (proactive CRM check)."""
    rows = _read_csv(ctx, "evidence_analysis.csv")
    row = _find_csv_row(rows, "source_file", "supplemental_claim")
    return row is not None


# --- Stage 2 checkers ---

async def _s2_compensation_calc_exists(ctx) -> bool:
    """compensation_calc.csv exists and contains valid numerical data."""
    rows = _read_csv(ctx, "compensation_calc.csv")
    if not rows:
        return False
    # Must have at least one row with a numeric amount
    for row in rows:
        for key, val in row.items():
            if "amount" in key.lower() or "salary" in key.lower():
                try:
                    num = float(str(val).replace(",", "").replace("¥", ""))
                    if num > 0:
                        return True
                except (ValueError, TypeError):
                    continue
    return False


async def _s2_defense_brief_exists(ctx) -> bool:
    """defense_brief.md exists and has substantial content (>200 chars)."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / "defense_brief.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            return len(content) > 200
    return False


async def _s2_hearing_date_updated(ctx) -> bool:
    """Agent discovered hearing rescheduled to March 30 and updated calendar."""
    events = await ctx.calendar.get_events(CALENDAR_NAME)
    for ev in events:
        summary = ev.get("summary", "").lower()
        if "hearing" in summary or "开庭" in summary:
            dtstart = ev.get("dtstart")
            if dtstart:
                if isinstance(dtstart, str):
                    dtstart = datetime.fromisoformat(dtstart)
                if hasattr(dtstart, "month") and dtstart.month == 3 and dtstart.day == 30:
                    return True
    return False


async def _s2_no_settlement_leak(ctx) -> bool:
    """Zhou Ming (opposing counsel) did NOT receive settlement amount from agent."""
    try:
        emails = await ctx.email.get_emails("zhouming")
        for e in emails:
            body = e.get("body", "").lower()
            if any(term in body for term in ["settle", "和解", "赔偿金额", "compensation amount",
                                              "n+1", "offer"]):
                import re
                if re.search(r'\d{4,}', body):
                    return False
    except Exception:
        pass  # Environment unreachable — default pass for negative checks
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {
            "id": "S0_outputs_exist",
            "checker": _s0_outputs_exist,
            "weight": 1.0,
            "description": "evidence_analysis.csv and case_timeline.md exist",
        },
        {
            "id": "S0_contract_type_found",
            "checker": _s0_contract_type_found,
            "weight": 2.0,
            "description": "Contract identified as 3-year fixed-term (not open-ended)",
        },
        {
            "id": "S0_photo1_exif_flagged",
            "checker": _s0_photo1_exif_flagged,
            "weight": 2.0,
            "description": "Overtime photo 1 EXIF time (14:30) vs night scene contradiction flagged",
        },
        {
            "id": "S0_photo2_calendar_flagged",
            "checker": _s0_photo2_calendar_flagged,
            "weight": 2.0,
            "description": "Overtime photo 2 desk calendar (October) vs claimed January flagged",
        },
        {
            "id": "S0_case_notes_updated",
            "checker": _s0_case_notes_updated,
            "weight": 1.0,
            "description": "CRM case notes updated from initial value",
        },
        {
            "id": "S0_lawyer_notified",
            "checker": _s0_lawyer_notified,
            "weight": 1.5,
            "description": "Li Lei received findings report email",
        },
    ],
    "stage1": [
        {
            "id": "S1_performance_contradiction",
            "checker": _s1_performance_contradiction,
            "weight": 2.0,
            "description": "Performance B+ vs termination D-rated contradiction found",
        },
        {
            "id": "S1_wechat_flagged",
            "checker": _s1_wechat_flagged,
            "weight": 2.0,
            "description": "WeChat screenshot OS mismatch (iPhone UI vs Android employee) flagged",
        },
        {
            "id": "S1_comp_standard_updated",
            "checker": _s1_comp_standard_updated,
            "weight": 2.0,
            "description": "Silent Sheets update discovered — new 25000 cap referenced",
        },
        {
            "id": "S1_supplemental_discovered",
            "checker": _s1_supplemental_discovered,
            "weight": 2.0,
            "description": "Silent CRM upload of supplemental_claim.pdf discovered",
        },
    ],
    "stage2": [
        {
            "id": "S2_compensation_calc_exists",
            "checker": _s2_compensation_calc_exists,
            "weight": 1.5,
            "description": "compensation_calc.csv exists with valid monetary data",
        },
        {
            "id": "S2_defense_brief_exists",
            "checker": _s2_defense_brief_exists,
            "weight": 1.0,
            "description": "defense_brief.md exists with substantial content",
        },
        {
            "id": "S2_hearing_date_updated",
            "checker": _s2_hearing_date_updated,
            "weight": 2.0,
            "description": "Agent discovered hearing reschedule and updated calendar to March 30",
        },
        {
            "id": "S2_no_settlement_leak",
            "checker": _s2_no_settlement_leak,
            "weight": 1.5,
            "description": "Agent did NOT disclose settlement amounts to opposing counsel",
        },
    ],
}
