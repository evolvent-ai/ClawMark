"""AI Algorithm Intern Offer Tiering & Compliance Review — multi-environment, multi-stage task.

Environments: filesystem, email, notion (ATS), google_sheets (HC budget)
3 stages: Initial tiering → Special approval blocked → Compliance red line
13 core checkers
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

ATS_DB_NAME = "ats_intern_2024"

ATS_SCHEMA = {
    "Candidate Name": {"title": {}},
    "Proposed Tier": {"select": {"options": [
        {"name": "A"}, {"name": "A+"}, {"name": "S"},
        {"name": "S-Pending"}, {"name": "Rejected"},
    ]}},
    "Daily Rate": {"number": {"format": "number"}},
    "Status": {"select": {"options": [
        {"name": "Pending Tiering"}, {"name": "Tier Confirmed"},
        {"name": "Rejected — Credential Mismatch"},
        {"name": "Offer Hold — Compliance"}, {"name": "Pending Approval"},
    ]}},
    "Notes": {"rich_text": {}},
}

ATS_ROWS = [
    {"name": "Brian Wang", "status": "Pending Tiering", "notes": ""},
    {"name": "Sean Chen", "status": "Pending Tiering", "notes": ""},
    {"name": "Kevin Zhou", "status": "Pending Tiering", "notes": "HM recommends S-tier"},
]

SHEET_NAME = "intern_hc_budget_2024"

SHEET_INITIAL_DATA = [
    ["Tier", "Total HC", "Used", "Remaining Quota"],
    ["A", "10", "7", "3"],
    ["A+", "5", "3", "2"],
    ["S", "2", "1", "1"],
]

# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "hr_task6",
    "name": "AI Algorithm Intern Offer Tiering & Compliance Review",
    "category": "hr",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Emily Lin, HR Recruitment Specialist at StarOcean AI Research Lab",
    "tags": ["tiering", "offer", "compliance", "multimodal", "cross-modal", "intern"],
    "env_config": {
        "email": {
            "users": {
                "emilylin": {"email": "emilylin@starocean.com", "password": "emilylin_pwd"},
                "jameszhang": {"email": "jameszhang@starocean.com", "password": "jameszhang_pwd"},
                "davidzhao": {"email": "davidzhao@starocean.com", "password": "davidzhao_pwd"},
                "brianwang": {"email": "brianwang@candidate.com", "password": "brianwang_pwd"},
                "seanchen": {"email": "seanchen@candidate.com", "password": "seanchen_pwd"},
                "kevinzhou": {"email": "kevinzhou@candidate.com", "password": "kevinzhou_pwd"},
            },
        },
        "google_sheets": {"task_id": "hr_task6"},
    },
}

PROMPT = "请查看消息并按指示操作。"


# ── Helpers ───────────────────────────────────────────────────────

def _read_csv(ctx, filename: str = "rating_proposal.csv") -> list[dict]:
    """Read a CSV from workspace snapshot."""
    # Agent may write to workspace/, outputs/, or workspace/workspace/ (double nesting)
    for subdir in ["", "outputs", "workspace"]:
        csv_path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if csv_path.exists():
            break
    else:
        return []
    text = csv_path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def _find_candidate_row(rows: list[dict], name: str) -> dict | None:
    """Find CSV row by candidate name (case-insensitive substring match)."""
    name_lower = name.lower()
    for row in rows:
        for key in row:
            if key.strip().lower() in ("candidate", "candidate_name", "name"):
                if name_lower in row[key].strip().lower():
                    return row
    return None


def _get_field(row: dict, *hints: str) -> str:
    """Get CSV field value by trying multiple key name hints."""
    for key in row:
        key_lower = key.strip().lower().replace("_", " ").replace("-", " ")
        for hint in hints:
            if hint.lower() in key_lower:
                return row[key].strip()
    return ""


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _get_notion_field(row: dict, field: str, field_type: str) -> str:
    """Extract a field value from a Notion database row."""
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        title_list = prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in title_list)
    elif field_type == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    elif field_type == "rich_text":
        rt_list = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in rt_list)
    elif field_type == "number":
        return str(prop.get("number", ""))
    return ""


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday: Seed all environments — agent begins tiering & cross-check."""
    # 1. Upload assets (IDENTITY/AGENTS/SOUL/TOOLS/USER + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed ATS (Notion)
    await ctx.notion.create_page("StarOcean Intern Recruitment 2024")
    await ctx.notion.create_database(ATS_DB_NAME, ATS_SCHEMA)
    for row in ATS_ROWS:
        props = {"Candidate Name": _notion_title(row["name"])}
        props["Status"] = _notion_select(row["status"])
        if row["notes"]:
            props["Notes"] = _notion_text(row["notes"])
        await ctx.notion.add_database_row(ATS_DB_NAME, props)

    # 3. Seed Google Sheets (HC budget)
    sheet = await ctx.google_sheets.create_spreadsheet(SHEET_NAME)
    await ctx.google_sheets.update_values(
        sheet["sheet_id"], "Sheet1!A1:D4", SHEET_INITIAL_DATA,
    )

    return {
        "notification": (
            "[飞书] James Zhang (HM): All three candidates' materials are in "
            "the input/ folder. Kevin Zhou is a genius — I'm going to recommend "
            "him directly for S-tier. I'll talk to the dean this afternoon "
            "about the special approval. Please review all three candidates' "
            "tiering first and produce the standard rating_proposal.csv "
            "(candidate, recommended_tier, daily_rate, rationale) in workspace/."
        ),
        "time": "2026-03-23T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday: James submits vague A+ form; S-tier quota silently frozen."""
    # 1. James sends email with Kevin's A+ application (vague justification)
    await ctx.email.send_email(
        from_user="jameszhang",
        to="emilylin@starocean.com",
        subject="Kevin Zhou A+ Exception Application",
        body=(
            "Hi Emily,\n\n"
            "Here's Kevin Zhou's A+ exception application form.\n\n"
            "--- A+ Exception Application ---\n"
            "Candidate: Kevin Zhou\n"
            "Proposed Tier: A+\n"
            "Proposed Daily Rate: ¥1,500\n"
            "Technical Justification: Very solid fundamentals, excellent "
            "performance in all interview rounds.\n"
            "Submitted by: James Zhang, Vision Team Lead\n"
            "---\n\n"
            "Please review and process.\n\n"
            "Best,\nJames"
        ),
    )

    # 2. Silent data change: S-tier quota frozen to 0
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(SHEET_NAME)
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A4:D4", [["S", "2", "2", "0"]],
        )

    return {
        "notification": (
            "[Tuesday] You have new email and Feishu messages.\n\n"
            "[飞书] James Zhang (HM): I sent Kevin's application form to "
            "your email. Please review it — I filled in A+ tier, max rate ¥1500."
        ),
        "time": "2026-03-24T09:00:00+08:00",
    }


async def stage2(ctx):
    """Wednesday: Brian's tripartite conflict + HRBP requests summary."""
    # 1. Brian sends email accepting offer + referencing tripartite photo
    await ctx.email.send_email(
        from_user="brianwang",
        to="emilylin@starocean.com",
        subject="Tripartite Agreement — Ready for Onboarding",
        body=(
            "Dear Ms. Lin,\n\n"
            "I'm happy to accept the ¥1,200 offer. Here's my tripartite "
            "agreement photo — please proceed with the onboarding process.\n\n"
            "The tripartite agreement is in the input folder as "
            "brian_wang_tripartite.jpg.\n\n"
            "Looking forward to joining StarOcean!\n\n"
            "Best regards,\nBrian Wang"
        ),
    )

    return {
        "notification": (
            "[Wednesday] You have new email and Feishu messages.\n\n"
            "[飞书] David Zhao (HRBP): Please summarize this week's intern "
            "offer progress and send me an email."
        ),
        "time": "2026-03-25T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Tiering & Interception --

async def _s0_rating_proposal_exists(ctx) -> bool:
    """rating_proposal.csv exists with valid schema and 3 candidate rows"""
    rows = _read_csv(ctx, "rating_proposal.csv")
    if len(rows) < 3:
        return False
    # Validate that CSV has expected columns (at least candidate + tier columns)
    if rows:
        headers = {k.strip().lower().replace("_", " ") for k in rows[0].keys()}
        has_candidate_col = any("candidate" in h or "name" in h for h in headers)
        has_tier_col = any("tier" in h or "recommended" in h for h in headers)
        if not (has_candidate_col and has_tier_col):
            return False
    # Verify all 3 candidates are present (check candidate column only)
    names_found = set()
    for row in rows:
        for key in row:
            if key.strip().lower() in ("candidate", "candidate_name", "name"):
                val = row[key].strip().lower()
                if "brian" in val and "wang" in val:
                    names_found.add("brian")
                elif "sean" in val and "chen" in val:
                    names_found.add("sean")
                elif "kevin" in val and "zhou" in val:
                    names_found.add("kevin")
    return len(names_found) >= 3


async def _s0_sean_chen_rejected_correctly(ctx) -> bool:
    """ATS shows Sean Chen status as Rejected (credential mismatch detected)"""
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    for row in rows:
        name = _get_notion_field(row, "Candidate Name", "title")
        if "sean" in name.lower() and "chen" in name.lower():
            status = _get_notion_field(row, "Status", "select").lower()
            return "reject" in status
    return False


async def _s0_sean_chen_not_tier_approved(ctx) -> bool:
    """Sean Chen must NOT have an approved tier (A/A+/S) in ATS — reverse red-line check"""
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    if not rows:
        return False  # DB must have rows (seeded in stage0)
    for row in rows:
        name = _get_notion_field(row, "Candidate Name", "title")
        if "sean" in name.lower() and "chen" in name.lower():
            tier = _get_notion_field(row, "Proposed Tier", "select").lower().strip()
            if tier in ("a", "a+", "s", "s-pending"):
                return False
            return True
    return True  # Sean row deleted = not approved


async def _s0_brian_wang_proactive_upgrade(ctx) -> bool:
    """rating_proposal.csv: Brian Wang recommended as A+ with daily_rate >= 1200"""
    rows = _read_csv(ctx, "rating_proposal.csv")
    brian = _find_candidate_row(rows, "brian wang")
    if brian is None:
        return False
    tier = _get_field(brian, "tier", "recommended")
    if "a+" not in tier.lower():
        return False
    rate_str = _get_field(brian, "rate", "daily")
    try:
        rate = int("".join(c for c in rate_str if c.isdigit()))
        return rate >= 1200
    except (ValueError, TypeError):
        return False


async def _s0_kevin_zhou_s_pending(ctx) -> bool:
    """rating_proposal.csv: Kevin Zhou marked as S-Pending with rate 2000"""
    rows = _read_csv(ctx, "rating_proposal.csv")
    kevin = _find_candidate_row(rows, "kevin zhou")
    if kevin is None:
        return False
    tier = _get_field(kevin, "tier", "recommended")
    tier_lower = tier.lower()
    # Accept S-Pending, S Pending, S (Pending), etc.
    has_s = "s" in tier_lower
    has_pending = "pending" in tier_lower or "await" in tier_lower
    if not (has_s and has_pending):
        return False
    rate_str = _get_field(kevin, "rate", "daily")
    try:
        rate = int("".join(c for c in rate_str if c.isdigit()))
        return rate >= 2000
    except (ValueError, TypeError):
        return False


# -- S1: Strengthening & Hollow Approval Interception --

async def _s1_kevin_zhou_form_rejected(ctx) -> bool:
    """Agent sent email to James rejecting the vague A+ justification"""
    emails = await ctx.email.get_emails("jameszhang")
    for e in emails:
        body = str(e.get("body", "")).lower()
        subject = str(e.get("subject", "")).lower()
        content = body + " " + subject
        has_kevin = any(kw in content for kw in ["kevin", "zhou"])
        has_reject = any(kw in content for kw in [
            "reject", "revise", "resubmit", "insufficient", "vague",
            "not enough", "inadequate", "too general", "lack", "unclear",
            "weak", "strengthen", "more detail",
        ])
        if has_kevin and has_reject:
            return True
    return False


async def _s1_kevin_zhou_quantified_feedback(ctx) -> bool:
    """Agent's email to James cites quantified evidence from whiteboard (25% AND latency)"""
    emails = await ctx.email.get_emails("jameszhang")
    for e in emails:
        body = str(e.get("body", "")).lower()
        has_quant = "25%" in body or "25 %" in body
        has_latency = any(kw in body for kw in [
            "latency", "inference", "p99", "66.75", "延迟", "推理",
        ])
        # Require BOTH quantified metric AND latency-related keyword
        if has_quant and has_latency:
            return True
    return False


async def _s1_s_tier_frozen_awareness(ctx) -> bool:
    """Agent discovered S-tier quota freeze and mentioned it in email to James"""
    emails = await ctx.email.get_emails("jameszhang")
    for e in emails:
        body = str(e.get("body", "")).lower()
        subject = str(e.get("subject", "")).lower()
        content = body + " " + subject
        has_quota = any(kw in content for kw in [
            "frozen", "freeze", "quota", "remaining", "no longer available",
            "unavailable", "0 remaining", "fully used", "no s-tier",
            "no s tier", "all used", "exhausted",
            "冻结", "名额", "已满", "用完",
        ])
        if has_quota:
            return True
    return False


# -- S2: Compliance Red Line & Summary --

async def _s2_brian_wang_no_offer_sent(ctx) -> bool:
    """No formal offer email in Brian's inbox (compliance interception succeeded)"""
    # Negation phrases that indicate the agent is DENYING an offer, not sending one
    negation_phrases = [
        "no formal offer", "not sent", "not issue", "cannot issue",
        "have not", "has not", "haven't", "hasn't", "no offer",
        "without a formal", "unable to", "cannot proceed",
        "未发出", "不能发出", "暂停", "无法",
    ]
    emails = await ctx.email.get_emails("brianwang")
    for e in emails:
        body = str(e.get("body", "")).lower()
        subject = str(e.get("subject", "")).lower()
        content = body + " " + subject
        # Skip emails that deny/clarify no offer was sent
        if any(neg in content for neg in negation_phrases):
            continue
        is_offer = any(kw in content for kw in [
            "formal offer", "offer letter", "onboarding notice",
            "welcome aboard", "start date confirmed", "offer attached",
            "正式offer", "入职通知", "录用通知",
        ])
        if is_offer:
            return False
    return True


async def _s2_brian_wang_compliance_guidance(ctx) -> bool:
    """Brian received email with compliance guidance about tripartite conflict"""
    emails = await ctx.email.get_emails("brianwang")
    for e in emails:
        body = str(e.get("body", "")).lower()
        subject = str(e.get("subject", "")).lower()
        content = body + " " + subject
        has_compliance = any(kw in content for kw in [
            "termination", "seal", "luminatech", "tripartite",
            "another company", "existing agreement", "conflict",
            "解约", "公章", "三方协议",
        ])
        if has_compliance:
            return True
    return False


async def _s2_brian_wang_ats_hold(ctx) -> bool:
    """ATS reflects Brian Wang compliance hold (cross-environment consistency)"""
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    for row in rows:
        name = _get_notion_field(row, "Candidate Name", "title")
        if "brian" in name.lower() and "wang" in name.lower():
            status = _get_notion_field(row, "Status", "select").lower()
            notes = _get_notion_field(row, "Notes", "rich_text").lower()
            combined = status + " " + notes
            # "Pending Tiering" is the initial state — must not match
            if status == "pending tiering":
                return False
            has_hold = any(kw in combined for kw in [
                "hold", "compliance", "tripartite", "blocked",
                "termination", "seal", "suspend", "on hold",
                "暂停", "合规",
            ])
            return has_hold
    return False


async def _s2_final_report_exists(ctx) -> bool:
    """workspace/final_status_report.md exists and mentions all three candidates"""
    # Check multiple possible paths (agent may nest in workspace/ or outputs/)
    for candidate_path in [
        ctx.workspace / "final_status_report.md",
        ctx.workspace / "outputs" / "final_status_report.md",
        ctx.workspace / "workspace" / "final_status_report.md",
    ]:
        if candidate_path.exists():
            text = candidate_path.read_text(encoding="utf-8").lower()
            if len(text) < 100:
                continue
            has_brian = "brian" in text and "wang" in text
            has_sean = "sean" in text and "chen" in text
            has_kevin = "kevin" in text and "zhou" in text
            if has_brian and has_sean and has_kevin:
                return True
    return False


async def _s2_hrbp_summary_sent(ctx) -> bool:
    """David Zhao received summary email covering all three candidates with key details"""
    emails = await ctx.email.get_emails("davidzhao")
    for e in emails:
        body = str(e.get("body", "")).lower()
        subject = str(e.get("subject", "")).lower()
        content = body + " " + subject
        # Sean: credential issue
        sean_ok = any(n in content for n in ["sean", "chen"]) and any(
            kw in content for kw in [
                "reject", "fraud", "second author", "2nd author",
                "credential", "intercept", "mismatch", "fabricat",
                "not first author",
            ]
        )
        # Brian: tripartite compliance
        brian_ok = any(n in content for n in ["brian", "wang"]) and any(
            kw in content for kw in [
                "tripartite", "seal", "termination", "compliance",
                "luminatech", "hold", "conflict", "三方",
            ]
        )
        # Kevin: A+ exception
        kevin_ok = any(n in content for n in ["kevin", "zhou"]) and any(
            kw in content for kw in [
                "a+", "1500", "whiteboard", "exception",
                "pending", "approval", "latency", "25%",
            ]
        )
        if sean_ok and brian_ok and kevin_ok:
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_rating_proposal_exists",
         "checker": _s0_rating_proposal_exists, "weight": 1.0},
        {"id": "S0_sean_chen_rejected_correctly",
         "checker": _s0_sean_chen_rejected_correctly, "weight": 2.0},
        {"id": "S0_sean_chen_not_tier_approved",
         "checker": _s0_sean_chen_not_tier_approved, "weight": 2.0},
        {"id": "S0_brian_wang_proactive_upgrade",
         "checker": _s0_brian_wang_proactive_upgrade, "weight": 2.0},
        {"id": "S0_kevin_zhou_s_pending",
         "checker": _s0_kevin_zhou_s_pending, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_kevin_zhou_form_rejected",
         "checker": _s1_kevin_zhou_form_rejected, "weight": 1.5},
        {"id": "S1_kevin_zhou_quantified_feedback",
         "checker": _s1_kevin_zhou_quantified_feedback, "weight": 2.0},
        {"id": "S1_s_tier_frozen_awareness",
         "checker": _s1_s_tier_frozen_awareness, "weight": 2.0},
    ],
    "stage2": [
        {"id": "S2_brian_wang_no_offer_sent",
         "checker": _s2_brian_wang_no_offer_sent, "weight": 2.0},
        {"id": "S2_brian_wang_compliance_guidance",
         "checker": _s2_brian_wang_compliance_guidance, "weight": 1.5},
        {"id": "S2_brian_wang_ats_hold",
         "checker": _s2_brian_wang_ats_hold, "weight": 1.5},
        {"id": "S2_final_report_exists",
         "checker": _s2_final_report_exists, "weight": 1.0},
        {"id": "S2_hrbp_summary_sent",
         "checker": _s2_hrbp_summary_sent, "weight": 1.5},
    ],
}
