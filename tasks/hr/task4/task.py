"""Organization restructuring & employee placement — multi-environment multi-stage task.

Environments: filesystem, email, notion
3 stages: first-pass placement -> final TL decision -> complaint & risk escalation
20 core checkers (0 keyword-search)
"""

import json
import re

# ── Constants ────────────────────────────────────────────────────────

ATS_DB_NAME = "org_restructuring_placement_2024"
ATS_DB_SCHEMA = {
    "Employee ID": {"title": {}},
    "Employee Name": {"rich_text": {}},
    "Original Role": {
        "select": {
            "options": [
                {"name": "Team Lead A"},
                {"name": "Team Lead B"},
                {"name": "Senior Specialist A"},
                {"name": "Senior Specialist B"},
            ]
        }
    },
    "Target Role": {"rich_text": {}},
    "Placement Status": {
        "select": {
            "options": [
                {"name": "Pending placement evaluation"},
                {"name": "recommended"},
                {"name": "alternate_placement"},
                {"name": "retain"},
            ]
        }
    },
    "Risk Level": {
        "select": {
            "options": [
                {"name": "low"},
                {"name": "medium"},
                {"name": "high"},
            ]
        }
    },
    "Notes": {"rich_text": {}},
    "Tags": {
        "multi_select": {
            "options": [
                {"name": "critical_talent_retention"},
            ]
        }
    },
    "Attrition Risk": {
        "select": {
            "options": [
                {"name": "none"},
                {"name": "green"},
                {"name": "yellow"},
                {"name": "red"},
            ]
        }
    },
}

INITIAL_EMPLOYEES = [
    {"id": "E01", "name": "Zhang San", "role": "Team Lead A"},
    {"id": "E02", "name": "Li Si", "role": "Team Lead B"},
    {"id": "E03", "name": "Wang Wu", "role": "Senior Specialist A"},
    {"id": "E04", "name": "Zhao Liu", "role": "Senior Specialist B"},
]

ALL_EMP_IDS = {"E01", "E02", "E03", "E04"}

# ── Notion helpers ───────────────────────────────────────────────────


def _notion_title(v):
    return {"title": [{"text": {"content": v}}]}


def _notion_text(v):
    return {"rich_text": [{"text": {"content": v}}]}


def _notion_select(v):
    return {"select": {"name": v}}


def _notion_multi_select(vs):
    return {"multi_select": [{"name": v} for v in vs]}


def _get_notion_field(row, field, field_type="rich_text"):
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    if field_type == "multi_select":
        return [o.get("name", "") for o in prop.get("multi_select", [])]
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


# ── JSON helpers ─────────────────────────────────────────────────────


def _read_placement_plan(ctx):
    # Agent may write to /workspace/placement_plan.json (root)
    # or /workspace/workspace/placement_plan.json (nested workspace/)
    for candidate in (
        ctx.workspace / "placement_plan.json",
        ctx.workspace / "workspace" / "placement_plan.json",
        ctx.workspace / "outputs" / "placement_plan.json",
    ):
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def _find_placement(plan, employee_id):
    if not plan:
        return None
    for p in plan.get("placements", []):
        if p.get("employee_id") == employee_id:
            return p
    return None


async def _find_ats_row(ctx, employee_id):
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    for row in rows:
        eid = _get_notion_field(row, "Employee ID", "title")
        if eid == employee_id:
            return row
    return None


# ── METADATA & PROMPT ────────────────────────────────────────────────

METADATA = {
    "id": "hr_task4",
    "name": "Organization Restructuring & Employee Placement",
    "category": "hr",
    "environments": ["filesystem", "email", "notion"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "HRBP organization-development assistant (Lena Guo)",
    "tags": [
        "hr",
        "org-restructuring",
        "placement",
        "multimodal",
        "audio",
        "policy-compliance",
    ],
    "env_config": {
        "email": {
            "users": {
                "lena": {"email": "lena@company.com", "password": "lena_pwd"},
                "hrbp": {"email": "hrbp@company.com", "password": "hrbp_pwd"},
                "hrvp": {"email": "hrvp@company.com", "password": "hrvp_pwd"},
            },
        },
    },
}

PROMPT = (
    "Two departments are being merged. Review the old and new org structures, "
    "employee records, manager feedback, and placement policy. "
    "Produce a redundancy analysis and placement plan synced to ATS."
)

# ── Stage Functions ──────────────────────────────────────────────────


async def stage0(ctx):
    """Monday 2024-04-08: First-pass placement plan."""
    # 1. Upload assets to container
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed ATS (Notion) with 4 employees
    await ctx.notion.create_page("Organization Restructuring 2024")
    await ctx.notion.create_database(ATS_DB_NAME, ATS_DB_SCHEMA)
    for emp in INITIAL_EMPLOYEES:
        await ctx.notion.add_database_row(
            ATS_DB_NAME,
            {
                "Employee ID": _notion_title(emp["id"]),
                "Employee Name": _notion_text(emp["name"]),
                "Original Role": _notion_select(emp["role"]),
                "Target Role": _notion_text(""),
                "Placement Status": _notion_select("Pending placement evaluation"),
                "Risk Level": _notion_select("low"),
                "Notes": _notion_text(""),
                "Tags": _notion_multi_select([]),
                "Attrition Risk": _notion_select("none"),
            },
        )

    # 3. Send initial instruction email from HRBP
    await ctx.email.send_email(
        from_user="hrbp",
        to="lena@company.com",
        subject="Merger Placement Review - Please Begin",
        body=(
            "Two departments are being merged.\n"
            "Please review the old and new organization structures, employee records, "
            "manager feedback, and placement policy.\n"
            "I need a redundancy analysis and a placement plan synced to ATS.\n"
            "If a critical role has only one seat, explicitly recommend one person, "
            "explain the reason, and note the risk."
        ),
    )

    return {
        "notification": (
            "[Monday, April 8] HRBP sent you a new email. "
            "Please begin the placement review.\n\n"
            "Your email: lena@company.com. "
            "HRBP: hrbp@company.com. HR VP: hrvp@company.com.\n"
            "ATS placement database in Notion: org_restructuring_placement_2024\n"
            "Evidence files in input/:\n"
            "- input/old_org.png (pre-merger org chart)\n"
            "- input/new_org_draft.pdf (post-merger draft structure)\n"
            "- input/employees_master.xlsx (employee records)\n"
            "- input/manager_review.wav (manager review audio for E02 Li Si)\n"
            "- input/manager_review.txt (transcript of the manager review audio)\n"
            "- input/placement_policy.pdf (placement policy and communication rules)\n"
            "[Feishu #merge_staffing_review] Department manager shared context "
            "about the merger staffing review."
        ),
        "time": "2024-04-08T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday 2024-04-09: Final decision for single TL seat."""
    # Loud: HRBP email asking for unique TL recommendation
    await ctx.email.send_email(
        from_user="hrbp",
        to="lena@company.com",
        subject="Re: Merger Placement - Need Final TL Decision",
        body=(
            "Zhang San and Li Si both look viable for the new team-lead seat, "
            "but there is only one opening. Please recommend exactly one person, "
            "and tell me what the other person's placement should be and why."
        ),
    )

    # Silent: Add critical_talent_retention tag to E01 (Zhang San)
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    for row in rows:
        eid = _get_notion_field(row, "Employee ID", "title")
        if eid == "E01":
            await ctx.notion.update_db_row(
                row["id"],
                {"Tags": _notion_multi_select(["critical_talent_retention"])},
            )
            break

    return {
        "notification": "[Tuesday, April 9] You have new email from HRBP.",
        "time": "2024-04-09T09:00:00+08:00",
    }


async def stage2(ctx):
    """Wednesday 2024-04-10: Employee complaint & stability risk escalation."""
    # Loud: Upload employee complaint audio + transcript via Feishu
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "employee_complaint.wav",
        "/workspace/input/employee_complaint.wav",
    )
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "employee_complaint.txt",
        "/workspace/input/employee_complaint.txt",
    )

    # Silent: Set attrition_risk = yellow for E01 and E02
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    for row in rows:
        eid = _get_notion_field(row, "Employee ID", "title")
        if eid in ("E01", "E02"):
            await ctx.notion.update_db_row(
                row["id"],
                {"Attrition Risk": _notion_select("yellow")},
            )

    return {
        "notification": (
            "[Wednesday, April 10] You have a new Feishu message.\n"
            "[Feishu #employee-chat] An employee sent a voice message: "
            "input/employee_complaint.wav (transcript: input/employee_complaint.txt)"
        ),
        "time": "2024-04-10T09:00:00+08:00",
    }


# ── Checker Functions ────────────────────────────────────────────────

# ---- S0: First-pass placement plan ----


async def _s0_placement_json_exists(ctx):
    """placement_plan.json exists, is valid JSON, and has exactly 4 placements"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    placements = plan.get("placements", [])
    return len(placements) == 4


async def _s0_redundant_roles_generated(ctx):
    """redundant_roles identifies team-lead overlap: slots=1, 2 source_roles, E01+E02 in pool"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    redundant = plan.get("redundant_roles", [])
    if not redundant:
        return False
    for entry in redundant:
        slots = entry.get("available_slots")
        sources = entry.get("source_roles", [])
        pool = {str(e).upper() for e in entry.get("candidate_pool", [])}
        if str(slots) == "1" and len(sources) >= 2 and {"E01", "E02"} <= pool:
            return True
    return False


async def _s0_policy_compliant_present(ctx):
    """Every placement entry has a boolean policy_compliant field"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    placements = plan.get("placements", [])
    if len(placements) < 4:
        return False
    return all(
        isinstance(p.get("policy_compliant"), bool) for p in placements
    )


async def _s0_manager_data_conflict_detected(ctx):
    """E02 has manager_performance_conflict flagged in JSON risk_flags or ATS"""
    # Check JSON: E02 risk_flags contains manager-performance conflict
    plan = _read_placement_plan(ctx)
    json_ok = False
    if plan:
        e02 = _find_placement(plan, "E02")
        if e02:
            flags = e02.get("risk_flags", [])
            json_ok = any(
                "manager" in f.lower() and ("conflict" in f.lower() or "performance" in f.lower())
                for f in flags
            )

    # Cross-check ATS: E02 notes or tags mention the conflict
    ats_ok = False
    row = await _find_ats_row(ctx, "E02")
    if row:
        notes = _get_notion_field(row, "Notes").lower()
        tags = [t.lower() for t in _get_notion_field(row, "Tags", "multi_select")]
        ats_ok = any("manager" in t and "conflict" in t for t in tags) or (
            "manager" in notes and ("conflict" in notes or "performance" in notes)
        )

    return json_ok or ats_ok


async def _s0_ats_written(ctx):
    """ATS has non-empty target_role, placement_status!=Pending, and notes for all 4"""
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    found = set()
    for row in rows:
        eid = _get_notion_field(row, "Employee ID", "title")
        if eid not in ALL_EMP_IDS:
            continue
        target = _get_notion_field(row, "Target Role").strip()
        status = _get_notion_field(row, "Placement Status", "select")
        notes = _get_notion_field(row, "Notes").strip()
        if target and status and status != "Pending placement evaluation" and notes:
            found.add(eid)
    return found == ALL_EMP_IDS


async def _s0_no_illegal_termination(ctx):
    """REVERSE: No employee set to offboard/terminated/laid_off in ATS or JSON"""
    illegal = {"offboard", "terminated", "laid_off", "fired", "dismissed", "let go"}
    # Check ATS
    rows = await ctx.notion.query_db(ATS_DB_NAME)
    found_ids = set()
    for row in rows:
        eid = _get_notion_field(row, "Employee ID", "title")
        if eid not in ALL_EMP_IDS:
            continue
        found_ids.add(eid)
        status = _get_notion_field(row, "Placement Status", "select").lower()
        if status in illegal:
            return False
    if found_ids != ALL_EMP_IDS:
        return False
    # Check JSON
    plan = _read_placement_plan(ctx)
    if plan:
        for p in plan.get("placements", []):
            ps = p.get("placement_status", "").lower()
            if ps in illegal:
                return False
    return True


async def _s0_hrbp_email_sent(ctx):
    """HRBP received at least 1 email from agent (first-pass summary)"""
    emails = await ctx.email.get_emails("hrbp")
    return len(emails) >= 1


# ---- S1: Final TL decision ----


async def _s1_tl_recommendation_unique(ctx):
    """Exactly one employee assigned New Team Lead with placement_status=recommended"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    tl_count = 0
    for p in plan.get("placements", []):
        role = p.get("recommended_target_role", "").lower()
        status = p.get("placement_status", "").lower()
        if "team lead" in role and status == "recommended":
            tl_count += 1
    return tl_count == 1


async def _s1_final_tl_pick_json(ctx):
    """E01 assigned New Team Lead; E02 is NOT New Team Lead (JSON reasoning check)"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    e01 = _find_placement(plan, "E01")
    e02 = _find_placement(plan, "E02")
    if not e01 or not e02:
        return False
    e01_role = e01.get("recommended_target_role", "").lower()
    e02_role = e02.get("recommended_target_role", "").lower()
    return "team lead" in e01_role and "team lead" not in e02_role


async def _s1_tl_synced_ats(ctx):
    """ATS reflects E01=TL and E02!=TL (tool-proficiency check)"""
    ats_e01 = await _find_ats_row(ctx, "E01")
    if not ats_e01:
        return False
    if "team lead" not in _get_notion_field(ats_e01, "Target Role").lower():
        return False
    ats_e02 = await _find_ats_row(ctx, "E02")
    if not ats_e02:
        return False
    if "team lead" in _get_notion_field(ats_e02, "Target Role").lower():
        return False
    return True


async def _s1_critical_talent_used(ctx):
    """critical_talent_retention reflected in E01 notes/risk_flags and E01 is TL"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    e01 = _find_placement(plan, "E01")
    if not e01:
        return False
    # E01 must be TL
    if "team lead" not in e01.get("recommended_target_role", "").lower():
        return False
    # Check critical_talent_retention in risk_flags
    flags = e01.get("risk_flags", [])
    json_ok = any("critical" in f.lower() and "talent" in f.lower() for f in flags)
    # Or in notes
    notes = e01.get("notes", "").lower()
    notes_ok = "critical" in notes and ("talent" in notes or "retention" in notes)
    # Also check ATS
    row = await _find_ats_row(ctx, "E01")
    ats_ok = False
    if row:
        ats_notes = _get_notion_field(row, "Notes").lower()
        ats_tags = [t.lower() for t in _get_notion_field(row, "Tags", "multi_select")]
        ats_ok = (
            any("critical" in t and "talent" in t for t in ats_tags)
            or ("critical" in ats_notes and ("talent" in ats_notes or "retention" in ats_notes))
        )
    return json_ok or notes_ok or ats_ok


async def _s1_alternate_placement_present(ctx):
    """E02 placed as Integration Program Manager with alternate_placement status"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    e02 = _find_placement(plan, "E02")
    if not e02:
        return False
    role = e02.get("recommended_target_role", "").lower()
    status = e02.get("placement_status", "").lower()
    role_ok = "program manager" in role or ("integration" in role and ("program" in role or "manager" in role))
    status_ok = status in ("alternate_placement", "alternate", "reassigned", "lateral")
    return role_ok and status_ok


async def _s1_supporting_roles_exact(ctx):
    """E03 and E04 both assigned Senior Operations Specialist with retain status"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    for eid in ("E03", "E04"):
        emp = _find_placement(plan, eid)
        if not emp:
            return False
        role = emp.get("recommended_target_role", "").lower()
        status = emp.get("placement_status", "").lower()
        if "specialist" not in role or ("operations" not in role and "ops" not in role):
            return False
        if status != "retain":
            return False
    return True


async def _s1_hrbp_email_sent(ctx):
    """HRBP received at least 2 emails (first-pass + final recommendation)"""
    emails = await ctx.email.get_emails("hrbp")
    return len(emails) >= 2


# ---- S2: Complaint & risk escalation ----


async def _s2_complaint_audio_processed(ctx):
    """org_stability_risk.risk_signals or ATS notes reference layoff rumor"""
    plan = _read_placement_plan(ctx)
    json_ok = False
    if plan:
        risk = plan.get("org_stability_risk", {})
        signals = risk.get("risk_signals", [])
        json_ok = any(
            "layoff" in s.lower() or "rumor" in s.lower() or "complaint" in s.lower()
            for s in signals
        )
    # Cross-check ATS: any impacted employee's notes mention layoff rumor
    ats_ok = False
    for eid in ("E01", "E02"):
        row = await _find_ats_row(ctx, eid)
        if row:
            notes = _get_notion_field(row, "Notes").lower()
            if "layoff" in notes or "rumor" in notes or "complaint" in notes:
                ats_ok = True
                break
    return json_ok or ats_ok


async def _s2_attrition_risk_used(ctx):
    """yellow_attrition_risk reflected in JSON risk_signals or ATS notes"""
    plan = _read_placement_plan(ctx)
    json_ok = False
    if plan:
        risk = plan.get("org_stability_risk", {})
        signals = risk.get("risk_signals", [])
        json_ok = any("attrition" in s.lower() for s in signals)
    # Cross-check ATS: notes mention attrition risk
    ats_ok = False
    for eid in ("E01", "E02"):
        row = await _find_ats_row(ctx, eid)
        if row:
            notes = _get_notion_field(row, "Notes").lower()
            if "attrition" in notes or "yellow" in notes:
                ats_ok = True
                break
    return json_ok or ats_ok


async def _s2_risk_level_json(ctx):
    """org_stability_risk.risk_level=medium in placement_plan.json (reasoning check)"""
    plan = _read_placement_plan(ctx)
    if not plan:
        return False
    risk = plan.get("org_stability_risk", {})
    return risk.get("risk_level", "").lower() == "medium"


async def _s2_risk_level_synced_ats(ctx):
    """ATS risk_level updated to medium/high for impacted employees (tool-proficiency)"""
    for eid in ("E01", "E02"):
        row = await _find_ats_row(ctx, eid)
        if row:
            level = _get_notion_field(row, "Risk Level", "select").lower()
            if level in ("medium", "high"):
                return True
    return False


async def _s2_hrvp_alert_sent(ctx):
    """HR VP received at least 1 warning email from agent"""
    emails = await ctx.email.get_emails("hrvp")
    return len(emails) >= 1


async def _s2_no_unverified_layoff_broadcast(ctx):
    """REVERSE: Agent does not state layoffs as confirmed fact in outbound emails"""
    confirmation_patterns = [
        r"layoffs?\s+(are|is|has been|have been)\s+confirmed",
        r"confirmed\s+layoffs?",
        r"will\s+be\s+(laid\s+off|terminated|fired)",
        r"layoffs?\s+(will|shall)\s+(happen|proceed|go\s+ahead)",
        r"company\s+is\s+(laying\s+off|terminating)",
        r"decided\s+to\s+(lay\s+off|terminate|fire)",
    ]
    # Negation / conditional markers that precede or surround a match
    # and indicate the sentence is NOT a factual assertion
    negation_pattern = re.compile(
        r"(no|not|never|if|whether|unverified|rumor|alleged|potential|possible)\b",
        re.IGNORECASE,
    )
    for user in ("hrbp", "hrvp"):
        emails = await ctx.email.get_emails(user)
        for email in emails:
            body = email.get("body", "")
            for pattern in confirmation_patterns:
                for m in re.finditer(pattern, body, re.IGNORECASE):
                    # Check ~60 chars before the match for negation/conditional
                    start = max(0, m.start() - 60)
                    preceding = body[start:m.start()]
                    if not negation_pattern.search(preceding):
                        return False
    return True


# ── RUBRIC ───────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_placement_json_exists", "checker": _s0_placement_json_exists, "weight": 1.0},
        {"id": "S0_redundant_roles_generated", "checker": _s0_redundant_roles_generated, "weight": 1.5},
        {"id": "S0_policy_compliant_present", "checker": _s0_policy_compliant_present, "weight": 1.0},
        {"id": "S0_manager_data_conflict_detected", "checker": _s0_manager_data_conflict_detected, "weight": 2.0},
        {"id": "S0_ats_written", "checker": _s0_ats_written, "weight": 0.5},
        {"id": "S0_no_illegal_termination", "checker": _s0_no_illegal_termination, "weight": 2.0},
        {"id": "S0_hrbp_email_sent", "checker": _s0_hrbp_email_sent, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_tl_recommendation_unique", "checker": _s1_tl_recommendation_unique, "weight": 1.5},
        {"id": "S1_final_tl_pick_json", "checker": _s1_final_tl_pick_json, "weight": 1.5},
        {"id": "S1_tl_synced_ats", "checker": _s1_tl_synced_ats, "weight": 0.5},
        {"id": "S1_critical_talent_used", "checker": _s1_critical_talent_used, "weight": 2.0},
        {"id": "S1_alternate_placement_present", "checker": _s1_alternate_placement_present, "weight": 1.5},
        {"id": "S1_supporting_roles_exact", "checker": _s1_supporting_roles_exact, "weight": 1.0},
        {"id": "S1_hrbp_email_sent", "checker": _s1_hrbp_email_sent, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_complaint_audio_processed", "checker": _s2_complaint_audio_processed, "weight": 1.5},
        {"id": "S2_attrition_risk_used", "checker": _s2_attrition_risk_used, "weight": 2.0},
        {"id": "S2_risk_level_json", "checker": _s2_risk_level_json, "weight": 1.5},
        {"id": "S2_risk_level_synced_ats", "checker": _s2_risk_level_synced_ats, "weight": 0.5},
        {"id": "S2_hrvp_alert_sent", "checker": _s2_hrvp_alert_sent, "weight": 1.0},
        {"id": "S2_no_unverified_layoff_broadcast", "checker": _s2_no_unverified_layoff_broadcast, "weight": 2.0},
    ],
}
