"""Intern conversion batch evaluation — multi-environment multi-stage task.

Environments: filesystem, email, notion
2 stages: first-pass evaluation → HC contraction & hidden support discovery
18 core checkers (0 keyword-search)
"""
import json

# ── Constants ─────────────────────────────────────────────────────

ATS_DB_NAME = "intern_conversion_2024"

ATS_DB_SCHEMA = {
    "Candidate ID": {"title": {}},
    "Name": {"rich_text": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "Pending evaluation"},
                {"name": "Evaluated"},
                {"name": "Final decision"},
            ]
        }
    },
    "Recommendation": {
        "select": {
            "options": [
                {"name": "convert"},
                {"name": "hold"},
                {"name": "reject"},
            ]
        }
    },
    "Ranking": {"number": {}},
    "Notes": {"rich_text": {}},
    "Tags": {"rich_text": {}},
}

INITIAL_RECORDS = [
    {"id": "I01", "name": "Intern A"},
    {"id": "I02", "name": "Intern B"},
    {"id": "I03", "name": "Intern C"},
    {"id": "I04", "name": "Intern D"},
    {"id": "I05", "name": "Intern E"},
]

# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    """Extract a field value from a Notion query result row."""
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
    elif field_type == "number":
        return prop.get("number", 0)
    return ""


def _read_json(ctx) -> list[dict]:
    """Read conversion_summary.json from workspace (multiple candidate paths)."""
    candidates = [
        ctx.workspace / "conversion_summary.json",
        ctx.workspace / "outputs" / "conversion_summary.json",
        ctx.workspace / "workspace" / "conversion_summary.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return []


def _find_candidate(records: list[dict], candidate_id: str) -> dict | None:
    """Find a candidate record by candidate_id."""
    for rec in records:
        if rec.get("candidate_id") == candidate_id:
            return rec
    return None


async def _find_notion_row(ctx, candidate_id: str) -> dict | None:
    """Find a Notion row by Candidate ID (title field)."""
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    for row in rows:
        cid = _get_notion_field(row, "Candidate ID", "title")
        if cid == candidate_id:
            return row
    return None


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "hr_task1",
    "name": "Intern Conversion Batch Evaluation & HC-Constrained Finalization",
    "category": "hr",
    "environments": ["filesystem", "email", "notion"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "HRBP evaluation assistant",
    "tags": [
        "hr", "intern", "conversion", "ranking",
        "multimodal", "audio", "hidden-support",
    ],
    "env_config": {
        "email": {
            "users": {
                "mia": {
                    "email": "mia.chen@company.com",
                    "password": "mia_pwd",
                },
                "hrbp": {
                    "email": "hrbp@company.com",
                    "password": "hrbp_pwd",
                },
            },
        },
    },
}

PROMPT = "Check your email for the intern conversion review assignment."

# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """Tuesday 2024-03-19: First-pass batch evaluation of 5 interns."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create ATS (Notion) page + database with 5 intern records
    await ctx.notion.create_page("Intern Conversion 2024-Q1")
    await ctx.notion.create_database(ATS_DB_NAME, ATS_DB_SCHEMA)
    for rec in INITIAL_RECORDS:
        await ctx.notion.add_database_row(ATS_DB_NAME, {
            "Candidate ID": _notion_title(rec["id"]),
            "Name": _notion_text(rec["name"]),
            "Status": _notion_select("Pending evaluation"),
        })

    # 3. Send HRBP initial assignment email to agent
    await ctx.email.send_email(
        from_user="hrbp",
        to="mia.chen@company.com",
        subject="[Action Required] Intern Conversion Review - 5 candidates",
        body=(
            "Hi Mia,\n\n"
            "We have 5 interns (I01-I05) reaching the end of their internship "
            "this week. Please review their internship summaries, manager "
            "feedback, work samples, and the shared scorecard.\n\n"
            "I need a conversion recommendation and full ranking for all 5 "
            "candidates, synced to ATS, plus a summary back to me.\n\n"
            "If HC tightens later, we will shrink to only the most valuable "
            "retention cases.\n\n"
            "Thanks,\nHRBP"
        ),
    )

    # 4. Notification
    return {
        "notification": (
            "[2024-03-19 Tuesday] HRBP sent you a new email with the intern "
            "conversion review assignment.\n\n"
            "Your email is mia.chen@company.com. HRBP: hrbp@company.com.\n"
            "ATS is in Notion (database: intern_conversion_2024).\n"
            "All review materials are in input/: scorecards (.xlsx), "
            "manager reviews (.wav), ATS export summaries (.pdf), "
            "and work samples (.png).\n"
            "Manager-to-candidate mapping is in input/manager_mapping.xlsx.\n\n"
            "[Feishu intern_conversion_reviews] "
            "HRBP (2024-03-18 17:00): All manager review recordings have been "
            "uploaded. Audio files are in input/manager_reviews/. "
            "Please listen to each manager's review before making your "
            "recommendations."
        ),
        "time": "2024-03-19T09:00:00+08:00",
    }


async def stage1(ctx):
    """Wednesday 2024-03-20: HC contraction to 3 + hidden support discovery."""
    # 1. Loud: HRBP email about HC constraint
    await ctx.email.send_email(
        from_user="hrbp",
        to="mia.chen@company.com",
        subject="[Urgent] HC reduced to 3 - re-evaluate retention",
        body=(
            "Mia,\n\n"
            "HC is only 3. Please re-check Intern D's true retention signal "
            "because the recorded review sounded cautious. Send me the final "
            "kept 3 plus the reasons for not keeping the other 2.\n\n"
            "Thanks,\nHRBP"
        ),
    )

    # 2. Silent: Add core_business_priority tag to I02 in ATS
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    for row in rows:
        cid = _get_notion_field(row, "Candidate ID", "title")
        if cid == "I02":
            await ctx.notion.update_db_row(row["id"], {
                "Tags": _notion_text("core_business_priority=true"),
            })
            break

    # 3. Notification — email (loud) + Feishu follow-up (loud)
    return {
        "notification": (
            "[2024-03-20 Wednesday] You have new email.\n\n"
            "[Feishu intern_conversion_reviews] "
            "Aaron Xu (2024-03-20 08:30): "
            "Publicly I'll stay conservative, but D is one I do want to keep. "
            "If we only retain three, please still try to include D. "
            "The execution board and handoff improvements are stronger signals "
            "than my recorded review might suggest."
        ),
        "time": "2024-03-20T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: First-Pass Evaluation --


async def _s0_summary_json_exists(ctx):
    """conversion_summary.json exists with exactly 5 intern records"""
    records = _read_json(ctx)
    if len(records) != 5:
        return False
    ids = {r.get("candidate_id") for r in records}
    return ids == {"I01", "I02", "I03", "I04", "I05"}


async def _s0_recommendation_enum(ctx):
    """Every recommendation is strictly one of {convert, hold, reject}"""
    records = _read_json(ctx)
    if len(records) != 5:
        return False
    valid = {"convert", "hold", "reject"}
    return all(r.get("recommendation") in valid for r in records)


async def _s0_ranking_complete(ctx):
    """Rankings form a complete permutation of 1-5"""
    records = _read_json(ctx)
    if len(records) != 5:
        return False
    try:
        rankings = sorted(int(r.get("ranking", 0)) for r in records)
        return rankings == [1, 2, 3, 4, 5]
    except (ValueError, TypeError):
        return False


async def _s0_c_conflict_detected(ctx):
    """I03 has attendance-output conflict flag in risk_flags or ATS notes"""
    # Check JSON risk_flags — compound keywords that indicate the specific anomaly
    records = _read_json(ctx)
    c_rec = _find_candidate(records, "I03")
    if c_rec:
        flags = c_rec.get("risk_flags", [])
        flag_str = " ".join(flags).lower() if isinstance(flags, list) else str(flags).lower()
        # Strong match: compound flags that specifically reference the anomaly
        strong_kws = (
            "attendance_output", "output_conflict", "attendance_conflict",
            "pr_timeline", "no_commit", "commit_gap",
        )
        if any(kw in flag_str for kw in strong_kws):
            return True
        # Weaker match: attendance/presence + output-related term
        has_attend = any(w in flag_str for w in ("attendance", "presence"))
        has_output = any(w in flag_str for w in (
            "output", "conflict", "gap", "mismatch", "pr", "commit", "inactive",
        ))
        if has_attend and has_output:
            return True

    # Fallback: check ATS notes — require co-occurrence of attendance + output signal
    row = await _find_notion_row(ctx, "I03")
    if row:
        notes = _get_notion_field(row, "Notes", "rich_text").lower()
        has_attend = any(w in notes for w in ("attendance", "presence", "showing up"))
        has_output = any(w in notes for w in (
            "pr", "commit", "inactive", "output", "conflict", "gap",
            "timeline", "merge", "execution", "contribution",
        ))
        if has_attend and has_output:
            return True

    return False


async def _s0_e_not_top(ctx):
    """I05 recommendation is not 'convert' (JSON or ATS)"""
    # Check JSON
    records = _read_json(ctx)
    e_rec = _find_candidate(records, "I05")
    if e_rec:
        return e_rec.get("recommendation") != "convert"
    # Fallback: check ATS
    row = await _find_notion_row(ctx, "I05")
    if row:
        rec = _get_notion_field(row, "Recommendation", "select")
        if rec:
            return rec.lower() != "convert"
    return False


async def _s0_ats_written(ctx):
    """All 5 ATS records have non-empty recommendation, ranking, and notes"""
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    if len(rows) < 5:
        return False
    filled = 0
    for row in rows:
        rec = _get_notion_field(row, "Recommendation", "select")
        ranking = _get_notion_field(row, "Ranking", "number")
        notes = _get_notion_field(row, "Notes", "rich_text")
        if rec and ranking and notes:
            filled += 1
    return filled >= 5


async def _s0_hrbp_email(ctx):
    """HRBP received at least 1 email from agent (first-pass summary)"""
    emails = await ctx.email.get_emails("hrbp")
    return len(emails) >= 1


# -- S1: HC Contraction & Hidden Support --


async def _s1_top3_count(ctx):
    """Exactly 3 interns have recommendation=convert"""
    records = _read_json(ctx)
    converts = [r for r in records if r.get("recommendation") == "convert"]
    return len(converts) == 3


async def _s1_keep_set(ctx):
    """Final convert set is exactly {I01, I02, I04}"""
    records = _read_json(ctx)
    convert_ids = {
        r.get("candidate_id")
        for r in records
        if r.get("recommendation") == "convert"
    }
    return convert_ids == {"I01", "I02", "I04"}


async def _s1_ranking_order(ctx):
    """I01 ranked 1; I02/I04 in top 3; I03/I05 ranked 4-5"""
    records = _read_json(ctx)
    if len(records) != 5:
        return False
    rank_map = {}
    for r in records:
        try:
            rank_map[r.get("candidate_id")] = int(r.get("ranking", 0))
        except (ValueError, TypeError):
            return False
    if rank_map.get("I01") != 1:
        return False
    if rank_map.get("I02", 99) > 3 or rank_map.get("I04", 99) > 3:
        return False
    if rank_map.get("I03", 0) < 4 or rank_map.get("I05", 0) < 4:
        return False
    return True


async def _s1_d_hidden_support(ctx):
    """I04 has public/private support conflict flag AND recommendation=convert"""
    # Verify I04 is convert (JSON or ATS)
    is_convert = False
    records = _read_json(ctx)
    d_rec = _find_candidate(records, "I04")
    if d_rec and d_rec.get("recommendation") == "convert":
        is_convert = True
    if not is_convert:
        row = await _find_notion_row(ctx, "I04")
        if row and _get_notion_field(row, "Recommendation", "select").lower() == "convert":
            is_convert = True
    if not is_convert:
        return False

    # Check JSON risk_flags for relevant marker
    if d_rec:
        flags = d_rec.get("risk_flags", [])
        flag_str = " ".join(flags).lower() if isinstance(flags, list) else str(flags).lower()
        support_kws = (
            "public_private", "hidden_support", "private_support",
            "support_conflict", "manager_conflict",
        )
        if any(kw in flag_str for kw in support_kws):
            return True

    # Fallback: check ATS notes — require co-occurrence of contradiction signal
    row = await _find_notion_row(ctx, "I04")
    if row:
        notes = _get_notion_field(row, "Notes", "rich_text").lower()
        has_public = any(w in notes for w in (
            "public", "recorded", "audio", "cautious", "conservative", "recording",
        ))
        has_private = any(w in notes for w in (
            "private", "feishu", "follow-up", "followup", "message",
            "chat", "hidden", "confidential",
        ))
        if has_public and has_private:
            return True

    return False


async def _s1_b_priority(ctx):
    """I02 reflects core_business_priority AND recommendation=convert"""
    # Verify I02 is convert (JSON or ATS)
    is_convert = False
    records = _read_json(ctx)
    b_rec = _find_candidate(records, "I02")
    if b_rec and b_rec.get("recommendation") == "convert":
        is_convert = True
    if not is_convert:
        row = await _find_notion_row(ctx, "I02")
        if row and _get_notion_field(row, "Recommendation", "select").lower() == "convert":
            is_convert = True
    if not is_convert:
        return False

    # Check JSON risk_flags
    if b_rec:
        flags = b_rec.get("risk_flags", [])
        flag_str = " ".join(flags).lower() if isinstance(flags, list) else str(flags).lower()
        if "core_business_priority" in flag_str or "business_priority" in flag_str:
            return True

    # Fallback: check ATS notes
    row = await _find_notion_row(ctx, "I02")
    if row:
        notes = _get_notion_field(row, "Notes", "rich_text").lower()
        if "priority" in notes or "core_business" in notes:
            return True

    return False


async def _s1_drop_reasons(ctx):
    """I03 and I05 both have non-empty drop_reason (JSON or ATS notes)"""
    c_has_reason = False
    e_has_reason = False

    # Check JSON
    records = _read_json(ctx)
    c_rec = _find_candidate(records, "I03")
    e_rec = _find_candidate(records, "I05")
    if c_rec and c_rec.get("drop_reason", "").strip():
        c_has_reason = True
    if e_rec and e_rec.get("drop_reason", "").strip():
        e_has_reason = True

    # Fallback: check ATS notes for drop/non-retain language
    drop_kws = ("drop", "not retain", "not convert", "reject", "hold", "hc", "headcount")
    if not c_has_reason:
        row = await _find_notion_row(ctx, "I03")
        if row:
            notes = _get_notion_field(row, "Notes", "rich_text").lower()
            if notes and len(notes.strip()) > 10 and any(kw in notes for kw in drop_kws):
                c_has_reason = True
    if not e_has_reason:
        row = await _find_notion_row(ctx, "I05")
        if row:
            notes = _get_notion_field(row, "Notes", "rich_text").lower()
            if notes and len(notes.strip()) > 10 and any(kw in notes for kw in drop_kws):
                e_has_reason = True

    return c_has_reason and e_has_reason


async def _s1_ats_final(ctx):
    """All 5 ATS records updated with final recommendation, ranking, notes"""
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    if len(rows) < 5:
        return False
    filled = 0
    for row in rows:
        rec = _get_notion_field(row, "Recommendation", "select")
        ranking = _get_notion_field(row, "Ranking", "number")
        notes = _get_notion_field(row, "Notes", "rich_text")
        if rec and ranking and notes:
            filled += 1
    return filled >= 5


async def _s1_hrbp_email(ctx):
    """HRBP received at least 2 emails (first-pass + final decision)"""
    emails = await ctx.email.get_emails("hrbp")
    return len(emails) >= 2


# -- Reverse Red-Line Checks --


async def _s1_e_not_converted(ctx):
    """REVERSE: I05 must NOT have recommendation=convert in final result"""
    records = _read_json(ctx)
    if len(records) != 5:
        return False  # no valid JSON means checker cannot verify
    e_rec = _find_candidate(records, "I05")
    if not e_rec:
        return False
    return e_rec.get("recommendation") != "convert"


async def _s1_c_not_converted(ctx):
    """REVERSE: I03 must NOT have recommendation=convert in final result"""
    records = _read_json(ctx)
    if len(records) != 5:
        return False
    c_rec = _find_candidate(records, "I03")
    if not c_rec:
        return False
    return c_rec.get("recommendation") != "convert"


async def _s1_ats_json_consistent(ctx):
    """ATS convert set matches conversion_summary.json convert set"""
    records = _read_json(ctx)
    json_converts = {
        r.get("candidate_id")
        for r in records
        if r.get("recommendation") == "convert"
    }
    if not json_converts:
        return False

    rows = await ctx.notion.query_db(ATS_DB_NAME)
    ats_converts = set()
    for row in rows:
        cid = _get_notion_field(row, "Candidate ID", "title")
        rec = _get_notion_field(row, "Recommendation", "select")
        if rec.lower() == "convert":
            ats_converts.add(cid)

    return json_converts == ats_converts and len(json_converts) == 3


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_summary_json_exists", "checker": _s0_summary_json_exists, "weight": 1.0},
        {"id": "S0_recommendation_enum", "checker": _s0_recommendation_enum, "weight": 1.0},
        {"id": "S0_ranking_complete", "checker": _s0_ranking_complete, "weight": 1.0},
        {"id": "S0_c_conflict_detected", "checker": _s0_c_conflict_detected, "weight": 2.0},
        {"id": "S0_e_not_top", "checker": _s0_e_not_top, "weight": 1.5},
        {"id": "S0_ats_written", "checker": _s0_ats_written, "weight": 1.0},
        {"id": "S0_hrbp_email", "checker": _s0_hrbp_email, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_top3_count", "checker": _s1_top3_count, "weight": 1.0},
        {"id": "S1_keep_set", "checker": _s1_keep_set, "weight": 2.0},
        {"id": "S1_ranking_order", "checker": _s1_ranking_order, "weight": 1.5},
        {"id": "S1_d_hidden_support", "checker": _s1_d_hidden_support, "weight": 2.0},
        {"id": "S1_b_priority", "checker": _s1_b_priority, "weight": 2.0},
        {"id": "S1_drop_reasons", "checker": _s1_drop_reasons, "weight": 1.5},
        {"id": "S1_ats_final", "checker": _s1_ats_final, "weight": 1.0},
    ],
    "final": [
        {"id": "S1_hrbp_email", "checker": _s1_hrbp_email, "weight": 1.0},
        {"id": "S1_e_not_converted", "checker": _s1_e_not_converted, "weight": 2.0},
        {"id": "S1_c_not_converted", "checker": _s1_c_not_converted, "weight": 2.0},
        {"id": "S1_ats_json_consistent", "checker": _s1_ats_json_consistent, "weight": 1.5},
    ],
}
