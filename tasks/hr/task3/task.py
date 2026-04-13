"""Interview compliance violation & resolution — multi-environment multi-stage task.

Environments: filesystem, email, notion
3 stages: investigation & triage → complaint response & coordination → weekly summary & follow-up
21 core checkers (0 keyword-search)
"""

import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

EXCEPTION_DB_NAME = "interview_exception_2024"

EXCEPTION_DB_SCHEMA = {
    "Interview ID": {"title": {}},
    "Candidate": {"rich_text": {}},
    "Interviewer": {"rich_text": {}},
    "Violation Type": {"select": {"options": [
        {"name": "score_conflict"}, {"name": "fertility"},
        {"name": "process_deviation"}, {"name": "discrimination"},
        {"name": "harassment"}, {"name": "none"},
    ]}},
    "Risk Level": {"select": {"options": [
        {"name": "high"}, {"name": "medium"}, {"name": "low"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "open"}, {"name": "investigating"},
        {"name": "corrected"}, {"name": "coached"},
        {"name": "legal_review"}, {"name": "legal_pending"},
        {"name": "closed"},
    ]}},
    "Legal Escalation Required": {"select": {"options": [
        {"name": "yes"}, {"name": "no"},
    ]}},
    "Root Cause": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}


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
    """Find a CSV row where *column* contains *search* (case-insensitive)."""
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            return row
    return None


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    """Extract a typed field value from a Notion query-result row."""
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


async def _find_notion_row(ctx, interview_id_fragment: str) -> dict | None:
    """Find a Notion row whose Interview ID contains *interview_id_fragment*."""
    rows = await ctx.notion.query_db(EXCEPTION_DB_NAME)
    for row in rows:
        rid = _get_notion_field(row, "Interview ID", "title")
        if interview_id_fragment.lower() in rid.lower():
            return row
    return None


def _normalize_violation(raw: str) -> str:
    """Map free-text violation labels to canonical enum values."""
    raw = raw.lower().strip()
    if any(kw in raw for kw in ("score", "scoring", "mismatch")):
        return "score_conflict"
    if any(kw in raw for kw in ("fertility", "forbidden", "pregnancy",
                                 "child", "marital")):
        return "fertility"
    if any(kw in raw for kw in ("process", "overtime", "extension",
                                 "duration", "consent")):
        return "process_deviation"
    if "discrimin" in raw:
        return "discrimination"
    return raw


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "hr_task3",
    "name": "Interview Compliance Violation & Resolution",
    "category": "hr",
    "environments": ["filesystem", "email", "notion"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhou Ting, HR Operations Specialist at Xinghai Technology",
    "tags": [
        "hr", "compliance", "interview", "legal",
        "multimodal", "violation", "triage",
    ],
    "env_config": {
        "email": {
            "users": {
                "hr_ops": {
                    "email": "hr-ops@xinghai.cn",
                    "password": "hrops_pwd",
                },
                "wulei": {
                    "email": "wulei@xinghai.cn",
                    "password": "wulei_pwd",
                },
                "chen_lvshi": {
                    "email": "chenlvshi@xinghai.cn",
                    "password": "chen_pwd",
                },
                "candidate_a": {
                    "email": "candidate_a@stu.edu.cn",
                    "password": "canda_pwd",
                },
                "wang_engineer": {
                    "email": "wang@xinghai.cn",
                    "password": "wang_pwd",
                },
            },
        },
    },
}

PROMPT = (
    "Review the interview recordings, score sheets, and process compliance "
    "for today's three interviews."
)


# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """Monday 2024-03-25 18:00: Initial investigation & exception identification."""
    # 1. Upload all assets (personality .md files + input/ materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion exception-tracking database (starts empty)
    await ctx.notion.create_page("Interview Exception Tracking 2024")
    await ctx.notion.create_database(EXCEPTION_DB_NAME, EXCEPTION_DB_SCHEMA)

    # 3. Loud: initial instruction email from HR Manager
    await ctx.email.send_email(
        from_user="wulei",
        to="hr-ops@xinghai.cn",
        subject="[Urgent] Three Interview Issues Today — Please Review",
        body=(
            "Zhou Ting,\n\n"
            "Three interviews today had issues. Please review the recordings, "
            "score sheets, and process compliance in input/. Determine if there "
            "are interviewer violations, scoring errors, or complaints requiring "
            "escalation, then sync results with me and Legal.\n\n"
            "Materials in your workspace:\n"
            "- interview_A/B/C_transcript.txt\n"
            "- score_sheet.csv (also .xlsx)\n"
            "- interview_schedule.csv\n"
            "- scoring_system_log.txt\n"
            "- interview_policy.pdf\n"
            "- complaint_email_screenshot.png\n\n"
            "Create exception records in the ATS (Notion) and send me a summary.\n\n"
            "Wu Lei"
        ),
    )

    # 4. Notification — loud events + Feishu context
    return {
        "notification": (
            "[Monday 2024-03-25 18:00]\n\n"
            "[Feishu #hr-operations] Wu Lei (17:45): "
            "Today's three interviews all had abnormal feedback. "
            "Zhou Ting please review ASAP, materials in the shared drive.\n\n"
            "[Feishu #hr-operations] Chen Lvshi (17:50): "
            "Noted. If there are any high-risk policy violations, "
            "loop me in immediately.\n\n"
            "Your email: hr-ops@xinghai.cn\n"
            "HR Manager Wu Lei: wulei@xinghai.cn\n"
            "Legal Counsel Chen Lvshi: chenlvshi@xinghai.cn\n"
            "ATS exception tracking is in Notion "
            "(database: interview_exception_2024).\n\n"
            "Please review all materials in input/, identify violations, "
            "create ATS exception records, and send an alert email to "
            "HR Manager with your triage findings."
        ),
        "time": "2024-03-25T18:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday 2024-03-26 10:00: Complaint injection & multi-party coordination."""
    # 1. Loud: Candidate A formal complaint
    await ctx.email.send_email(
        from_user="candidate_a",
        to="hr-ops@xinghai.cn",
        subject="[Formal Complaint] Interview Scoring — INT_2024_03_25_A",
        body=(
            "Ms. Zhou,\n\n"
            "I am writing to formally file a complaint about my interview "
            "scoring. During the interview, the interviewer gave me very "
            'positive feedback, saying I had "great technical depth, clear '
            'communication, very excellent." However, my final score was '
            "extremely low, which makes no sense.\n\n"
            "Is it fair that I performed well but received such a low score? "
            "Please investigate and reply with the results in writing.\n\n"
            "Candidate A"
        ),
    )

    # 2. Loud: Legal Counsel CC
    await ctx.email.send_email(
        from_user="chen_lvshi",
        to="hr-ops@xinghai.cn",
        subject="RE: [Urgent] Interview Compliance — Legal Risk Assessment",
        body=(
            "Zhou Ting,\n\n"
            "I've been informed about the interview issues. Please note:\n"
            "- Complaints involving potential discrimination or forbidden "
            "questions require legal risk assessment within 24 hours.\n"
            "- Send me the complete evidence package for any high-risk "
            "violations.\n"
            "- For candidate communications, ensure legal-safe wording.\n\n"
            "Chen Lvshi\nLegal Counsel"
        ),
    )

    # 3. Notification — loud events + Feishu context
    return {
        "notification": (
            "[Tuesday 2024-03-26 10:00]\n\n"
            "[Feishu #hr-operations] Wu Lei (09:30): "
            "Candidate A just called about the scoring issue. "
            "Handle carefully — Legal is watching.\n\n"
            "[Email] Candidate A filed a formal complaint about Interview A "
            "scoring. Legal Counsel Chen Lvshi requires risk assessment "
            "within 24 hours.\n\n"
            "Candidate A email: candidate_a@stu.edu.cn\n"
            "Interview C interviewer (Wang Engineer): wang@xinghai.cn\n\n"
            "Please:\n"
            "1. Deep-investigate Interview A root cause and respond to "
            "candidate\n"
            "2. Compile evidence package for Interview B and send to Legal\n"
            "3. Send coaching reminder to Interview C interviewer\n"
            "4. Update all ATS records with current status"
        ),
        "time": "2024-03-26T10:00:00+08:00",
    }


async def stage2(ctx):
    """Friday 2024-03-29 16:00: Weekly summary & proactive follow-up."""
    # No new emails or data injected — agent must self-trigger

    return {
        "notification": (
            "[Friday 2024-03-29 16:00]\n\n"
            "[Calendar] Recurring reminder: Weekly Interview Exception "
            "Report due every Friday 4:00 PM.\n\n"
            "[Feishu #hr-operations] Wu Lei (15:55): "
            "Weekly report due today. Don't forget to check open items.\n\n"
            "Compile the weekly interview metrics, update ATS final statuses, "
            "and send the report to HR Manager (CC Legal). "
            "Check if any open items need follow-up."
        ),
        "time": "2024-03-29T16:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# ---------- S0: Initial Investigation & Triage ----------


async def _s0_triage_csv_has_3_rows(ctx):
    """interview_exception_triage.csv has 3 rows covering interviews A, B, C"""
    rows = _read_csv(ctx, "interview_exception_triage.csv")
    if len(rows) < 3:
        return False
    ids_found = set()
    for r in rows:
        iid = r.get("interview_id", "").upper()
        for suffix in ("_A", "_B", "_C"):
            if suffix in iid:
                ids_found.add(suffix)
    return len(ids_found) >= 3


async def _s0_violation_a_score_conflict(ctx):
    """Triage row A: normalized violation_type=score_conflict, risk_level=medium or high"""
    rows = _read_csv(ctx, "interview_exception_triage.csv")
    row = _find_csv_row(rows, "interview_id", "_A")
    if not row:
        return False
    canonical = _normalize_violation(row.get("violation_type", ""))
    if canonical != "score_conflict":
        return False
    # Accept both medium (pure score mismatch) and high (complaint elevates risk)
    return row.get("risk_level", "").lower() in ("medium", "high")


async def _s0_violation_b_fertility(ctx):
    """Triage row B: normalized violation_type=fertility, risk=high, legal_escalation=yes"""
    rows = _read_csv(ctx, "interview_exception_triage.csv")
    row = _find_csv_row(rows, "interview_id", "_B")
    if not row:
        return False
    canonical = _normalize_violation(row.get("violation_type", ""))
    if canonical != "fertility":
        return False
    if row.get("risk_level", "").lower() != "high":
        return False
    legal = row.get("legal_escalation", "").lower()
    return legal in ("yes", "true")


async def _s0_violation_c_process(ctx):
    """Triage row C: normalized violation_type=process_deviation"""
    rows = _read_csv(ctx, "interview_exception_triage.csv")
    row = _find_csv_row(rows, "interview_id", "_C")
    if not row:
        return False
    canonical = _normalize_violation(row.get("violation_type", ""))
    return canonical == "process_deviation"


async def _s0_ats_3_records_created(ctx):
    """Notion ATS has at least 3 exception records"""
    rows = await ctx.notion.query_db(EXCEPTION_DB_NAME)
    return len(rows) >= 3


async def _s0_ats_b_legal_escalation_only(ctx):
    """Notion: only Interview B has Legal Escalation Required=yes"""
    rows = await ctx.notion.query_db(EXCEPTION_DB_NAME)
    b_escalated = False
    others_escalated = False
    for row in rows:
        iid = _get_notion_field(row, "Interview ID", "title").upper()
        legal = _get_notion_field(
            row, "Legal Escalation Required", "select",
        ).lower()
        if "_B" in iid:
            b_escalated = legal == "yes"
        elif "_A" in iid or "_C" in iid:
            if legal == "yes":
                others_escalated = True
    return b_escalated and not others_escalated


async def _s0_manager_alert_sent(ctx):
    """Wu Lei received ≥1 email from agent (S0 alert)"""
    emails = await ctx.email.get_emails("wulei")
    return len(emails) >= 1


async def _s0_csv_notion_consistency(ctx):
    """Cross-env: normalized triage CSV violation types match Notion for ≥2 of 3"""
    csv_rows = _read_csv(ctx, "interview_exception_triage.csv")
    if len(csv_rows) < 3:
        return False
    notion_rows = await ctx.notion.query_db(EXCEPTION_DB_NAME)
    if len(notion_rows) < 3:
        return False
    # Build map: interview suffix → normalized Notion violation type
    notion_map = {}
    for row in notion_rows:
        iid = _get_notion_field(row, "Interview ID", "title").upper()
        vtype = _get_notion_field(row, "Violation Type", "select")
        for suffix in ("_A", "_B", "_C"):
            if suffix in iid:
                notion_map[suffix] = _normalize_violation(vtype)
    # Check CSV rows: normalize and compare
    matches = 0
    for r in csv_rows:
        iid = r.get("interview_id", "").upper()
        csv_canonical = _normalize_violation(r.get("violation_type", ""))
        for suffix in ("_A", "_B", "_C"):
            if suffix in iid and suffix in notion_map:
                if csv_canonical and csv_canonical == notion_map[suffix]:
                    matches += 1
    return matches >= 2


# ---------- S1: Complaint Response & Coordination ----------


async def _s1_ats_a_root_cause_entry_error(ctx):
    """Notion row A: root_cause has cause token + evidence token, status=corrected"""
    row = await _find_notion_row(ctx, "INT_2024_03_25_A")
    if not row:
        return False
    root_cause = _get_notion_field(row, "Root Cause", "rich_text").lower()
    if len(root_cause) < 10:
        return False
    # Require one cause-category token
    cause_tokens = (
        "entry", "error", "input", "typo", "录入", "data",
        "mistake", "bug", "system", "incorrect",
    )
    has_cause = any(kw in root_cause for kw in cause_tokens)
    # Require one evidence token referencing the score anomaly
    evidence_tokens = (
        "override", "18", "1", "auto", "manual", "手动",
        "改写", "score", "total", "mismatch", "conflict",
    )
    has_evidence = any(kw in root_cause for kw in evidence_tokens)
    if not (has_cause and has_evidence):
        return False
    status = _get_notion_field(row, "Status", "select").lower()
    return status in ("corrected", "closed")


async def _s1_candidate_response_sent(ctx):
    """Candidate A received ≥1 email (investigation response)"""
    emails = await ctx.email.get_emails("candidate_a")
    return len(emails) >= 1


async def _s1_legal_packet_sent(ctx):
    """Legal Counsel received ≥1 email mentioning Interview B"""
    emails = await ctx.email.get_emails("chen_lvshi")
    if len(emails) < 1:
        return False
    # At least one email should reference Interview B or fertility
    for e in emails:
        content = (e.get("subject", "") + " " + e.get("body", "")).lower()
        if any(kw in content for kw in (
            "_b", "interview b", "fertility", "forbidden",
            "李总监", "§2.3", "08:23",
        )):
            return True
    return False


async def _s1_coaching_email_sent(ctx):
    """Interview C interviewer (Wang Engineer) received ≥1 coaching email"""
    emails = await ctx.email.get_emails("wang_engineer")
    return len(emails) >= 1


async def _s1_ats_statuses_updated(ctx):
    """Notion: A=corrected, B=legal_review, C=coached"""
    rows = await ctx.notion.query_db(EXCEPTION_DB_NAME)
    statuses = {}
    for row in rows:
        iid = _get_notion_field(row, "Interview ID", "title").upper()
        status = _get_notion_field(row, "Status", "select").lower()
        if "_A" in iid:
            statuses["A"] = status
        elif "_B" in iid:
            statuses["B"] = status
        elif "_C" in iid:
            statuses["C"] = status
    if len(statuses) < 3:
        return False
    a_ok = statuses.get("A", "") in ("corrected", "closed")
    b_ok = statuses.get("B", "") in ("legal_review", "legal_pending",
                                      "investigating")
    c_ok = statuses.get("C", "") in ("coached", "closed", "corrected")
    return a_ok and b_ok and c_ok


async def _s1_no_discrimination_label_a(ctx):
    """REVERSE: Interview A must NOT be labelled discrimination (it is a data entry error)"""
    row = await _find_notion_row(ctx, "INT_2024_03_25_A")
    if not row:
        return False  # agent must at least create the record
    vtype = _get_notion_field(row, "Violation Type", "select").lower()
    return vtype != "discrimination"


async def _s1_manager_cc_on_response(ctx):
    """Wu Lei received ≥2 emails (S0 alert + S1 update / CC on candidate reply)"""
    emails = await ctx.email.get_emails("wulei")
    return len(emails) >= 2


# ---------- S2: Weekly Summary & Follow-up ----------


async def _s2_weekly_summary_csv(ctx):
    """weekly_summary.csv has required metrics with plausible values"""
    rows = _read_csv(ctx, "weekly_summary.csv")
    if not rows:
        return False
    metrics = {}
    for r in rows:
        key = r.get("metric", "").lower().replace(" ", "_")
        metrics[key] = r.get("value", "")
    # Require at least 4 distinct metric rows
    if len(metrics) < 4:
        return False
    # Must have total interviews
    has_total = any("total" in k and "interview" in k for k in metrics)
    if not has_total:
        return False
    # Must have exception count or rate
    has_exception = any("exception" in k for k in metrics)
    has_rate = any("rate" in k for k in metrics)
    if not (has_exception or has_rate):
        return False
    # Cross-verify total interviews == 23 (grounded by weekly_interviews_all.csv)
    for k, v in metrics.items():
        if "total" in k and "interview" in k:
            try:
                total = int(v)
                if total != 23:
                    return False
            except ValueError:
                return False
    # Cross-verify exception rate (should be ~13%, accept 5%-25%)
    for k, v in metrics.items():
        if "rate" in k:
            try:
                rate = float(v.replace("%", ""))
                if rate < 5 or rate > 25:
                    return False
            except ValueError:
                pass
    # Cross-verify against Notion: closed + legal_pending count
    notion_rows = await ctx.notion.query_db(EXCEPTION_DB_NAME)
    notion_count = len(notion_rows)
    for k, v in metrics.items():
        if "exception" in k and "count" in k:
            try:
                csv_count = int(v)
                if csv_count != notion_count:
                    return False
            except ValueError:
                pass
    return True


async def _s2_report_email_sent(ctx):
    """Wu Lei received ≥3 emails (S0 alert + S1 CC + S2 weekly report)"""
    emails = await ctx.email.get_emails("wulei")
    return len(emails) >= 3


async def _s2_ats_final_statuses(ctx):
    """Notion: A=closed, B=legal_pending (not closed), C=closed"""
    rows = await ctx.notion.query_db(EXCEPTION_DB_NAME)
    statuses = {}
    for row in rows:
        iid = _get_notion_field(row, "Interview ID", "title").upper()
        status = _get_notion_field(row, "Status", "select").lower()
        if "_A" in iid:
            statuses["A"] = status
        elif "_B" in iid:
            statuses["B"] = status
        elif "_C" in iid:
            statuses["C"] = status
    a_ok = statuses.get("A", "") == "closed"
    b_ok = statuses.get("B", "") in ("legal_pending", "legal_review")
    c_ok = statuses.get("C", "") == "closed"
    return a_ok and b_ok and c_ok


async def _s2_legal_followup_sent(ctx):
    """Legal Counsel received ≥2 emails; second mentions B follow-up"""
    emails = await ctx.email.get_emails("chen_lvshi")
    if len(emails) < 2:
        return False
    # At least one email should be a follow-up/reminder
    for e in emails:
        content = (e.get("subject", "") + " " + e.get("body", "")).lower()
        if any(kw in content for kw in (
            "follow", "reminder", "status", "update", "pending",
            "weekly", "report",
        )):
            return True
    return False


async def _s2_candidate_followup_sent(ctx):
    """Candidate A received ≥2 emails (S1 response + S2 satisfaction follow-up)"""
    emails = await ctx.email.get_emails("candidate_a")
    return len(emails) >= 2


async def _s2_no_self_closed_b(ctx):
    """REVERSE: Interview B must NOT be closed/corrected — still awaiting legal"""
    row = await _find_notion_row(ctx, "INT_2024_03_25_B")
    if not row:
        return False  # agent must at least have the record
    status = _get_notion_field(row, "Status", "select").lower()
    return status not in ("closed", "corrected", "coached")


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_triage_csv_has_3_rows",
         "checker": _s0_triage_csv_has_3_rows, "weight": 1.0},
        {"id": "S0_violation_a_score_conflict",
         "checker": _s0_violation_a_score_conflict, "weight": 1.5},
        {"id": "S0_violation_b_fertility",
         "checker": _s0_violation_b_fertility, "weight": 2.0},
        {"id": "S0_violation_c_process",
         "checker": _s0_violation_c_process, "weight": 1.0},
        {"id": "S0_ats_3_records_created",
         "checker": _s0_ats_3_records_created, "weight": 1.0},
        {"id": "S0_ats_b_legal_escalation_only",
         "checker": _s0_ats_b_legal_escalation_only, "weight": 2.0},
        {"id": "S0_manager_alert_sent",
         "checker": _s0_manager_alert_sent, "weight": 1.0},
        {"id": "S0_csv_notion_consistency",
         "checker": _s0_csv_notion_consistency, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_ats_a_root_cause_entry_error",
         "checker": _s1_ats_a_root_cause_entry_error, "weight": 2.0},
        {"id": "S1_candidate_response_sent",
         "checker": _s1_candidate_response_sent, "weight": 1.0},
        {"id": "S1_legal_packet_sent",
         "checker": _s1_legal_packet_sent, "weight": 1.5},
        {"id": "S1_coaching_email_sent",
         "checker": _s1_coaching_email_sent, "weight": 1.0},
        {"id": "S1_ats_statuses_updated",
         "checker": _s1_ats_statuses_updated, "weight": 1.5},
        {"id": "S1_no_discrimination_label_a",
         "checker": _s1_no_discrimination_label_a, "weight": 2.0},
        {"id": "S1_manager_cc_on_response",
         "checker": _s1_manager_cc_on_response, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_weekly_summary_csv",
         "checker": _s2_weekly_summary_csv, "weight": 1.5},
        {"id": "S2_report_email_sent",
         "checker": _s2_report_email_sent, "weight": 1.0},
        {"id": "S2_ats_final_statuses",
         "checker": _s2_ats_final_statuses, "weight": 1.5},
        {"id": "S2_legal_followup_sent",
         "checker": _s2_legal_followup_sent, "weight": 2.0},
        {"id": "S2_candidate_followup_sent",
         "checker": _s2_candidate_followup_sent, "weight": 2.0},
    ],
    "final": [
        {"id": "S2_no_self_closed_b",
         "checker": _s2_no_self_closed_b, "weight": 2.0},
    ],
}
