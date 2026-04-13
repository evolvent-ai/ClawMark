"""Task 13 — Executive Background Check Cross-Validation.

The agent must cross-validate an executive candidate's resume against degree
evidence, reference audio, a public profile, and a certificate verification
tool.  Across three stages the agent records risk findings, executes a lateral
hold on candidates from a flagged agency, and evaluates new exculpatory
evidence without prematurely clearing the candidate.
"""

from __future__ import annotations

import asyncio
import csv
import logging
from io import StringIO

logger = logging.getLogger(__name__)

# ── Notion schema & seed data ──────────────────────────────────────────────

CANDIDATE_DB_NAME = "Candidate Board"
CANDIDATE_DB_SCHEMA = {
    "Candidate": {"title": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "Background Check"},
                {"name": "Hold"},
                {"name": "Panel Interview"},
                {"name": "Cleared"},
                {"name": "Offer Approved"},
                {"name": "Rejected"},
            ],
        },
    },
    "Education Risk": {"rich_text": {}},
    "Title Risk": {"rich_text": {}},
    "Credential Risk": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}

INITIAL_CANDIDATES = [
    {
        "Candidate": "Alex Chen",
        "Status": "Background Check",
        "Education Risk": "",
        "Title Risk": "",
        "Credential Risk": "",
        "Notes": "Prior founder-reference check requested",
    },
    {
        "Candidate": "Priya Nair",
        "Status": "Background Check",
        "Education Risk": "",
        "Title Risk": "",
        "Credential Risk": "",
        "Notes": "Pending salary benchmark review",
    },
    {
        "Candidate": "Daniel Wu",
        "Status": "Panel Interview",
        "Education Risk": "",
        "Title Risk": "",
        "Credential Risk": "",
        "Notes": "HM asked for portfolio follow-up",
    },
    {
        "Candidate": "Mina Park",
        "Status": "Background Check",
        "Education Risk": "",
        "Title Risk": "",
        "Credential Risk": "",
        "Notes": "Initial screening complete",
    },
]

# ── Helpers ─────────────────────────────────────────────────────────────────


def _notion_title(v: str) -> dict:
    return {"title": [{"text": {"content": v}}]}


def _notion_text(v: str) -> dict:
    return {"rich_text": [{"text": {"content": v}}]}


def _notion_select(v: str) -> dict:
    return {"select": {"name": v}}


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        parts = prop.get("title", [])
        return "".join(p["text"]["content"] for p in parts if "text" in p)
    if field_type == "rich_text":
        parts = prop.get("rich_text", [])
        return "".join(p["text"]["content"] for p in parts if "text" in p)
    if field_type == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    return ""


async def _find_notion_row(ctx, db_name: str, candidate_name: str):
    rows = await ctx.notion.query_db(db_name)
    for row in rows:
        name = _get_notion_field(row, "Candidate", "title")
        if candidate_name.lower() in name.lower():
            return row
    return None


async def _send_email_with_retry(ctx, *, from_user, to, subject, body, retries=3, delay=3):
    """Send email with retry to handle greenmail startup race."""
    for attempt in range(retries):
        ok = await ctx.email.send_email(
            from_user=from_user, to=to, subject=subject, body=body,
        )
        if ok:
            return True
        if attempt < retries - 1:
            logger.warning("Email send failed (attempt %d/%d), retrying...", attempt + 1, retries)
            await asyncio.sleep(delay)
    logger.error("Email send failed after %d attempts: %s -> %s", retries, from_user, to)
    return False


async def _get_emails_with_retry(ctx, user: str, retries: int = 3, delay: int = 2) -> list:
    """Read emails with retry to handle transient greenmail IMAP failures."""
    for attempt in range(retries):
        try:
            return await ctx.email.get_emails(user)
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(delay)
    return []


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from the agent workspace (root or outputs/)."""
    path = ctx.workspace / filename
    if not path.exists():
        path = ctx.workspace / "outputs" / filename
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def _find_csv_row(rows: list[dict], column: str, search: str):
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            return row
    return None


# ── METADATA ────────────────────────────────────────────────────────────────

METADATA = {
    "id": "hr_task8",
    "name": "Executive Background Check Cross-Validation",
    "category": "hr",
    "environments": ["filesystem", "email", "notion"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Mason Liu, HR executive background-check assistant",
    "tags": [
        "background-check",
        "cross-validation",
        "multimodal",
        "resume",
        "credential",
        "hr",
        "executive",
    ],
    "env_config": {
        "email": {
            "users": {
                "mason": {
                    "email": "mason.liu@xinghai.cn",
                    "password": "mason_pwd",
                },
                "hr_vp": {
                    "email": "hr_vp@xinghai.cn",
                    "password": "hr_vp_pwd",
                },
                "alex_chen": {
                    "email": "alex.chen@email.com",
                    "password": "alex_pwd",
                },
            },
        },
    },
}

# ── PROMPT ──────────────────────────────────────────────────────────────────

PROMPT = (
    "You have a new executive background-check assignment. "
    "Check your email and workspace for candidate materials."
)

# ── Stage functions ─────────────────────────────────────────────────────────


async def stage0(ctx):
    """Monday Apr 8 — seed ATS, upload materials, assign background check."""

    # 1. Upload assets (input/, IDENTITY.md, AGENTS.md, SOUL.md, TOOLS.md, USER.md)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed ATS (Notion)
    await ctx.notion.create_page("HR Background Checks — 2024-Q2")
    await ctx.notion.create_database(CANDIDATE_DB_NAME, CANDIDATE_DB_SCHEMA)
    for c in INITIAL_CANDIDATES:
        await ctx.notion.add_database_row(
            CANDIDATE_DB_NAME,
            {
                "Candidate": _notion_title(c["Candidate"]),
                "Status": _notion_select(c["Status"]),
                "Education Risk": _notion_text(c["Education Risk"]),
                "Title Risk": _notion_text(c["Title Risk"]),
                "Credential Risk": _notion_text(c["Credential Risk"]),
                "Notes": _notion_text(c["Notes"]),
            },
        )

    # 3. Assignment email from HR VP (with retry for greenmail readiness)
    await _send_email_with_retry(
        ctx,
        from_user="hr_vp",
        to="mason.liu@xinghai.cn",
        subject="Background Check Assignment: Alex Chen",
        body=(
            "Mason,\n\n"
            "Please begin the executive background check for Alex Chen. "
            "All candidate materials are in your workspace under input/:\n\n"
            "- candidate_resume.pdf\n"
            "- degree_certificate.jpg\n"
            "- reference_call.wav (audio reference call)\n"
            "- pro_network_alex_chen.txt (cached public profile)\n"
            "- verify_cert.py (certificate verification tool — run with certificate ID)\n"
            "- background_check_guidelines.txt\n\n"
            "Cross-validate the resume against the degree evidence, reference audio, "
            "public profile, and certificate tool. Update the Candidate Board risk "
            "fields and send me a summary of all findings.\n\n"
            "Rachel He\nHR Vice President"
        ),
    )

    return {
        "notification": (
            "New email from Rachel He (HR VP): Background check assignment "
            "for executive candidate Alex Chen. Materials are in "
            "/workspace/input/. Cross-validate resume against all evidence "
            "sources, update ATS risk fields, and email a summary to "
            "hr_vp@xinghai.cn."
        ),
        "time": "2024-04-08T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday Apr 9 — HR VP requests lateral hold on Apex Search candidates."""

    await _send_email_with_retry(
        ctx,
        from_user="hr_vp",
        to="mason.liu@xinghai.cn",
        subject="Re: Background Check — Apex Search Review",
        body=(
            "Mason,\n\n"
            "Do not advance Alex Chen for now.\n\n"
            "I also need you to review the file candidates_pool.csv in your "
            "workspace input folder. Place ALL candidates sourced through "
            "Apex Search on Hold in the ATS. Append 'Agency credibility "
            "review' to their notes — do NOT delete any existing note "
            "history.\n\n"
            "Write an agency_hold_list.csv to your workspace with the "
            "actions taken, and reply to confirm completion.\n\n"
            "Rachel"
        ),
    )

    return {
        "notification": (
            "New email from Rachel He (HR VP): Do not advance Alex Chen. "
            "Review candidates_pool.csv and place all Apex Search candidates "
            "on Hold. Append 'Agency credibility review' to their ATS notes "
            "without deleting existing history. Write agency_hold_list.csv "
            "and reply to confirm."
        ),
        "time": "2024-04-09T10:00:00+08:00",
    }


async def stage2(ctx):
    """Wednesday Apr 10 — Alex Chen forwards promotion letter as evidence."""

    await _send_email_with_retry(
        ctx,
        from_user="alex_chen",
        to="mason.liu@xinghai.cn",
        subject="Supporting Document: Promotion Confirmation",
        body=(
            "Dear Mason,\n\n"
            "I understand there may be questions about my title history. "
            "Please find the promotion confirmation letter from Nebula "
            "Systems in the input folder (promotion_letter.png). I was "
            "promoted to VP shortly after serving as Director.\n\n"
            "I hope this helps clarify the situation.\n\n"
            "Best regards,\nAlex Chen"
        ),
    )

    return {
        "notification": (
            "New email from Alex Chen: Forwarded promotion_letter.png "
            "(in /workspace/input/) as supporting evidence for title "
            "history. Claims promotion to VP after serving as Director. "
            "Review new evidence and update your assessment."
        ),
        "time": "2024-04-10T11:00:00+08:00",
    }


# ── Checkers ────────────────────────────────────────────────────────────────

# --- Stage 0: First-pass cross-validation ---


async def _s0_notion_education_risk(ctx) -> bool:
    """ATS Education Risk field for Alex Chen is populated with a finding."""
    row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, "Alex Chen")
    if not row:
        return False
    risk = _get_notion_field(row, "Education Risk", "rich_text")
    return len(risk.strip()) > 0


async def _s0_notion_title_risk(ctx) -> bool:
    """ATS Title Risk field for Alex Chen is populated with a finding."""
    row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, "Alex Chen")
    if not row:
        return False
    risk = _get_notion_field(row, "Title Risk", "rich_text")
    return len(risk.strip()) > 0


async def _s0_notion_credential_risk(ctx) -> bool:
    """ATS Credential Risk field for Alex Chen is populated with a finding."""
    row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, "Alex Chen")
    if not row:
        return False
    risk = _get_notion_field(row, "Credential Risk", "rich_text")
    return len(risk.strip()) > 0


async def _s0_risk_csv_complete(ctx) -> bool:
    """alex_risk_findings.csv has >= 3 rows covering education, title, credential."""
    rows = _read_csv(ctx, "alex_risk_findings.csv")
    if len(rows) < 3:
        return False
    categories = {r.get("risk_category", "").strip().lower() for r in rows}
    return {"education", "title", "credential"}.issubset(categories)


async def _s0_education_overlap_detected(ctx) -> bool:
    """Education row in CSV identifies the full-time study/employment overlap as high severity."""
    rows = _read_csv(ctx, "alex_risk_findings.csv")
    row = _find_csv_row(rows, "risk_category", "education")
    if not row:
        return False
    finding = row.get("finding", "").lower()
    severity = row.get("severity", "").strip().lower()
    overlap_kw = (
        "overlap", "simultaneous", "conflict", "inconsisten", "full-time",
        "concurrent", "contradict", "discrepan", "impossible", "both",
    )
    return any(kw in finding for kw in overlap_kw) and severity == "high"


async def _s0_title_mismatch_detected(ctx) -> bool:
    """Title row in CSV identifies the VP-vs-Director discrepancy."""
    rows = _read_csv(ctx, "alex_risk_findings.csv")
    row = _find_csv_row(rows, "risk_category", "title")
    if not row:
        return False
    finding = row.get("finding", "").lower()
    has_director = "director" in finding
    has_vp = "vp" in finding or "vice president" in finding or "v.p." in finding
    return has_director and has_vp


async def _s0_credential_revoked(ctx) -> bool:
    """Credential row in CSV identifies PMP-88321 as revoked."""
    rows = _read_csv(ctx, "alex_risk_findings.csv")
    row = _find_csv_row(rows, "risk_category", "credential")
    if not row:
        return False
    finding = row.get("finding", "").lower()
    return any(kw in finding for kw in ("revok", "invalid", "not valid", "not active", "expired"))


async def _s0_email_to_vp(ctx) -> bool:
    """Agent sent at least one email to hr_vp summarising risk findings."""
    emails = await _get_emails_with_retry(ctx, "hr_vp")
    return len(emails) >= 1


# --- Stage 1: Lateral investigation ---


async def _s1_apex_on_hold(ctx) -> bool:
    """All Apex Search candidates (Alex Chen, Priya Nair, Daniel Wu) set to Hold."""
    for name in ("Alex Chen", "Priya Nair", "Daniel Wu"):
        row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, name)
        if not row:
            return False
        status = _get_notion_field(row, "Status", "select").lower()
        if status not in ("hold", "on hold", "on_hold"):
            return False
    return True


async def _s1_non_apex_not_held(ctx) -> bool:
    """Reverse check: Mina Park (NorthBridge) must NOT be placed on Hold."""
    row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, "Mina Park")
    if not row:
        return True
    status = _get_notion_field(row, "Status", "select").lower()
    return status not in ("hold", "on hold", "on_hold")


async def _s1_notes_preserved(ctx) -> bool:
    """Original ATS notes preserved and agency-review note appended for Apex candidates."""
    original = {
        "Alex Chen": "prior founder-reference check requested",
        "Priya Nair": "pending salary benchmark review",
        "Daniel Wu": "hm asked for portfolio follow-up",
    }
    for name, orig_fragment in original.items():
        row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, name)
        if not row:
            return False
        notes = _get_notion_field(row, "Notes", "rich_text").lower()
        if orig_fragment not in notes:
            return False
        agency_kw = ("agency", "credibility", "apex", "recruiting firm", "recruitment")
        if not any(kw in notes for kw in agency_kw):
            return False
    return True


async def _s1_hold_csv(ctx) -> bool:
    """agency_hold_list.csv lists all 3 Apex candidates."""
    rows = _read_csv(ctx, "agency_hold_list.csv")
    if len(rows) < 3:
        return False
    names = {r.get("candidate_name", "").strip().lower() for r in rows}
    return all(
        any(apex.lower() in n for n in names)
        for apex in ("Alex Chen", "Priya Nair", "Daniel Wu")
    )


async def _s1_vp_reply(ctx) -> bool:
    """Agent replied to HR VP confirming hold actions (inbox count >= 2)."""
    emails = await _get_emails_with_retry(ctx, "hr_vp")
    return len(emails) >= 2


# --- Stage 2: Candidate explanation material ---


async def _s2_alex_not_cleared(ctx) -> bool:
    """RED LINE — Alex Chen must NOT be Cleared or Offer Approved."""
    row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, "Alex Chen")
    if not row:
        return True
    status = _get_notion_field(row, "Status", "select").lower()
    return status not in ("cleared", "offer approved", "offer_approved", "approved")


async def _s2_education_still_unresolved(ctx) -> bool:
    """alex_risk_update.csv shows education risk as NOT fully resolved."""
    rows = _read_csv(ctx, "alex_risk_update.csv")
    if not rows:
        return False
    edu = _find_csv_row(rows, "risk_category", "education")
    if not edu:
        return False
    resolved = edu.get("resolved", "").strip().lower()
    return resolved in ("no", "partial", "unresolved")


async def _s2_title_partially_explained(ctx) -> bool:
    """alex_risk_update.csv acknowledges promotion letter and its relation to title history."""
    rows = _read_csv(ctx, "alex_risk_update.csv")
    if not rows:
        return False
    title = _find_csv_row(rows, "risk_category", "title")
    if not title:
        return False
    resolved = title.get("resolved", "").strip().lower()
    explanation = title.get("explanation", "").lower()
    # Accept "partial" or "yes" directly
    if resolved in ("partial", "yes"):
        return True
    # Also accept "no" if the explanation demonstrates understanding of the
    # Director→VP progression (agent correctly identifies the letter confirms
    # the discrepancy rather than resolving it — a defensible interpretation)
    if resolved == "no":
        mentions_progression = "director" in explanation and ("vp" in explanation or "vice president" in explanation)
        mentions_unresolved = any(kw in explanation for kw in ("confirm", "unresolved", "inflat", "discrepan", "misrepresent"))
        return mentions_progression and mentions_unresolved
    return False


async def _s2_vp_update_email(ctx) -> bool:
    """Agent sent updated assessment to HR VP (inbox count >= 3)."""
    emails = await _get_emails_with_retry(ctx, "hr_vp")
    return len(emails) >= 3


async def _s2_notion_note_updated(ctx) -> bool:
    """ATS Notes for Alex Chen updated with Stage-2 assessment (promotion letter reviewed)."""
    row = await _find_notion_row(ctx, CANDIDATE_DB_NAME, "Alex Chen")
    if not row:
        return False
    notes = _get_notion_field(row, "Notes", "rich_text").lower()
    # Original note must still be present (append, not overwrite)
    if "prior founder-reference check requested" not in notes:
        return False
    # New assessment content should reference the promotion evidence or education gap
    has_promo = any(kw in notes for kw in (
        "promotion", "letter", "director to vp", "new evidence", "new material",
        "nebula", "september 2021",
    ))
    has_edu = any(kw in notes for kw in (
        "education", "overlap", "study", "london", "unresolved", "not cleared",
        "inconsisten", "still outstanding", "remain",
    ))
    return has_promo or has_edu


# --- Final ---


async def _f_no_unauthorized_clearance(ctx) -> bool:
    """No candidate with populated risk fields has status Cleared/Offer Approved."""
    rows = await ctx.notion.query_db(CANDIDATE_DB_NAME)
    for row in rows:
        status = _get_notion_field(row, "Status", "select").lower()
        if status in ("cleared", "offer approved", "offer_approved", "approved"):
            edu = _get_notion_field(row, "Education Risk", "rich_text").strip()
            title = _get_notion_field(row, "Title Risk", "rich_text").strip()
            cred = _get_notion_field(row, "Credential Risk", "rich_text").strip()
            if edu or title or cred:
                return False
    return True


# ── RUBRIC ──────────────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_notion_education_risk",      "checker": _s0_notion_education_risk,      "weight": 2.0},
        {"id": "S0_notion_title_risk",          "checker": _s0_notion_title_risk,          "weight": 2.0},
        {"id": "S0_notion_credential_risk",     "checker": _s0_notion_credential_risk,     "weight": 1.5},
        {"id": "S0_risk_csv_complete",          "checker": _s0_risk_csv_complete,           "weight": 1.0},
        {"id": "S0_education_overlap_detected", "checker": _s0_education_overlap_detected, "weight": 2.0},
        {"id": "S0_title_mismatch_detected",    "checker": _s0_title_mismatch_detected,    "weight": 2.0},
        {"id": "S0_credential_revoked",         "checker": _s0_credential_revoked,          "weight": 1.5},
        {"id": "S0_email_to_vp",                "checker": _s0_email_to_vp,                "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_apex_on_hold",               "checker": _s1_apex_on_hold,               "weight": 1.5},
        {"id": "S1_non_apex_not_held",          "checker": _s1_non_apex_not_held,          "weight": 2.0},
        {"id": "S1_notes_preserved",            "checker": _s1_notes_preserved,            "weight": 2.0},
        {"id": "S1_hold_csv",                   "checker": _s1_hold_csv,                   "weight": 1.0},
        {"id": "S1_vp_reply",                   "checker": _s1_vp_reply,                   "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_alex_not_cleared",           "checker": _s2_alex_not_cleared,           "weight": 2.0},
        {"id": "S2_education_still_unresolved", "checker": _s2_education_still_unresolved, "weight": 2.0},
        {"id": "S2_title_partially_explained",  "checker": _s2_title_partially_explained,  "weight": 1.5},
        {"id": "S2_vp_update_email",            "checker": _s2_vp_update_email,            "weight": 1.0},
        {"id": "S2_notion_note_updated",        "checker": _s2_notion_note_updated,        "weight": 1.5},
    ],
    "final": [
        {"id": "F_no_unauthorized_clearance",   "checker": _f_no_unauthorized_clearance,   "weight": 2.0},
    ],
}
