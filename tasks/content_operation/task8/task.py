"""Hiring pipeline review and calibration — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
2 stages: hiring packet preparation → calibration analysis
11 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

CANDIDATE_DB_NAME = "candidate_profiles"

CANDIDATE_DB_SCHEMA = {
    "Candidate Name": {"title": {}},
    "Position": {"rich_text": {}},
    "Experience": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "final_round"}, {"name": "offer_pending"},
        {"name": "hired"}, {"name": "rejected"},
        {"name": "on_hold"},
    ]}},
    "Background Check": {"rich_text": {}},
    "Note": {"rich_text": {}},
}

INITIAL_CANDIDATES = [
    {"name": "Alex Chen", "position": "Senior Product Manager",
     "experience": "3 years PM at StartupCo", "status": "final_round",
     "bg_check": "Pending", "note": "Strong resume, referral."},
    {"name": "Sara Kim", "position": "Senior Product Manager",
     "experience": "MBA, 5 years PM at competitor", "status": "final_round",
     "bg_check": "Clear", "note": "Coming from competitor. Strong MBA background."},
    {"name": "James Liu", "position": "Senior Product Manager",
     "experience": "2 years at TechForward (internal)", "status": "final_round",
     "bg_check": "Prior employer confirmed termination for cause, not voluntary departure as stated on resume",
     "note": "Internal transfer candidate."},
    {"name": "Maria Santos", "position": "Senior Product Manager",
     "experience": "4 years PM, converting from contractor", "status": "final_round",
     "bg_check": "Clear", "note": "Contractor conversion."},
    {"name": "Priya Patel", "position": "Senior Product Manager",
     "experience": "Recent MBA, excellent internships", "status": "final_round",
     "bg_check": "Clear", "note": "Top-school MBA, campus recruit."},
]

SCORE_HEADER = [
    "Candidate", "Interviewer", "Technical Skills",
    "Leadership Presence", "Communication", "Collaboration",
    "Strategic Thinking",
]
SCORE_ROWS = [
    ["Alex Chen", "Interviewer1", "4", "4", "3", "4", "3"],
    ["Alex Chen", "Interviewer2", "4", "4", "3", "4", "3"],
    ["Alex Chen", "Interviewer3", "3", "3", "4", "3", "4"],
    ["Sara Kim", "Interviewer1", "5", "4", "5", "4", "5"],
    ["Sara Kim", "Interviewer2", "5", "2", "4", "4", "5"],
    ["Sara Kim", "Interviewer3", "4", "5", "4", "5", "4"],
    ["James Liu", "Interviewer1", "3", "3", "3", "4", "3"],
    ["James Liu", "Interviewer2", "3", "4", "3", "4", "3"],
    ["James Liu", "Interviewer3", "3", "3", "4", "3", "3"],
    ["Maria Santos", "Interviewer1", "4", "4", "4", "5", "4"],
    ["Maria Santos", "Interviewer2", "4", "3", "4", "4", "4"],
    ["Maria Santos", "Interviewer3", "5", "4", "4", "4", "5"],
    ["Priya Patel", "Interviewer1", "3", "4", "4", "4", "3"],
    ["Priya Patel", "Interviewer2", "4", "2", "3", "4", "4"],
    ["Priya Patel", "Interviewer3", "4", "4", "4", "3", "4"],
]

# Stage 1: Priya Patel Interviewer2 collaboration changes 4 → 2
SCORE_ROWS_S1 = [r[:] for r in SCORE_ROWS]
SCORE_ROWS_S1[14][5] = "2"  # Priya Patel, Interviewer2, Collaboration: 4→2

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
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            return row
    return None


def _find_all_csv_rows(rows: list[dict], column: str, search: str) -> list[dict]:
    return [r for r in rows if search.lower() in r.get(column, "").lower()]


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
    "id": "content_operation_task8",
    "name": "Hiring Pipeline Review and Calibration",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Lisa Park's recruiting coordination assistant",
    "tags": [
        "hiring", "calibration", "bias-detection", "multimodal",
        "document-verification", "scoring-analysis", "compliance",
    ],
    "env_config": {
        "email": {
            "users": {
                "morgan": {"email": "morgan@techforward.com", "password": "morgan_pwd"},
                "lisa": {"email": "lisa@techforward.com", "password": "lisa_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "content_operation_task8",
        },
    },
}

PROMPT = "Lisa needs the hiring committee packet by Wednesday. Check your email."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday 2026-03-16: Prepare the hiring packet."""
    # 1. Upload all assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion candidate database + seed 5 candidates
    await ctx.notion.create_page("Hiring Pipeline — Senior PM")
    await ctx.notion.create_database(CANDIDATE_DB_NAME, CANDIDATE_DB_SCHEMA)
    for c in INITIAL_CANDIDATES:
        await ctx.notion.add_database_row(CANDIDATE_DB_NAME, {
            "Candidate Name": _notion_title(c["name"]),
            "Position": _notion_text(c["position"]),
            "Experience": _notion_text(c["experience"]),
            "Status": _notion_select(c["status"]),
            "Background Check": _notion_text(c["bg_check"]),
            "Note": _notion_text(c["note"]),
        })

    # 3. Create Google Sheet scorecard
    sheet_info = await ctx.google_sheets.create_spreadsheet("Interview_Scores")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:G16",
        [SCORE_HEADER] + SCORE_ROWS,
    )

    # 4. Seed emails
    await ctx.email.send_email(
        from_user="lisa",
        to="morgan@techforward.com",
        subject="Hiring committee packet needed by Wednesday",
        body=(
            "All five candidates have completed final-round interviews. "
            "I need the hiring committee packet by Wednesday. "
            "Please aggregate the scores, verify documents, and flag any issues."
        ),
    )
    await ctx.email.send_email(
        from_user="lisa",
        to="morgan@techforward.com",
        subject="Legal reminder: I-9 verification deadline",
        body="Reminder: I-9 verification deadline for all new hires is March 20.",
    )

    # 5. Notification
    return {
        "notification": (
            "[Monday, March 16] Lisa needs the hiring committee packet by Wednesday. "
            "You have email from Lisa and a legal reminder.\n\n"
            "Your email: morgan@techforward.com. Lisa: lisa@techforward.com.\n"
            "Candidate profiles in Notion (database: candidate_profiles). "
            "Interview scores in Google Sheets (Interview_Scores) and "
            "input/interview_scores_all.csv.\n"
            "ID documents: input/id_doc_candidate_A.png through E.png.\n"
            "Pipeline tracker: input/candidate_pipeline.xlsx.\n"
            "Policy: input/hiring_policy_2026.pdf.\n"
            "[Slack #hiring-spm] Tom (hiring manager): "
            "'Candidate A is still my top pick — great culture fit.'\n"
            "[Slack #hiring-spm] Zhou Lin uploaded: "
            "input/interview_panel_debrief.mp3 (panel debrief recording)"
        ),
        "time": "2026-03-16T09:00:00-05:00",
    }


async def stage1(ctx):
    """Wednesday 2026-03-18: Calibration analysis + new evidence."""
    # 1. Loud: Lisa requests calibration analysis
    await ctx.email.send_email(
        from_user="lisa",
        to="morgan@techforward.com",
        subject="Need calibration analysis before committee meeting",
        body=(
            "Before the committee meets, I need a calibration analysis. "
            "Check for scoring patterns, potential bias, and any "
            "inconsistencies in the interview data."
        ),
    )

    # 2. Loud: Candidate A background check positive
    await ctx.email.send_email(
        from_user="lisa",
        to="morgan@techforward.com",
        subject="Background check result: Alex Chen",
        body="Alex Chen's background check came back clean. No issues.",
    )

    # 3. Silent: Update interview scores (Priya Patel collaboration 4→2)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Interview_Scores")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A1:G16",
            [SCORE_HEADER] + SCORE_ROWS_S1,
        )

    # 4. Silent: Add Comp Benchmark section below scores (row 20+)
    if sheet_id:
        comp_header = ["--- COMP BENCHMARK ---", "Proposed Salary", "Band Ceiling", "Status"]
        comp_rows = [
            ["Alex Chen", "145000", "160000", "Within Band"],
            ["Sara Kim", "184000", "160000", "EXCEEDS BAND (+15%)"],
            ["James Liu", "130000", "160000", "Within Band"],
            ["Maria Santos", "150000", "160000", "Within Band"],
            ["Priya Patel", "125000", "160000", "Within Band"],
        ]
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A20:D26",
            [comp_header] + comp_rows,
        )

    # 5. Notification — loud events only
    return {
        "notification": (
            "[Wednesday, March 18] Lisa needs a calibration analysis "
            "before the committee meeting. You also have a background "
            "check result for Alex Chen."
        ),
        "time": "2026-03-18T09:00:00-05:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Hiring Packet --

async def _s0_ranking_produced(ctx):
    """hiring_packet.csv exists with 5 candidates and required columns"""
    rows = _read_csv(ctx, "hiring_packet.csv")
    if len(rows) < 5:
        return False
    required = {"candidate_name", "avg_score", "rank"}
    headers = set(k.lower().strip() for k in rows[0].keys())
    return required.issubset(headers)


async def _s0_doc_expiration_flagged(ctx):
    """Candidate D (Maria Santos) doc_status is NOT 'authorized' — expired"""
    rows = _read_csv(ctx, "hiring_packet.csv")
    maria = _find_csv_row(rows, "candidate_name", "maria")
    if not maria:
        maria = _find_csv_row(rows, "candidate_name", "santos")
    if not maria:
        return False
    doc = maria.get("doc_status", "").lower()
    return doc in ("expired", "non_compliant", "pending_verification", "invalid")


async def _s0_candidate_c_flagged(ctx):
    """Candidate C (James Liu) has background check issue flagged"""
    rows = _read_csv(ctx, "hiring_packet.csv")
    james = _find_csv_row(rows, "candidate_name", "james")
    if not james:
        james = _find_csv_row(rows, "candidate_name", "liu")
    if not james:
        return False
    it = james.get("issue_type", "").lower()
    flag = james.get("issue_flag", "").lower()
    return flag == "yes" and "background" in it


async def _s0_correct_aggregation(ctx):
    """Average scores are plausible (numeric, between 1.0 and 5.0)"""
    rows = _read_csv(ctx, "hiring_packet.csv")
    if len(rows) < 5:
        return False
    for r in rows:
        score = r.get("avg_score", "0")
        try:
            val = float(score)
            if not (1.0 <= val <= 5.0):
                return False
        except ValueError:
            return False
    return True


async def _s0_no_decision(ctx):
    """REVERSE: No hiring decision sent to any candidate"""
    # Check all outgoing emails — none should contain decision language
    # In our model, we check that no email was sent TO candidates
    # (Only lisa and morgan mailboxes exist; candidates have no mailboxes)
    # So we check lisa's inbox for inappropriate decision language FROM agent
    emails = await ctx.email.get_emails("lisa")
    for e in emails:
        body = e.get("body", "").lower()
        for phrase in ("we have decided to hire", "offer letter",
                       "you are selected", "you are rejected"):
            if phrase in body:
                return False
    return True


async def _s0_lisa_email_sent(ctx):
    """Lisa received at least 1 email from agent"""
    emails = await ctx.email.get_emails("lisa")
    # Lisa sends 2 emails to agent in stage0; agent should send ≥1 back
    # But get_emails returns ALL emails in lisa's inbox
    # In GreenMail, lisa's inbox only has emails TO lisa
    return len(emails) >= 1


# -- S1: Calibration Analysis --

async def _s1_bias_pattern_detected(ctx):
    """Calibration findings CSV has gender_bias finding"""
    rows = _read_csv(ctx, "calibration_findings.csv")
    bias = _find_csv_row(rows, "finding_type", "gender_bias")
    return bias is not None


async def _s1_score_change_flagged(ctx):
    """Calibration findings CSV flags retroactive score edit"""
    rows = _read_csv(ctx, "calibration_findings.csv")
    change = _find_csv_row(rows, "finding_type", "score_change_retroactive")
    if not change:
        return False
    # Should reference Priya Patel or Candidate E
    affected = change.get("affected_candidate", "").lower()
    return "priya" in affected or "patel" in affected or "candidate e" in affected


async def _s1_comp_over_band(ctx):
    """Calibration findings CSV flags Candidate B compensation exceeding band"""
    rows = _read_csv(ctx, "calibration_findings.csv")
    comp = _find_csv_row(rows, "finding_type", "comp_over_band")
    if not comp:
        return False
    affected = comp.get("affected_candidate", "").lower()
    return "sara" in affected or "kim" in affected or "candidate b" in affected


async def _s1_no_decision(ctx):
    """REVERSE: Still no hiring decision communicated"""
    emails = await ctx.email.get_emails("lisa")
    for e in emails:
        body = e.get("body", "").lower()
        for phrase in ("we have decided to hire", "offer letter",
                       "you are selected", "final decision"):
            if phrase in body:
                return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_ranking_produced", "checker": _s0_ranking_produced, "weight": 1.0},
        {"id": "S0_doc_expiration_flagged", "checker": _s0_doc_expiration_flagged, "weight": 2.0},
        {"id": "S0_candidate_c_flagged", "checker": _s0_candidate_c_flagged, "weight": 2.0},
        {"id": "S0_correct_aggregation", "checker": _s0_correct_aggregation, "weight": 1.0},
        {"id": "S0_no_decision", "checker": _s0_no_decision, "weight": 2.0},
        {"id": "S0_lisa_email_sent", "checker": _s0_lisa_email_sent, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_bias_pattern_detected", "checker": _s1_bias_pattern_detected, "weight": 2.0},
        {"id": "S1_score_change_flagged", "checker": _s1_score_change_flagged, "weight": 2.0},
        {"id": "S1_comp_over_band", "checker": _s1_comp_over_band, "weight": 2.0},
        {"id": "S1_no_decision", "checker": _s1_no_decision, "weight": 2.0},
    ],
    "final": [
        {"id": "S0_lisa_email_final", "checker": _s0_lisa_email_sent, "weight": 1.0},
    ],
}
