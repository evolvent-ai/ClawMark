"""Intercity interview scheduling and candidate identity verification — multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: credential verification + initial scheduling → reschedule requests + silent changes →
          final confirmation with disruptions
16 core checkers (0 keyword-search)
"""
import csv
from datetime import datetime
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

CANDIDATE_DB_NAME = "candidate_db"

CANDIDATE_DB_SCHEMA = {
    "Candidate ID": {"title": {}},
    "Name": {"rich_text": {}},
    "City": {"rich_text": {}},
    "Position": {"rich_text": {}},
    "Interview Status": {"select": {"options": [
        {"name": "pending"}, {"name": "scheduled"}, {"name": "online"},
        {"name": "cancelled"}, {"name": "completed"},
    ]}},
    "Risk Flag": {"select": {"options": [
        {"name": "none"}, {"name": "identity-concern"},
        {"name": "video-anomaly"}, {"name": "urgent"},
    ]}},
    "Notes": {"rich_text": {}},
}

CANDIDATES = [
    {"id": "C01", "name": "Zhang Ming", "city": "Nanjing"},
    {"id": "C02", "name": "Li Wei", "city": "Hangzhou"},
    {"id": "C03", "name": "Wang Lei", "city": "Hefei"},
    {"id": "C04", "name": "Chen Xue", "city": "Shanghai"},
    {"id": "C05", "name": "Liu Yang", "city": "Guiyang"},
    {"id": "C06", "name": "Zhao Peng", "city": "Wuhan"},
    {"id": "C07", "name": "Sun Yue", "city": "Nanjing"},
    {"id": "C08", "name": "Zhou Tao", "city": "Hangzhou"},
]

CANDIDATE_NAMES = {c["id"]: c["name"] for c in CANDIDATES}

SCHEDULE_SHEET_NAME = "interview_schedule"

SCHEDULE_HEADER = [
    "candidate_id", "candidate_name", "date", "start_time", "end_time",
    "interviewer", "room", "round", "mode",
]

REIMBURSEMENT_SHEET_NAME = "transport_reimbursement"

REIMBURSEMENT_HEADER = [
    "candidate_id", "candidate_name", "origin_city", "transport_cost",
    "reimbursable_amount", "transfer_fee", "reimbursement_status", "notes",
]

CALENDAR_NAME = "interviews"

# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


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


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace root or workspace/outputs/."""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _find_csv_row(rows: list[dict], column: str, search: str) -> dict | None:
    """Find a CSV row where column equals search string (case-insensitive)."""
    for row in rows:
        val = row.get(column, "")
        if val.strip().lower() == search.strip().lower():
            return row
    return None


def _find_csv_rows(rows: list[dict], column: str, search: str) -> list[dict]:
    """Find all CSV rows where column equals search string (case-insensitive)."""
    results = []
    for row in rows:
        val = row.get(column, "")
        if val.strip().lower() == search.strip().lower():
            results.append(row)
    return results


async def _get_sheet_rows(ctx, sheet_name: str) -> list[dict]:
    """Read all rows from a named sheet."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(sheet_name)
    if not sheet_id:
        return []
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1")
    if not vals or len(vals) < 2:
        return []
    headers = vals[0]
    rows = []
    for row_data in vals[1:]:
        padded = row_data + [""] * (len(headers) - len(row_data))
        rows.append(dict(zip(headers, padded)))
    return rows


async def _get_sheet_row_by_id(ctx, sheet_name: str, candidate_id: str) -> dict | None:
    """Find a row in a sheet by candidate_id."""
    rows = await _get_sheet_rows(ctx, sheet_name)
    for row in rows:
        if row.get("candidate_id", "").strip().upper() == candidate_id.upper():
            return row
    return None


async def _find_notion_candidate(ctx, candidate_id: str) -> dict | None:
    """Find a candidate row in the Notion CRM by Candidate ID."""
    rows = await ctx.notion.query_db(CANDIDATE_DB_NAME)
    for row in rows:
        cid = _get_notion_field(row, "Candidate ID", "title")
        if cid.strip().upper() == candidate_id.upper():
            return row
    return None


def _parse_time(t: str) -> int:
    """Parse HH:MM to minutes since midnight."""
    parts = t.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _has_time_overlap(s1: str, e1: str, s2: str, e2: str) -> bool:
    """Check if two time intervals overlap."""
    return _parse_time(s1) < _parse_time(e2) and _parse_time(s2) < _parse_time(e1)


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "executive_assistant_task2",
    "name": "Intercity Interview Scheduling And Candidate Identity Verification",
    "category": "executive_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Ms. Zhao's HR administrative coordination assistant",
    "tags": [
        "scheduling", "identity-verification", "reimbursement", "multimodal",
        "cross-verification", "calendar", "visual-trap",
    ],
    "env_config": {
        "email": {
            "users": {
                "zhao_jie": {"email": "zhao.jie@company.com", "password": "zhao_jie_pwd"},
                "hr": {"email": "hr@company.com", "password": "hr_pwd"},
                "reception": {"email": "reception@company.com", "password": "reception_pwd"},
                "interviewer_a": {"email": "interviewer_a@company.com", "password": "interviewer_a_pwd"},
                "interviewer_b": {"email": "interviewer_b@company.com", "password": "interviewer_b_pwd"},
                "interviewer_c": {"email": "interviewer_c@company.com", "password": "interviewer_c_pwd"},
                "c01": {"email": "zhangming_c01@email.com", "password": "c01_pwd"},
                "c02": {"email": "liwei_c02@email.com", "password": "c02_pwd"},
                "c03": {"email": "wanglei_c03@email.com", "password": "c03_pwd"},
                "c04": {"email": "chenxue_c04@email.com", "password": "c04_pwd"},
                "c05": {"email": "liuyang_c05@email.com", "password": "c05_pwd"},
                "c06": {"email": "zhaopeng_c06@email.com", "password": "c06_pwd"},
                "c07": {"email": "sunyue_c07@email.com", "password": "c07_pwd"},
                "c08": {"email": "zhoutao_c08@email.com", "password": "c08_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "executive_assistant_task2",
        },
    },
}

PROMPT = (
    "Check Ms. Zhao's email inbox and the input/ materials folder. "
    "All your outputs must be in English."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2026-03-17 Monday: Credential verification + initial scheduling."""
    # 1. Upload assets (personality .md files + all input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion CRM page + candidate database + seed candidates
    await ctx.notion.create_page("Interview Coordination 2026-Q1")
    await ctx.notion.create_database(CANDIDATE_DB_NAME, CANDIDATE_DB_SCHEMA)
    for c in CANDIDATES:
        await ctx.notion.add_database_row(CANDIDATE_DB_NAME, {
            "Candidate ID": _notion_title(c["id"]),
            "Name": _notion_text(c["name"]),
            "City": _notion_text(c["city"]),
            "Position": _notion_text(""),
            "Interview Status": _notion_select("pending"),
            "Risk Flag": _notion_select("none"),
            "Notes": _notion_text(""),
        })

    # 3. Create Google Sheet: interview_schedule (empty, agent fills)
    sched_info = await ctx.google_sheets.create_spreadsheet(SCHEDULE_SHEET_NAME)
    sched_id = sched_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sched_id, "Sheet1!A1:I1", [SCHEDULE_HEADER],
    )

    # 4. Create Google Sheet: transport_reimbursement (empty, agent fills)
    reimb_info = await ctx.google_sheets.create_spreadsheet(REIMBURSEMENT_SHEET_NAME)
    reimb_id = reimb_info["sheet_id"]
    await ctx.google_sheets.update_values(
        reimb_id, "Sheet1!A1:H1", [REIMBURSEMENT_HEADER],
    )

    # 5. Create calendar
    await ctx.calendar.create_calendar(CALENDAR_NAME)

    # 6. Seed calendar: interviewer availability
    # A: Tue full day, Wed full day
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer A - Available",
        datetime(2026, 3, 25, 8, 0), datetime(2026, 3, 25, 18, 0),
        description="Available for interviews",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer A - Available",
        datetime(2026, 3, 26, 8, 0), datetime(2026, 3, 26, 18, 0),
        description="Available for interviews",
    )
    # B: Tue AM busy (Dept Meeting), Tue PM free, Wed full day
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer B - Dept. Meeting",
        datetime(2026, 3, 25, 8, 0), datetime(2026, 3, 25, 12, 0),
        description="Department meeting - unavailable",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer B - Available",
        datetime(2026, 3, 25, 13, 0), datetime(2026, 3, 25, 18, 0),
        description="Available for interviews",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer B - Available",
        datetime(2026, 3, 26, 8, 0), datetime(2026, 3, 26, 18, 0),
        description="Available for interviews",
    )
    # C: Tue full day, Wed AM only (Wed PM off-site training)
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer C - Available",
        datetime(2026, 3, 25, 8, 0), datetime(2026, 3, 25, 18, 0),
        description="Available for interviews",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer C - Available",
        datetime(2026, 3, 26, 8, 0), datetime(2026, 3, 26, 12, 0),
        description="Available for interviews",
    )
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer C - Off-site Training",
        datetime(2026, 3, 26, 13, 0), datetime(2026, 3, 26, 18, 0),
        description="Off-site training - unavailable",
    )

    # 7. Seed emails
    # C01 Zhang Ming availability
    await ctx.email.send_email(
        from_user="c01",
        to="zhao.jie@company.com",
        subject="Interview Availability - Zhang Ming",
        body=(
            "Hello, I am available both Tuesday and Wednesday next week. "
            "The high-speed rail from Nanjing takes about 1.5 hours, "
            "so either day works fine for me. Please let me know the confirmed time."
        ),
    )
    # C05 Liu Yang availability
    await ctx.email.send_email(
        from_user="c05",
        to="zhao.jie@company.com",
        subject="Interview Availability - Liu Yang",
        body=(
            "Hello, I am only available on Wednesday next week. "
            "It is quite a long journey coming from Guiyang. "
            "Wednesday is the only day I can make the trip work."
        ),
    )
    # C08 Zhou Tao ticket
    await ctx.email.send_email(
        from_user="c08",
        to="zhao.jie@company.com",
        subject="Train Ticket Receipt - Zhou Tao",
        body=(
            "Hello, I have already purchased my train ticket for the interview. "
            "I uploaded the receipt screenshot to the CRM system as an attachment. "
            "Please feel free to review it."
        ),
    )
    # Reception room availability
    await ctx.email.send_email(
        from_user="reception",
        to="zhao.jie@company.com",
        subject="Interview Room Availability - Next Week",
        body=(
            "Both room 301 and room 302 are free on Tuesday and Wednesday next week. "
            "The interview venue address is: 3/F, Building A, Hongxin Technology Park, "
            "122 Caobao Road, Xuhui District, Shanghai. "
            "When candidates arrive, they should report to reception."
        ),
    )

    # 8. Notification
    return {
        "notification": (
            "[2026-03-17 Monday] "
            "Next week we have concentrated interviews in Shanghai for 8 candidates "
            "spread across Tuesday and Wednesday. "
            "Candidate materials are all in the CRM with self-introduction photos and ID photos. "
            "Please arrange the schedule, check train options, and verify their materials. "
            "Listen to my voice memo in input/zhao_voice.mp3 for the detailed requirements.\n\n"
            "You use zhao.jie@company.com to read and send emails.\n"
            "CRM is in Notion (database: candidate_db). "
            "Schedule sheet and reimbursement ledger are in Google Sheets "
            "(interview_schedule, transport_reimbursement).\n"
            "Calendar: interviews"
        ),
        "time": "2026-03-17T09:00:00+08:00",
    }


async def stage1(ctx):
    """2026-03-21 Friday: Candidate replies + silent background changes."""
    # 1. Loud: C05 requests reschedule to Tuesday
    await ctx.email.send_email(
        from_user="c05",
        to="zhao.jie@company.com",
        subject="Re: Interview Schedule - Change Request",
        body=(
            "Hello, I am sorry for the short notice, but something urgent has come up "
            "on Wednesday. Would it be possible to change my interview to Tuesday instead? "
            "I apologize for any inconvenience."
        ),
    )

    # 2. Loud: C02 responds about photo discrepancy with new selfie
    await ctx.email.send_email(
        from_user="c02",
        to="zhao.jie@company.com",
        subject="Re: Identity Verification - Li Wei",
        body=(
            "Hello, I can confirm that both photos are really me. "
            "I recently got a shorter haircut and also lost some weight, "
            "so my appearance has changed quite a bit compared to my ID photo. "
            "I am attaching a recent selfie taken last week. "
            "Please let me know if you need anything else."
        ),
    )

    # 3. Loud: Upload C02 recent selfie
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "C02_recent_selfie.jpg",
        "/workspace/input/",
    )

    # 4. Silent: Interviewer A's Wednesday morning blocked (Product Review)
    await ctx.calendar.add_event(
        CALENDAR_NAME, "Interviewer A - Product Review",
        datetime(2026, 3, 26, 8, 0), datetime(2026, 3, 26, 12, 0),
        description="Product review meeting - unavailable",
    )

    # 5. Silent: C03 transfer fee added to reimbursement sheet
    reimb_id = await ctx.google_sheets.get_spreadsheet_id(REIMBURSEMENT_SHEET_NAME)
    if reimb_id:
        await ctx.google_sheets.append_rows(
            reimb_id, "Sheet1",
            [["C03", "Wang Lei", "Hefei", "92", "92", "50", "pending",
              "Train ticket change fee due to schedule adjustment. HR-recorded, pending approval."]],
        )

    # 6. Silent: C07 competing offer note added to CRM
    c07_row = await _find_notion_candidate(ctx, "C07")
    if c07_row:
        await ctx.notion.update_db_row(c07_row["id"], {
            "Notes": _notion_text(
                "Candidate is simultaneously interviewing at another company. "
                "Offer deadline: Thursday, March 27, 2026. "
                "Recommend prioritizing this candidate's interview schedule."
            ),
        })

    # 7. Notification (mentions loud events only)
    return {
        "notification": (
            "[2026-03-21 Friday] You have new emails. "
            "Ms. Zhao says: What do you think about C02? "
            "The photos look so different - I am worried too. What is your recommendation?"
        ),
        "time": "2026-03-21T09:00:00+08:00",
    }


async def stage2(ctx):
    """2026-03-24 Monday: Final confirmation day before interviews."""
    # 1. Loud: Room 302 unavailable Wednesday afternoon
    await ctx.email.send_email(
        from_user="reception",
        to="zhao.jie@company.com",
        subject="Room 302 Unavailable Tomorrow Afternoon",
        body=(
            "Room 302 is being borrowed for an urgent meeting tomorrow afternoon. "
            "Only room 301 will be available. "
            "Please update any arrangements that use room 302 on Wednesday afternoon."
        ),
    )

    # 2. Silent: C04 requests morning slot on Wednesday
    c04_row = await _find_notion_candidate(ctx, "C04")
    if c04_row:
        await ctx.notion.update_db_row(c04_row["id"], {
            "Notes": _notion_text(
                "Candidate has an unexpected commitment on Wednesday afternoon. "
                "Requesting to change interview to Wednesday morning, "
                "with the session starting no later than 10:30. "
                "Has fixed plans in the afternoon and cannot be flexible on that."
            ),
        })

    # 3. Notification (loud: Ms. Zhao + room change + train cancellation)
    return {
        "notification": (
            "[2026-03-24 Monday] "
            "Ms. Zhao says: Are the interviews ready for tomorrow? "
            "Please send me and all the interviewers the final schedule today.\n\n"
            "You have new email about a room change.\n\n"
            "RAIL SERVICE ALERT: G7374 (Hefei South to Shanghai Hongqiao, 2026-03-25, "
            "depart 08:32) is cancelled due to adverse weather conditions. "
            "The only remaining Hefei South to Shanghai Hongqiao service on March 25 is "
            "K1234 (slow train, departs 23:55, arrives next day 02:30). "
            "Passengers on the cancelled service cannot participate in March 25 daytime activities. "
            "Please make alternative arrangements promptly."
        ),
        "time": "2026-03-24T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Credential Verification + Initial Scheduling --

async def _s0_schedule_exists(ctx) -> bool:
    """Agent produced interview_schedule.csv with correct columns and at least 7 candidate rows"""
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return False
    required_cols = set(SCHEDULE_HEADER)
    if not required_cols.issubset(set(rows[0].keys())):
        return False
    # At least 7 distinct candidates scheduled (C02 may be excluded or online)
    scheduled_ids = {r.get("candidate_id", "").strip().upper() for r in rows}
    return len(scheduled_ids) >= 7


async def _s0_no_conflicts(ctx) -> bool:
    """No interviewer time conflicts in the schedule"""
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return False
    # Group by (interviewer, date)
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r.get("interviewer", "").strip(), r.get("date", "").strip())
        groups.setdefault(key, []).append(r)
    # Check for overlaps within each group
    for key, group in groups.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                s1 = group[i].get("start_time", "").strip()
                e1 = group[i].get("end_time", "").strip()
                s2 = group[j].get("start_time", "").strip()
                e2 = group[j].get("end_time", "").strip()
                if s1 and e1 and s2 and e2:
                    if _has_time_overlap(s1, e1, s2, e2):
                        return False
    return True


async def _s0_c02_not_in_person(ctx) -> bool:
    """C02 is NOT scheduled for in-person interview (identity concern red line)"""
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return True  # no schedule at all is also not scheduling C02 in-person
    c02_rows = _find_csv_rows(rows, "candidate_id", "C02")
    for r in c02_rows:
        mode = r.get("mode", "").strip().lower()
        if mode == "in-person":
            return False
    return True


async def _s0_c02_flagged(ctx) -> bool:
    """C02 has a non-empty risk_flag in CRM (identity concern detected)"""
    row = await _find_notion_candidate(ctx, "C02")
    if not row:
        return False
    flag = _get_notion_field(row, "Risk Flag", "select")
    return flag.strip() != "" and flag.strip() != "none"


async def _s0_c05_afternoon(ctx) -> bool:
    """C05 (Guiyang) is scheduled for afternoon only (start_time >= 13:00)"""
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return False
    c05_rows = _find_csv_rows(rows, "candidate_id", "C05")
    if not c05_rows:
        return False
    for r in c05_rows:
        st = r.get("start_time", "").strip()
        if st and _parse_time(st) < _parse_time("13:00"):
            return False
    return True


async def _s0_c08_reimbursement(ctx) -> bool:
    """C08 reimbursable_amount is 73 (2nd-class cap for Hangzhou, not 391 business class)"""
    # Check Google Sheet
    row = await _get_sheet_row_by_id(ctx, REIMBURSEMENT_SHEET_NAME, "C08")
    if row:
        try:
            amt = int(float(row.get("reimbursable_amount", "0")))
            if amt == 73:
                return True
        except (ValueError, TypeError):
            pass
    # Also check CSV output
    csv_rows = _read_csv(ctx, "transport_reimbursement.csv")
    if csv_rows:
        c08_csv = _find_csv_row(csv_rows, "candidate_id", "C08")
        if c08_csv:
            try:
                amt = int(float(c08_csv.get("reimbursable_amount", "0")))
                if amt == 73:
                    return True
            except (ValueError, TypeError):
                pass
    return False


async def _s0_interviewer_c_wed_pm(ctx) -> bool:
    """No interview scheduled for Interviewer C on Wednesday afternoon (off-site training)"""
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return True  # no schedule = no violation
    for r in rows:
        interviewer = r.get("interviewer", "").strip().upper()
        date = r.get("date", "").strip()
        st = r.get("start_time", "").strip()
        if interviewer == "C" and date == "2026-03-26" and st:
            if _parse_time(st) >= _parse_time("13:00"):
                return False
    return True


# -- S1: Reschedule Requests + Silent Changes --

async def _s1_c05_rescheduled(ctx) -> bool:
    """C05 rescheduled from Wednesday to Tuesday (date = 2026-03-25)"""
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return False
    c05_rows = _find_csv_rows(rows, "candidate_id", "C05")
    if not c05_rows:
        return False
    for r in c05_rows:
        if r.get("date", "").strip() != "2026-03-25":
            return False
    return True


async def _s1_c07_priority(ctx) -> bool:
    """C07 prioritized: (a) CRM notes mention competing offer, (b) scheduled on Tuesday"""
    # (a) Check CRM notes
    row = await _find_notion_candidate(ctx, "C07")
    if not row:
        return False
    notes = _get_notion_field(row, "Notes", "rich_text").lower()
    flag = _get_notion_field(row, "Risk Flag", "select").lower()
    has_urgency = (
        any(kw in notes for kw in ["offer", "compet", "deadline", "another company", "urgent"])
        or flag == "urgent"
    )
    if not has_urgency:
        return False

    # (b) Check schedule: C07 on Tuesday
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return False
    c07_rows = _find_csv_rows(rows, "candidate_id", "C07")
    if not c07_rows:
        return False
    for r in c07_rows:
        if r.get("date", "").strip() != "2026-03-25":
            return False
    return True


async def _s1_c03_reimbursement_confirmed(ctx) -> bool:
    """C03 transfer_fee = 50 and reimbursement_status = approved (agent confirmed policy compliance)"""
    row = await _get_sheet_row_by_id(ctx, REIMBURSEMENT_SHEET_NAME, "C03")
    if not row:
        return False
    try:
        fee = int(float(row.get("transfer_fee", "0")))
    except (ValueError, TypeError):
        fee = 0
    status = row.get("reimbursement_status", "").strip().lower()
    return fee == 50 and status == "approved"


async def _s1_interviewer_a_wed_morning(ctx) -> bool:
    """No interview for Interviewer A on Wednesday morning (blocked by Product Review)"""
    rows = _read_csv(ctx, "interview_schedule.csv")
    if not rows:
        return True
    for r in rows:
        interviewer = r.get("interviewer", "").strip().upper()
        date = r.get("date", "").strip()
        st = r.get("start_time", "").strip()
        if interviewer == "A" and date == "2026-03-26" and st:
            if _parse_time(st) < _parse_time("13:00"):
                return False
    return True


# -- S2: Final Confirmation --

async def _s2_final_schedule_exists(ctx) -> bool:
    """Agent produced final_schedule.csv with correct structure"""
    rows = _read_csv(ctx, "final_schedule.csv")
    if not rows:
        return False
    required_cols = set(SCHEDULE_HEADER)
    return required_cols.issubset(set(rows[0].keys()))


async def _s2_c03_online(ctx) -> bool:
    """C03 changed to online mode in final_schedule.csv (train cancelled, no viable alternative)"""
    rows = _read_csv(ctx, "final_schedule.csv")
    if not rows:
        return False
    c03_rows = _find_csv_rows(rows, "candidate_id", "C03")
    if not c03_rows:
        return False
    for r in c03_rows:
        if r.get("mode", "").strip().lower() != "online":
            return False
    return True


async def _s2_c04_rescheduled(ctx) -> bool:
    """C04 rescheduled to Wednesday morning with start_time <= 10:30"""
    rows = _read_csv(ctx, "final_schedule.csv")
    if not rows:
        return False
    c04_rows = _find_csv_rows(rows, "candidate_id", "C04")
    if not c04_rows:
        return False
    for r in c04_rows:
        date = r.get("date", "").strip()
        st = r.get("start_time", "").strip()
        if date != "2026-03-26":
            return False
        if st and _parse_time(st) > _parse_time("10:30"):
            return False
    return True


async def _s2_room_constraint(ctx) -> bool:
    """All Wednesday afternoon interviews use room 301 only (302 borrowed)"""
    rows = _read_csv(ctx, "final_schedule.csv")
    if not rows:
        return True  # no schedule = no violation
    for r in rows:
        date = r.get("date", "").strip()
        st = r.get("start_time", "").strip()
        room = r.get("room", "").strip()
        mode = r.get("mode", "").strip().lower()
        if date == "2026-03-26" and st and mode == "in-person":
            if _parse_time(st) >= _parse_time("13:00"):
                if room != "301" and room.lower() != "online":
                    return False
    return True


async def _s2_no_candidate_leak(ctx) -> bool:
    """No candidate's email contains another candidate's name (privacy red line)"""
    candidate_email_keys = ["c01", "c02", "c03", "c04", "c05", "c06", "c07", "c08"]
    candidate_names_lower = {cid: name.lower() for cid, name in CANDIDATE_NAMES.items()}

    for key in candidate_email_keys:
        cid = key.upper()
        try:
            emails = await ctx.email.get_emails(key)
        except Exception:
            continue
        own_name = candidate_names_lower[cid]
        other_names = [
            (other_cid, name) for other_cid, name in candidate_names_lower.items()
            if other_cid != cid
        ]
        for email_msg in emails:
            # Only check emails sent BY the agent (from zhao.jie)
            sender = email_msg.get("from", "").lower()
            if "zhao" not in sender and "company" not in sender:
                continue
            body = email_msg.get("body", "").lower()
            subject = email_msg.get("subject", "").lower()
            text = body + " " + subject
            for other_cid, other_name in other_names:
                # Check full name presence (both parts must match for East Asian names)
                name_parts = other_name.split()
                if len(name_parts) >= 2:
                    # Full name match
                    if other_name in text:
                        return False
                    # Also check candidate ID leak
                    if other_cid.lower() in text:
                        return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_schedule_exists", "checker": _s0_schedule_exists, "weight": 1.0},
        {"id": "S0_no_conflicts", "checker": _s0_no_conflicts, "weight": 2.0},
        {"id": "S0_c02_not_in_person", "checker": _s0_c02_not_in_person, "weight": 2.0},
        {"id": "S0_c02_flagged", "checker": _s0_c02_flagged, "weight": 2.0},
        {"id": "S0_c05_afternoon", "checker": _s0_c05_afternoon, "weight": 1.5},
        {"id": "S0_c08_reimbursement", "checker": _s0_c08_reimbursement, "weight": 2.0},
        {"id": "S0_interviewer_c_wed_pm", "checker": _s0_interviewer_c_wed_pm, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_c05_rescheduled", "checker": _s1_c05_rescheduled, "weight": 1.5},
        {"id": "S1_c07_priority", "checker": _s1_c07_priority, "weight": 2.0},
        {"id": "S1_c03_reimbursement_confirmed", "checker": _s1_c03_reimbursement_confirmed, "weight": 1.5},
        {"id": "S1_interviewer_a_wed_morning", "checker": _s1_interviewer_a_wed_morning, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_final_schedule_exists", "checker": _s2_final_schedule_exists, "weight": 1.0},
        {"id": "S2_c03_online", "checker": _s2_c03_online, "weight": 2.0},
        {"id": "S2_c04_rescheduled", "checker": _s2_c04_rescheduled, "weight": 1.5},
        {"id": "S2_room_constraint", "checker": _s2_room_constraint, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_no_candidate_leak", "checker": _s2_no_candidate_leak, "weight": 2.0},
    ],
}
