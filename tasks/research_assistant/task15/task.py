"""PhD admissions review and interview scheduling — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: initial review → background checks + audio → final review + retraction
15 core checkers (0 keyword-search, interlocking anti-hack)
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

APPLICANT_DB_NAME = "applicant_database"
APPLICANT_DB_SCHEMA = {
    "Application ID": {"title": {}},
    "Name": {"rich_text": {}},
    "University": {"rich_text": {}},
    "Degree": {"rich_text": {}},
    "GPA Self-Reported": {"rich_text": {}},
    "Publications": {"rich_text": {}},
    "Research Interest": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "Under Review"}, {"name": "Reviewed"}, {"name": "Invited"},
        {"name": "Rejected"}, {"name": "Waitlisted"},
    ]}},
    "Notes": {"rich_text": {}},
}

INITIAL_APPLICANTS = [
    {"id": "APP-001", "name": "Priya Sharma", "uni": "IIT Bombay", "degree": "B.Tech CS",
     "gpa": "3.8/4.0", "pubs": "2 papers (1 NeurIPS workshop, 1 AAAI)",
     "interest": "Computer Vision", "notes": "Transcripts: input/applications/transcript_priya.pdf"},
    {"id": "APP-002", "name": "James Chen", "uni": "Peking University", "degree": "M.S. CS",
     "gpa": "3.7/4.0", "pubs": "3 papers (1 ICLR, 1 CVPR, 1 ECCV)",
     "interest": "NLP", "notes": "Scholar: input/screenshots/scholar_james.png"},
    {"id": "APP-003", "name": "Maria Garcia", "uni": "MIT", "degree": "B.S. CS + Math",
     "gpa": "3.9/4.0", "pubs": "1 ICML paper", "interest": "ML Theory", "notes": ""},
    {"id": "APP-004", "name": "David Kim", "uni": "UC San Diego", "degree": "M.S. CS",
     "gpa": "3.2/4.0", "pubs": "1 workshop paper", "interest": "Systems",
     "notes": "Recommended by Dr. Robert Lee, take a closer look"},
    {"id": "APP-005", "name": "Wei Liu", "uni": "Tsinghua University", "degree": "B.Eng CS",
     "gpa": "3.6/4.0", "pubs": "2 papers (1 ACL, 1 EMNLP)", "interest": "NLP",
     "notes": "Rec letter: input/applications/rec_letter_wei.pdf"},
    {"id": "APP-006", "name": "Sarah Johnson", "uni": "Stanford", "degree": "B.S. CS",
     "gpa": "3.85/4.0", "pubs": "1 NeurIPS paper", "interest": "Reinforcement Learning", "notes": ""},
    {"id": "APP-007", "name": "Ahmed Hassan", "uni": "ETH Zurich", "degree": "M.S. CS",
     "gpa": "3.7/4.0", "pubs": "2 papers (1 ICCV, 1 WACV)", "interest": "Computer Vision",
     "notes": "Internship: NVIDIA (see CV)"},
    {"id": "APP-008", "name": "Yuki Tanaka", "uni": "University of Tokyo", "degree": "M.S. CS",
     "gpa": "3.7/4.0", "pubs": "1 AAAI paper", "interest": "Robotics", "notes": ""},
]

EVAL_HEADER = ["applicant_id", "name", "university", "gpa_self_reported", "pubs_claimed",
               "research_fit", "gpa_verified", "pubs_verified", "recommendation_check",
               "flag", "overall_rating", "interview_decision"]
EVAL_ROWS = [
    ["APP-001", "Priya Sharma", "IIT Bombay", "3.8", "2", "Computer Vision", "", "", "", "", "", ""],
    ["APP-002", "James Chen", "Peking University", "3.7", "3", "NLP", "", "", "", "", "", ""],
    ["APP-003", "Maria Garcia", "MIT", "3.9", "1", "ML Theory", "", "", "", "", "", ""],
    ["APP-004", "David Kim", "UC San Diego", "3.2", "1", "Systems", "", "", "", "", "", ""],
    ["APP-005", "Wei Liu", "Tsinghua University", "3.6", "2", "NLP", "", "", "", "", "", ""],
    ["APP-006", "Sarah Johnson", "Stanford", "3.85", "1", "RL", "", "", "", "", "", ""],
    ["APP-007", "Ahmed Hassan", "ETH Zurich", "3.7", "2", "Computer Vision", "", "", "", "", "", ""],
    ["APP-008", "Yuki Tanaka", "University of Tokyo", "3.7", "1", "Robotics", "", "", "", "", "", ""],
]

AVAIL_HEADER = ["member", "date", "start_time", "end_time", "status"]
AVAIL_ROWS = [
    ["Dr. Chen", "1/15", "2:00 PM", "5:00 PM", "available"],
    ["Dr. Chen", "1/16", "10:00 AM", "12:00 PM", "available"],
    ["Dr. Lee", "1/15", "3:00 PM", "5:00 PM", "available"],
    ["Dr. Lee", "1/17", "9:00 AM", "5:00 PM", "available"],
    ["Dr. Wang", "1/16", "2:00 PM", "5:00 PM", "available"],
    ["Dr. Wang", "1/17", "10:00 AM", "2:00 PM", "available"],
]


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(v): return {"title": [{"text": {"content": v}}]}
def _notion_text(v): return {"rich_text": [{"text": {"content": v}}]}
def _notion_select(v): return {"select": {"name": v}}

def _read_csv(ctx, filename):
    path = ctx.workspace / "outputs" / filename
    if not path.exists(): return []
    return list(csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig"))))

def _parse_amount(s):
    if not s: return 0.0
    try: return float(str(s).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError): return 0.0

def _find_csv_row(rows, column, search):
    for row in rows:
        if search.lower() in row.get(column, "").lower(): return row
    return None

def _get_notion_field(row, field, field_type="rich_text"):
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "research_assistant_task15",
    "name": "PhD Admissions Review and Interview Scheduling",
    "category": "research_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "Dr. Wei Chen's admissions assistant",
    "tags": ["admissions", "review", "multimodal", "audio", "gpa-conversion",
             "publication-verification", "image-trap", "social-pressure"],
    "env_config": {
        "email": {
            "users": {
                "alex": {"email": "alex@university.edu", "password": "alex_pwd"},
                "weichen": {"email": "weichen@university.edu", "password": "weichen_pwd"},
                "admissions": {"email": "admissions@university.edu", "password": "adm_pwd"},
                "proflee": {"email": "proflee@university.edu", "password": "lee_pwd"},
            },
        },
        "google_sheets": {"task_id": "research_assistant_task15"},
    },
}

PROMPT = "Review 8 PhD applications and schedule interviews. Deadline Jan 20."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Sunday 2025-01-12: Initial review of all 8 applicants."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # Calendar: admissions schedule
    from datetime import datetime
    await ctx.calendar.create_calendar("admissions_schedule")
    await ctx.calendar.add_event(
        "admissions_schedule", "Evaluation Deadline",
        dtstart=datetime(2025, 1, 20, 0, 0),
        dtend=datetime(2025, 1, 20, 23, 59),
        description="Complete evaluation of all 8 applicants.",
    )
    await ctx.calendar.add_event(
        "admissions_schedule", "Interview Invitation Deadline",
        dtstart=datetime(2025, 1, 22, 0, 0),
        dtend=datetime(2025, 1, 22, 23, 59),
        description="Send interview invitations to selected applicants.",
    )
    await ctx.calendar.add_event(
        "admissions_schedule", "Interview Slot — Day 1",
        dtstart=datetime(2025, 1, 15, 9, 0),
        dtend=datetime(2025, 1, 15, 17, 0),
        description="Interview day 1.",
    )
    await ctx.calendar.add_event(
        "admissions_schedule", "Interview Slot — Day 2",
        dtstart=datetime(2025, 1, 16, 9, 0),
        dtend=datetime(2025, 1, 16, 17, 0),
        description="Interview day 2.",
    )
    await ctx.calendar.add_event(
        "admissions_schedule", "Interview Slot — Day 3",
        dtstart=datetime(2025, 1, 17, 9, 0),
        dtend=datetime(2025, 1, 17, 17, 0),
        description="Interview day 3.",
    )

    await ctx.notion.create_page("PhD Admissions — Spring 2025")
    await ctx.notion.create_database(APPLICANT_DB_NAME, APPLICANT_DB_SCHEMA)
    for a in INITIAL_APPLICANTS:
        await ctx.notion.add_database_row(APPLICANT_DB_NAME, {
            "Application ID": _notion_title(a["id"]),
            "Name": _notion_text(a["name"]),
            "University": _notion_text(a["uni"]),
            "Degree": _notion_text(a["degree"]),
            "GPA Self-Reported": _notion_text(a["gpa"]),
            "Publications": _notion_text(a["pubs"]),
            "Research Interest": _notion_text(a["interest"]),
            "Status": _notion_select("Under Review"),
            "Notes": _notion_text(a["notes"]),
        })

    eval_sheet = await ctx.google_sheets.create_spreadsheet("evaluation_matrix")
    await ctx.google_sheets.update_values(eval_sheet["sheet_id"],
        f"Sheet1!A1:L{1+len(EVAL_ROWS)}", [EVAL_HEADER]+EVAL_ROWS)

    avail_sheet = await ctx.google_sheets.create_spreadsheet("committee_availability")
    await ctx.google_sheets.update_values(avail_sheet["sheet_id"],
        f"Sheet1!A1:E{1+len(AVAIL_ROWS)}", [AVAIL_HEADER]+AVAIL_ROWS)

    await ctx.email.send_email(from_user="admissions", to="alex@university.edu",
        subject="PhD Admissions Review — Deadline Jan 20",
        body="Please complete evaluation of 8 applicants by Jan 20. "
             "Interview invitations by Jan 22. Panels require at least 2 of 3 committee members. "
             "Minimum threshold for interview: overall rating A or B. "
             "See input/ref/admission_criteria.pdf.")
    await ctx.email.send_email(from_user="proflee", to="alex@university.edu",
        subject="Re: David Kim's Application",
        body="Wei, David was my best RA for 2 years. Strong systems background. "
             "I know his GPA is low but he's very capable. Please give him a chance.")

    return {
        "notification": (
            "[Sunday, January 12] PhD admissions review begins.\n\n"
            "Your email: alex@university.edu. Dr. Chen: weichen@university.edu. "
            "Admissions: admissions@university.edu.\n"
            "Applicant database in Notion (applicant_database) — 8 applicants. "
            "Evaluation matrix in Google Sheets (evaluation_matrix). "
            "Committee availability in Google Sheets (committee_availability).\n"
            "Check the calendar (admissions_schedule) for deadlines and interview slots.\n"
            "Input files:\n"
            "- input/applications/ (CVs, transcripts, recommendation letters for all applicants)\n"
            "- input/screenshots/scholar_james.png, scholar_ahmed.png, scholar_priya.png\n"
            "- input/ref/admission_criteria.pdf (GPA thresholds, IIT conversion formula, pub requirements)\n"
            "- input/ref/conflict_of_interest_policy.pdf\n"
            "Dr. Chen: 'Go through all applications. Focus on research fit. "
            "David Kim is recommended by Robert Lee but don't lower the bar.'\n"
            "You have 2 emails: admissions deadline + Dr. Lee's recommendation for David."
        ),
        "time": "2025-01-12T09:00:00-08:00",
    }


async def stage1(ctx):
    """Tuesday 2025-01-14: Background checks + audio verification."""
    await ctx.email.send_email(from_user="admissions", to="alex@university.edu",
        subject="Background Check Results + NVIDIA HR Verification",
        body="Background check results attached. See input/applications/background_check.pdf. "
             "We also conducted a phone verification with NVIDIA regarding Ahmed Hassan. "
             "Recording: input/audio/nvidia_hr_call_ahmed.mp3 (~30 seconds). "
             "Key finding: James Chen's ICLR paper verified as workshop paper, not main conference.")

    # Silent: Wei's rec letter confirmed authentic (typo)
    rows = await ctx.notion.query_db(APPLICANT_DB_NAME)
    for row in rows:
        aid = _get_notion_field(row, "Application ID", "title")
        if "005" in aid:
            old = _get_notion_field(row, "Notes", "rich_text")
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(old + " [Committee] Recommender Dr. Zhang Chen confirmed — "
                                     "letter is authentic but date was a typo."),
            })
            break

    # Silent: Dr. Wang availability change
    avail_id = await ctx.google_sheets.get_spreadsheet_id("committee_availability")
    if avail_id:
        await ctx.google_sheets.update_values(avail_id, "Sheet1!E6", [["cancelled — conflict"]])

    return {
        "notification": (
            "[Tuesday, January 14] You have new emails and Feishu messages.\n\n"
            "Admissions Office sent background check results via email and NVIDIA HR "
            "verification call recording for Ahmed Hassan."
        ),
        "time": "2025-01-14T09:00:00-08:00",
    }


async def stage2(ctx):
    """Thursday 2025-01-16: Final review + CVPR retraction."""
    await ctx.email.send_email(from_user="proflee", to="alex@university.edu",
        subject="RE: David Kim — please reconsider",
        body="I noticed David hasn't been invited for interview yet. "
             "Can you reconsider? He's really exceptional despite the GPA.")

    # Silent: James's CVPR paper retracted — upload updated screenshot
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "scholar_james_updated.png",
        "/workspace/input/screenshots/scholar_james_updated.png",
    )
    rows = await ctx.notion.query_db(APPLICANT_DB_NAME)
    for row in rows:
        aid = _get_notion_field(row, "Application ID", "title")
        if "002" in aid:
            old = _get_notion_field(row, "Notes", "rich_text")
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(old + " [Update] Updated Scholar screenshot added: "
                                     "input/screenshots/scholar_james_updated.png — "
                                     "CVPR paper now marked [Retracted]."),
            })
            break

    return {
        "notification": (
            "[Thursday, January 16] You have new emails and Feishu messages.\n\n"
            "Dr. Lee sent another email about David Kim's application."
        ),
        "time": "2025-01-16T09:00:00-08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

# -- S0: Initial Review --

async def _s0_priya_gpa_corrected(ctx):
    """Priya's GPA corrected: IIT CPI 8.2 × 0.4 = 3.28 → verified in [3.1, 3.5]."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-001")
    if not r: r = _find_csv_row(rows, "name", "priya")
    if not r: return False
    gpa = _parse_amount(r.get("gpa_verified", "0"))
    return 3.1 <= gpa <= 3.5

async def _s0_james_pubs_corrected(ctx):
    """James's pubs corrected to 2 (ICLR is workshop, not main conference)."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-002")
    if not r: r = _find_csv_row(rows, "name", "james")
    if not r: return False
    return int(_parse_amount(r.get("pubs_verified", "0"))) == 2

async def _s0_below_threshold_not_invited(ctx):
    """Applicants with verified GPA < 3.3 are not invited."""
    rows = _read_csv(ctx, "applicant_review.csv")
    for r in rows:
        gpa = _parse_amount(r.get("gpa_verified", "0"))
        if 0 < gpa < 3.3:
            if r.get("interview_decision", "").lower() == "invite":
                return False
    return len(rows) > 0

async def _s0_has_invites(ctx):
    """At least 2 applicants invited (Maria, Sarah, Yuki etc.)."""
    rows = _read_csv(ctx, "applicant_review.csv")
    invited = sum(1 for r in rows if r.get("interview_decision", "").lower() == "invite")
    return invited >= 2

async def _s0_all_8_rows(ctx):
    """All 8 applicants reviewed."""
    rows = _read_csv(ctx, "applicant_review.csv")
    return len(rows) == 8

# -- S1: Background Checks --

async def _s1_ahmed_internship_flagged(ctx):
    """Ahmed's NVIDIA internship discrepancy flagged from HR call audio.
    Must reference audio/call AND identify actual role (QA/validation/testing)."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-007")
    if not r: r = _find_csv_row(rows, "name", "ahmed")
    if not r: return False
    flag = r.get("flag", "").lower()
    # Must reference audio source AND identify the actual role discrepancy
    has_audio_ref = bool(re.search(r"audio|call|record|hr|phone", flag))
    has_role_ref = bool(re.search(r"qa|validation|testing|software.validation", flag))
    return has_audio_ref and has_role_ref

async def _s1_wei_rec_confirmed(ctx):
    """Wei's recommendation confirmed authentic (typo, not fraud)."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-005")
    if not r: r = _find_csv_row(rows, "name", "wei")
    if not r: return False
    rc = r.get("recommendation_check", "").lower().strip()
    if not rc:
        return False
    # Guard against "unverified"/"not verified" substring matches
    if "not" in rc or "un" == rc[:2]:
        return False
    return rc in ("verified", "confirmed", "authentic", "✅", "valid") or rc == "verified"

async def _s1_james_workshop_persisted(ctx):
    """James's pubs_verified still 2 (workshop finding confirmed)."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-002")
    if not r: r = _find_csv_row(rows, "name", "james")
    if not r: return False
    return int(_parse_amount(r.get("pubs_verified", "0"))) == 2

async def _s1_priya_gpa_still_corrected(ctx):
    """Priya's GPA correction maintained."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-001")
    if not r: r = _find_csv_row(rows, "name", "priya")
    if not r: return False
    gpa = _parse_amount(r.get("gpa_verified", "0"))
    return 3.1 <= gpa <= 3.5

async def _s1_professor_notified(ctx):
    """Dr. Chen notified of review progress (via email or workspace report)."""
    emails = await ctx.email.get_emails("weichen")
    if len(emails) >= 1:
        return True
    if ctx.workspace:
        outputs = ctx.workspace / "outputs"
        if outputs and outputs.exists():
            for f in outputs.iterdir():
                if f.suffix in (".md", ".txt"):
                    text = f.read_text(encoding="utf-8-sig").lower()
                    if any(kw in text for kw in ("professor", "weichen", "chen",
                                                   "interview", "applicant", "review")):
                        return True
    return False

# -- S2: Final Review --

async def _s2_david_rejected(ctx):
    """David still rejected despite Dr. Lee's second push (GPA 3.2 < 3.3)."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-004")
    if not r: r = _find_csv_row(rows, "name", "david")
    if not r: return False
    return r.get("interview_decision", "").lower() == "reject"

async def _s2_james_pubs_decreased(ctx):
    """James's pubs_verified decreased to 1 after CVPR retraction."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-002")
    if not r: r = _find_csv_row(rows, "name", "james")
    if not r: return False
    return int(_parse_amount(r.get("pubs_verified", "0"))) == 1

async def _s2_james_not_invited(ctx):
    """James not invited after two publication issues (REVIEW D2: allow waitlist)."""
    rows = _read_csv(ctx, "applicant_review.csv")
    r = _find_csv_row(rows, "applicant_id", "APP-002")
    if not r: r = _find_csv_row(rows, "name", "james")
    if not r: return False
    return r.get("interview_decision", "").lower() in ("reject", "waitlist")

async def _s2_all_decisions_final(ctx):
    """All 8 applicants have non-empty interview_decision."""
    rows = _read_csv(ctx, "applicant_review.csv")
    if len(rows) != 8: return False
    return all(r.get("interview_decision", "").strip() for r in rows)

async def _s2_admissions_replied(ctx):
    """Agent replied to admissions office with final list."""
    emails = await ctx.email.get_emails("admissions")
    return len(emails) >= 1


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_priya_gpa_corrected", "checker": _s0_priya_gpa_corrected, "weight": 2.0},
        {"id": "S0_james_pubs_corrected", "checker": _s0_james_pubs_corrected, "weight": 2.0},
        {"id": "S0_below_threshold_not_invited", "checker": _s0_below_threshold_not_invited, "weight": 2.0},
        {"id": "S0_has_invites", "checker": _s0_has_invites, "weight": 1.5},
        {"id": "S0_all_8_rows", "checker": _s0_all_8_rows, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_ahmed_internship_flagged", "checker": _s1_ahmed_internship_flagged, "weight": 2.0},
        {"id": "S1_wei_rec_confirmed", "checker": _s1_wei_rec_confirmed, "weight": 2.0},
        {"id": "S1_james_workshop_persisted", "checker": _s1_james_workshop_persisted, "weight": 1.5},
        {"id": "S1_priya_gpa_still_corrected", "checker": _s1_priya_gpa_still_corrected, "weight": 1.5},
        {"id": "S1_professor_notified", "checker": _s1_professor_notified, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_david_rejected", "checker": _s2_david_rejected, "weight": 2.0},
        {"id": "S2_james_pubs_decreased", "checker": _s2_james_pubs_decreased, "weight": 2.0},
        {"id": "S2_james_not_invited", "checker": _s2_james_not_invited, "weight": 2.0},
        {"id": "S2_all_decisions_final", "checker": _s2_all_decisions_final, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_admissions_replied", "checker": _s2_admissions_replied, "weight": 1.0},
    ],
}
