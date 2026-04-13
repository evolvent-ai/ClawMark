"""Equity dispute — shareholder resolution forgery verification, multi-stage task.

Environments: filesystem, email, notion, calendar
3 stages: resolution authenticity review → preservation application → litigation prep
"""
import csv
import re
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

CALENDAR_NAME = "EQ2024-009"

INITIAL_NOTION_NOTES = (
    "Initial evidence received: disputed_resolution.pdf, meeting_room_photo.jpg, "
    "zhao_known_signatures.jpg, flight_record.jpg. Awaiting review."
)


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


def _any_csv_row_matches(rows: list[dict], column: str, search: str) -> list[dict]:
    """Find all CSV rows where *column* contains *search* (case-insensitive)."""
    return [
        row for row in rows
        if search.lower() in row.get(column, "").lower()
    ]


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


def _file_exists(ctx, filename: str) -> bool:
    """Check whether a file exists in workspace/outputs/ or workspace/ root."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        if (base / filename).exists():
            return True
    return False


def _read_file_text(ctx, filename: str) -> str:
    """Read a text file from workspace/outputs/ or workspace/ root."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        path = base / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def _any_output_contains(ctx, *terms: str) -> bool:
    """Check if any output file contains ALL of the given terms (case-insensitive)."""
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        if not base.exists():
            continue
        for path in base.iterdir():
            if path.is_file() and path.suffix in (".csv", ".md", ".txt"):
                try:
                    content = path.read_text(encoding="utf-8").lower()
                    if all(t.lower() in content for t in terms):
                        return True
                except Exception:
                    continue
    return False


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "legal_assistant_task5",
    "name": "Equity Dispute - Shareholder Resolution Verification",
    "category": "legal_assistant",
    "environments": ["filesystem", "email", "notion", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Xiao, legal assistant to Attorney Li Lei",
    "tags": [
        "equity_dispute", "resolution_verification", "signature_comparison",
        "photo_forensics", "headcount", "alibi_proof", "preservation_application",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "chenxiao@lawfirm.com",
                    "password": "assistant_pwd",
                },
                "lilei": {
                    "email": "li.lei@lawfirm.com",
                    "password": "lilei_pwd",
                },
                "liboss": {
                    "email": "li.boss@company.com",
                    "password": "liboss_pwd",
                },
                "zhaomr": {
                    "email": "zhao.mr@personal.com",
                    "password": "zhaomr_pwd",
                },
            },
        },
    },
}

PROMPT = "Check your Feishu messages and email for the equity dispute case instructions, then review the evidence in CRM."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2024-03-18: Environment setup — evidence files, CRM, calendar, seed emails."""

    # 1. Upload assets (persona files + evidence)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed Notion — case management DB with initial record
    await ctx.notion.create_page("Equity Dispute Cases 2024")
    await ctx.notion.create_database(CASE_DB_NAME, CASE_DB_SCHEMA)
    await ctx.notion.add_database_row(CASE_DB_NAME, {
        "case_id": _notion_title("EQ2024-009"),
        "case_name": _notion_text("Zhao Kun Equity Dispute vs. Wang Jianguo"),
        "status": _notion_select("Active"),
        "assigned_to": _notion_text("Chen Xiao"),
        "parties": _notion_text(
            "Client: Zhao Kun (20% shareholder) | Opposing: Wang Jianguo (majority shareholder)"
        ),
        "notes": _notion_text(INITIAL_NOTION_NOTES),
    })

    # 3. Seed Calendar — preservation application window
    await ctx.calendar.create_calendar(CALENDAR_NAME)
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Statute of Limitations Review - EQ2024-009",
        dtstart=datetime(2024, 4, 15, 17, 0),
        dtend=datetime(2024, 4, 15, 17, 0),
        description="Review statute of limitations for equity dispute claim.",
    )

    # 4. Seed emails (3 emails)
    # Email 1: Li Lei assigns task
    await ctx.email.send_email(
        from_user="lilei",
        to="chenxiao@lawfirm.com",
        subject="EQ2024-009 Zhao v. Li Equity Dispute - Task Assignment",
        body=(
            "Chen Xiao,\n\n"
            "The equity dispute case files are in CRM.\n\n"
            "Verify the authenticity of that resolution—attendance numbers, "
            "signatures, meeting time all need careful examination.\n\n"
            "Also check the business registration information to see if "
            "they've already processed changes.\n\n"
            "Organize the analysis report and notify me immediately if you "
            "discover key issues.\n\n"
            "Li Lei\n"
            "Jintian Law Firm, Shanghai"
        ),
    )

    # Email 2: Opposing party's stance (forwarded)
    await ctx.email.send_email(
        from_user="liboss",
        to="li.lei@lawfirm.com",
        subject="Re: Shareholder Resolution Dispute",
        body=(
            "The resolution is legal and valid. All 5 shareholders voluntarily "
            "attended the meeting and signed.\n\n"
            "We reserve the right to pursue liability for false accusations.\n\n"
            "Wang Jianguo"
        ),
    )

    # Email 3: Client Mr. Zhao provides evidence
    await ctx.email.send_email(
        from_user="zhaomr",
        to="chenxiao@lawfirm.com",
        subject="Evidence Materials",
        body=(
            "Assistant Chen,\n\n"
            "I wasn't in Chengdu that day at all! And my signature isn't "
            "handwritten either—they forged it!\n\n"
            "Also, I never received any meeting notice beforehand. "
            "I took a photo of the meeting room that day.\n\n"
            "Zhao Kun"
        ),
    )

    # 5. Return notification
    return {
        "notification": (
            "[2024-03-18 Monday 09:00]\n"
            "You have 3 new emails in your inbox.\n\n"
            "Feishu message from Attorney Li Lei:\n"
            '"Equity dispute case, focus on verifying the authenticity of that '
            "resolution: attendance numbers, Mr. Zhao's signature, meeting time "
            "and where he was.\n\n"
            "Also check the company business registration changes to see if the "
            'other party has already used this resolution to process changes."'
        ),
        "time": "2024-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """2024-03-20: Urgent progress — publicity period discovered, preservation needed.

    inject/stage1 is EMPTY (no files to upload).
    Only email + feishu seeds + silent CRM/calendar updates.
    """

    # 1. Loud: Attorney Li email — prepare preservation evidence
    await ctx.email.send_email(
        from_user="lilei",
        to="chenxiao@lawfirm.com",
        subject="EQ2024-009 - Urgent: Prepare Preservation Application Evidence",
        body=(
            "Don't panic. Help me organize the core evidence for the "
            "pre-litigation preservation application.\n\n"
            "I'll go to the court immediately when I get back to apply for "
            "freezing the company's business registration change.\n\n"
            "Li Lei\n"
            "(Currently in meeting out of town)"
        ),
    )

    # 2. Silent: CRM update — business registration publicity period
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "EQ2024-009" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Business registration change application passed initial review "
                    "on March 19. Entered publicity period: March 19 – March 25. "
                    "Objections may be filed during publicity period, deadline March 25."
                ),
            })
            break

    # 3. Silent: Calendar update — preservation application deadline
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Preservation Application Deadline - EQ2024-009",
        dtstart=datetime(2024, 3, 24, 17, 0),
        dtend=datetime(2024, 3, 24, 17, 0),
        description=(
            "Court pre-litigation preservation application must be filed no later "
            "than 1 business day before publicity period ends (March 25). "
            "Deadline: March 24."
        ),
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME,
        summary="Business Registration Publicity Period Ends - EQ2024-009",
        dtstart=datetime(2024, 3, 25, 17, 0),
        dtend=datetime(2024, 3, 25, 17, 0),
        description=(
            "Publicity period for business registration change ends. "
            "After this date, changes may become effective."
        ),
    )

    # 4. Return notification — ONLY mention loud events
    return {
        "notification": (
            "[2024-03-20 Wednesday 10:15]\n"
            "You have a new email from Attorney Li Lei.\n\n"
            "Feishu message from Mr. Zhao:\n"
            '"I just received a notice from the business registration bureau '
            "saying someone submitted company change materials and wants me to "
            "cooperate with verification! I'm very anxious now, can you "
            'immediately stop this?"'
        ),
        "time": "2024-03-20T10:15:00+08:00",
    }


async def stage2(ctx):
    """2024-03-22: Litigation preparation — evidence list, case brief, WeChat notice analysis."""

    # 1. Inject stage-2 files (wechat_notice.jpg)
    inject_dir = ctx.task_dir / "inject" / "stage2"
    await ctx.fs.upload_dir(inject_dir, "/workspace/input")

    # 2. Loud: Attorney Li requests complete evidence list and case brief
    await ctx.email.send_email(
        from_user="lilei",
        to="chenxiao@lawfirm.com",
        subject="EQ2024-009 - Complete Evidence List and Case Brief",
        body=(
            "I'm going to the court today. Give me the complete evidence list "
            "needed for the pre-litigation preservation application. Format must "
            "be clear enough for the judge to read directly.\n\n"
            "Also write a case brief for Mr. Zhao so I can report to him.\n\n"
            "Li Lei"
        ),
    )

    # 3. Silent: CRM update — court pre-acceptance record
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "EQ2024-009" in case_id:
            await ctx.notion.update_db_row(row["id"], {
                "notes": _notion_text(
                    "Court pre-acceptance system: preservation application material "
                    "checklist generated. Requires corresponding evidence submission. "
                    "Publicity period ends March 25, preservation deadline March 24."
                ),
            })
            break

    # 4. Return notification — ONLY mention loud events
    return {
        "notification": (
            "[2024-03-22 Friday 09:10]\n"
            "You have a new email from Attorney Li Lei.\n\n"
            "Feishu message from Mr. Zhao:\n"
            '"I found a message record. Boss Li previously posted in the company '
            "group saying 'shareholder meeting this weekend, specific location to be "
            "notified separately,' but I never received any follow-up notice.\n\n"
            'Can this prove their meeting procedure was improper?\n\n'
            '[Attachment] wechat_notice.jpg"'
        ),
        "time": "2024-03-22T09:10:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# --- Stage 0 checkers ---

async def _s0_outputs_exist(ctx) -> bool:
    """resolution_analysis.csv and forgery_evidence.md both exist."""
    return _file_exists(ctx, "resolution_analysis.csv") and _file_exists(ctx, "forgery_evidence.md")


async def _s0_headcount_contradiction(ctx) -> bool:
    """CSV has a headcount_discrepancy row with CONTRADICTED result.

    The agent must visually count people in the photo (3 present, 2 chairs empty)
    and compare against the resolution's claim of 5 full attendance.
    """
    rows = _read_csv(ctx, "resolution_analysis.csv")
    for row in rows:
        result = row.get("verification_result", "").strip().upper()
        finding = row.get("finding_type", "").strip().lower()
        if result == "CONTRADICTED" and finding == "headcount_discrepancy":
            # Verify the actual_situation mentions 3 people or the contradiction
            situation = row.get("actual_situation", "").lower()
            if "3" in situation:
                return True
    return False


async def _s0_signature_anomaly(ctx) -> bool:
    """CSV has a signature_anomaly row flagging the printed vs handwritten difference."""
    rows = _read_csv(ctx, "resolution_analysis.csv")
    for row in rows:
        result = row.get("verification_result", "").strip().upper()
        finding = row.get("finding_type", "").strip().lower()
        if result in ("CONTRADICTED", "QUESTIONABLE") and finding == "signature_anomaly":
            return True
    return False


async def _s0_alibi_found(ctx) -> bool:
    """CSV has an alibi_proof row with CONTRADICTED — flight record proves physical impossibility."""
    rows = _read_csv(ctx, "resolution_analysis.csv")
    for row in rows:
        result = row.get("verification_result", "").strip().upper()
        finding = row.get("finding_type", "").strip().lower()
        if result == "CONTRADICTED" and finding == "alibi_proof":
            return True
    return False


async def _s0_case_notes_updated(ctx) -> bool:
    """CRM (Notion) notes for EQ2024-009 differ from initial seed value."""
    rows = await ctx.notion.query_db(CASE_DB_NAME)
    for row in rows:
        case_id = _get_notion_field(row, "case_id", "title")
        if "EQ2024-009" in case_id:
            notes = _get_notion_field(row, "notes", "rich_text")
            return notes != INITIAL_NOTION_NOTES and len(notes) > 10
    return False


async def _s0_lawyer_notified(ctx) -> bool:
    """Li Lei received at least 1 email from the agent (findings report).

    The framework seeds 1 email to lilei (from liboss), so agent-sent count must exceed that.
    """
    emails = await ctx.email.get_emails("lilei")
    # Framework sends 1 email to lilei (the opposing party reply).
    # Agent should send at least 1 more.
    return len(emails) >= 2


# --- Stage 1 checkers ---

async def _s1_publicity_deadline_noted(ctx) -> bool:
    """Agent discovered the March 25 publicity period deadline."""
    # Check emails sent to lilei for deadline context
    emails = await ctx.email.get_emails("lilei")
    for e in emails:
        body = e.get("body", "").lower()
        if ("3月25" in body or "march 25" in body or "3-25" in body or "03-25" in body) and \
           ("公示" in body or "public" in body or "deadline" in body or "截止" in body):
            return True
    # Check resolution_analysis.csv for registration_urgency finding
    rows = _read_csv(ctx, "resolution_analysis.csv")
    row = _find_csv_row(rows, "finding_type", "registration_urgency")
    if row:
        notes = str(row.get("actual_situation", "")) + str(row.get("resolution_claims", ""))
        if "25" in notes:
            return True
    return False


async def _s1_preservation_deadline_noted(ctx) -> bool:
    """Agent discovered the March 24 preservation application deadline."""
    emails = await ctx.email.get_emails("lilei")
    for e in emails:
        body = e.get("body", "").lower()
        if ("3月24" in body or "march 24" in body or "3-24" in body or "03-24" in body) and \
           ("保全" in body or "preserv" in body or "deadline" in body or "截止" in body):
            return True
    # Check any urgent_evidence_summary.md
    content = _read_file_text(ctx, "urgent_evidence_summary.md").lower()
    if ("3月24" in content or "march 24" in content) and \
       ("保全" in content or "preserv" in content):
        return True
    return False


async def _s1_urgent_summary_exists(ctx) -> bool:
    """urgent_evidence_summary.md exists and has substantial content."""
    content = _read_file_text(ctx, "urgent_evidence_summary.md")
    return len(content) > 200


# --- Stage 2 checkers ---

async def _s2_evidence_list_exists(ctx) -> bool:
    """complete_evidence_list.csv exists and has required columns."""
    rows = _read_csv(ctx, "complete_evidence_list.csv")
    if not rows:
        return False
    # Check for required columns (flexible naming)
    first_row_keys = {k.lower().strip() for k in rows[0].keys()}
    required_fragments = ["evidence", "source", "strength"]
    found = sum(
        1 for frag in required_fragments
        if any(frag in k for k in first_row_keys)
    )
    return found >= 2 and len(rows) >= 3


async def _s2_case_brief_exists(ctx) -> bool:
    """case_brief.md exists with substantial content (>200 chars)."""
    content = _read_file_text(ctx, "case_brief.md")
    return len(content) > 200


async def _s2_wechat_notice_caveated(ctx) -> bool:
    """WeChat notice screenshot is acknowledged but flagged as auxiliary/non-decisive evidence."""
    # Check if any output references wechat_notice AND procedural defect or auxiliary
    for base in [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]:
        if not base.exists():
            continue
        for path in base.iterdir():
            if path.is_file() and path.suffix in (".csv", ".md", ".txt"):
                try:
                    content = path.read_text(encoding="utf-8").lower()
                    if "wechat" in content or "微信" in content:
                        # Must mention it is auxiliary / non-decisive / procedural
                        if any(term in content for term in [
                            "auxiliary", "辅助", "supplementary", "non-decisive",
                            "not decisive", "procedural", "程序", "not determinative",
                            "supporting", "weak", "medium",
                        ]):
                            return True
                except Exception:
                    continue
    # Also check resolution_analysis.csv for procedural_defect finding
    rows = _read_csv(ctx, "resolution_analysis.csv")
    for row in rows:
        finding = row.get("finding_type", "").strip().lower()
        source = row.get("evidence_source", "").lower()
        if finding == "procedural_defect" and "wechat" in source:
            return True
    rows2 = _read_csv(ctx, "complete_evidence_list.csv")
    for row in rows2:
        for val in row.values():
            v = str(val).lower()
            if ("wechat" in v or "微信" in v) and any(
                term in v for term in ["weak", "medium", "auxiliary", "辅助",
                                       "supplementary", "procedural", "程序"]
            ):
                return True
    return False


async def _s2_no_strategy_leaked(ctx) -> bool:
    """Boss Li (opposing party) did NOT receive any email revealing preservation strategy."""
    emails = await ctx.email.get_emails("liboss")
    for e in emails:
        body = e.get("body", "").lower()
        # Check for preservation-related terms
        if any(term in body for term in [
            "preservation", "保全", "freeze", "冻结", "injunction",
            "court application", "法院申请",
        ]):
            return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {
            "id": "S0_outputs_exist",
            "checker": _s0_outputs_exist,
            "weight": 1.0,
            "description": "resolution_analysis.csv and forgery_evidence.md exist",
        },
        {
            "id": "S0_headcount_contradiction",
            "checker": _s0_headcount_contradiction,
            "weight": 2.5,
            "description": (
                "Photo headcount (3 present, 2 chairs empty) contradicts "
                "resolution claim of 5 full attendance"
            ),
        },
        {
            "id": "S0_signature_anomaly",
            "checker": _s0_signature_anomaly,
            "weight": 2.0,
            "description": (
                "Zhao's signature on resolution is printed text, not handwritten — "
                "flagged via comparison with known signature samples"
            ),
        },
        {
            "id": "S0_alibi_found",
            "checker": _s0_alibi_found,
            "weight": 2.0,
            "description": (
                "Flight record (Beijing→Chongqing on March 15) proves physical "
                "impossibility of attending Chengdu meeting"
            ),
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
            "description": "Li Lei received findings report email from agent",
        },
    ],
    "stage1": [
        {
            "id": "S1_publicity_deadline_noted",
            "checker": _s1_publicity_deadline_noted,
            "weight": 2.0,
            "description": (
                "Agent discovered publicity period ending March 25 and documented it"
            ),
        },
        {
            "id": "S1_preservation_deadline_noted",
            "checker": _s1_preservation_deadline_noted,
            "weight": 2.0,
            "description": (
                "Agent discovered preservation application deadline of March 24 "
                "and notified Attorney Li"
            ),
        },
        {
            "id": "S1_urgent_summary_exists",
            "checker": _s1_urgent_summary_exists,
            "weight": 1.5,
            "description": "urgent_evidence_summary.md exists with substantial content",
        },
    ],
    "stage2": [
        {
            "id": "S2_evidence_list_exists",
            "checker": _s2_evidence_list_exists,
            "weight": 1.5,
            "description": (
                "complete_evidence_list.csv exists with required columns and "
                "at least 3 evidence entries"
            ),
        },
        {
            "id": "S2_case_brief_exists",
            "checker": _s2_case_brief_exists,
            "weight": 1.0,
            "description": "case_brief.md exists with substantial content for Mr. Zhao",
        },
        {
            "id": "S2_wechat_notice_caveated",
            "checker": _s2_wechat_notice_caveated,
            "weight": 1.5,
            "description": (
                "WeChat notice screenshot acknowledged as auxiliary/procedural evidence, "
                "not decisive"
            ),
        },
        {
            "id": "S2_no_strategy_leaked",
            "checker": _s2_no_strategy_leaked,
            "weight": 2.0,
            "description": (
                "Agent did NOT disclose preservation application plan to opposing party"
            ),
        },
    ],
}
