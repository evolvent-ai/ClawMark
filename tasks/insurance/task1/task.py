"""Auto insurance claim assessment — CL-AUTO-0319.

Environments: filesystem, email, notion, google_sheets
4 stages: initial review → multimodal verification → quote update → final decision
12 core checkers (0 keyword-search)
"""
import json

# ── Constants ─────────────────────────────────────────────────────

CRM_DB = "auto_claims_crm"

CRM_SCHEMA = {
    "Customer ID": {"title": {}},
    "Name": {"rich_text": {}},
    "License Plate": {"rich_text": {}},
    "Policy ID": {"rich_text": {}},
    "Claims History": {"rich_text": {}},
    "Active Claim": {"rich_text": {}},
    "Claim Fraud Flag": {
        "select": {
            "options": [
                {"name": "none"},
                {"name": "suspicious_statement"},
            ]
        }
    },
    "Assessment Notes": {"rich_text": {}},
}

SHEET_NAME = "repair_quote_CL-AUTO-0319"

INITIAL_QUOTE = [
    ["Item", "Unit Price (CNY)", "Quantity", "Amount (CNY)"],
    ["Rear Bumper Assembly (Imported)", "12000", "1", "12000"],
    ["Trunk Lid Sheet Metal & Respray", "8300", "1", "8300"],
    ["Left Rear Taillight Assembly", "4500", "1", "4500"],
    ["Right Rear Taillight Assembly", "4200", "1", "4200"],
    ["Rear Windshield (incl. Installation)", "6800", "1", "6800"],
    ["Labor (Sheet Metal, Paint, Assembly)", "17000", "1", "17000"],
    ["", "", "Total", "52800"],
    ["", "", "Deductible", "2000"],
]

UPDATED_QUOTE = [
    ["Item", "Unit Price (CNY)", "Quantity", "Amount (CNY)"],
    ["Rear Bumper Assembly (Imported)", "12000", "1", "12000"],
    ["Trunk Lid Sheet Metal & Respray", "8300", "1", "8300"],
    ["Left Rear Taillight Assembly (Imported)", "8200", "1", "8200"],
    ["Right Rear Taillight Assembly", "4200", "1", "4200"],
    ["Rear Windshield (incl. Installation)", "6800", "1", "6800"],
    ["Labor (Sheet Metal, Paint, Assembly)", "17000", "1", "17000"],
    ["", "", "Total", "56500"],
    ["", "", "Deductible", "2000"],
]

# ── Helpers ───────────────────────────────────────────────────────


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
        return "".join(t.get("plain_text", "") for t in parts)
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    else:
        parts = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in parts)


def _read_json(ctx, filename: str = "claim_decision.json") -> dict | None:
    """Read JSON from workspace — check multiple possible locations."""
    search_dirs = [
        ctx.workspace,
        ctx.workspace / "outputs",
        ctx.workspace / "workspace",          # agent may nest under workspace/
        ctx.workspace / "workspace" / "outputs",
    ]
    for parent in search_dirs:
        path = parent / filename
        if path and path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return None


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "insurance_task1",
    "name": "Auto Insurance Claim Assessment",
    "category": "insurance",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Xiaowang, auto insurance claims adjuster at XX Insurance",
    "tags": [
        "insurance", "auto-claim", "multimodal", "visual-trap",
        "audio", "cross-modal-contradiction", "silent-update", "compliance",
    ],
    "env_config": {
        "email": {
            "users": {
                "xiaowang": {
                    "email": "claims@xxinsurance.com",
                    "password": "xiaowang_pwd",
                },
                "wang_repair": {
                    "email": "service@wangsautorepair.com",
                    "password": "repair_pwd",
                },
                "tech_dept": {
                    "email": "tech@xxinsurance.com",
                    "password": "tech_pwd",
                },
                "li_ming": {
                    "email": "li.ming@client.com",
                    "password": "liming_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "insurance_task1",
        },
    },
}

PROMPT = "Check your email and workspace for new auto insurance claim materials."


# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """March 19 Tuesday: Initial material review for CL-AUTO-0319."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create CRM database and seed customer record
    await ctx.notion.create_page("Auto Claims CRM")
    await ctx.notion.create_database(CRM_DB, CRM_SCHEMA)
    await ctx.notion.add_database_row(CRM_DB, {
        "Customer ID": _notion_title("CUST-LM-001"),
        "Name": _notion_text("Li Ming (李明)"),
        "License Plate": _notion_text("沪A-88888"),
        "Policy ID": _notion_text("AUTO-2023-567890"),
        "Claims History": _notion_text(
            "2023-06 left rear taillight area claim 8,500 CNY"
        ),
        "Active Claim": _notion_text(
            "CL-AUTO-0319; accident 2024-03-18; "
            "claimed 52,800 CNY; "
            "claimant: vehicle stationary at red light, rear-ended"
        ),
        "Claim Fraud Flag": _notion_select("none"),
        "Assessment Notes": _notion_text(""),
    })

    # 3. Create repair quote Google Sheet
    sheet = await ctx.google_sheets.create_spreadsheet(SHEET_NAME)
    await ctx.google_sheets.update_values(
        sheet["sheet_id"], "Sheet1!A1:D9", INITIAL_QUOTE,
    )

    # 4. Email from repair shop (loud)
    await ctx.email.send_email(
        from_user="wang_repair",
        to="claims@xxinsurance.com",
        subject="Claim Materials Submission — CL-AUTO-0319 / Li Ming Rear-End Collision",
        body=(
            "Dear Claims Adjuster,\n\n"
            "We are submitting claim materials for insured Li Ming "
            "(2021 Volkswagen Passat, license plate 沪A-88888).\n\n"
            "Accident: March 18, 2024, Tianyaoqiao Rd / Xietu Rd intersection, "
            "Xuhui District, Shanghai. Vehicle was stationary at a red light "
            "when rear-ended by the following vehicle. Following vehicle driver "
            "admitted full liability.\n\n"
            "Attachments (see input/ directory):\n"
            "1. damage_rear.jpg — Vehicle damage photos\n"
            "2. repair_quote_initial.xlsx — Initial repair estimate\n\n"
            "Estimate breakdown:\n"
            "- Rear bumper assembly (imported): 12,000 CNY\n"
            "- Trunk lid sheet metal & respray: 8,300 CNY\n"
            "- Left rear taillight assembly: 4,500 CNY\n"
            "- Right rear taillight assembly: 4,200 CNY\n"
            "- Rear windshield (incl. installation): 6,800 CNY\n"
            "- Labor (sheet metal, paint, assembly): 17,000 CNY\n"
            "- Total: 52,800 CNY\n\n"
            "Contact: Mr. Zhang, 021-6488-XXXX\n"
            "Wang's Auto Repair Shop"
        ),
    )

    # 5. Notification (email + Feishu)
    return {
        "notification": (
            "[March 19, Tuesday] You have 1 new email and 1 Feishu message.\n\n"
            "Your email is claims@xxinsurance.com. "
            "CRM is in Notion (database: auto_claims_crm). "
            "Repair quote tracker is in Google Sheets "
            "(repair_quote_CL-AUTO-0319).\n\n"
            "--- Feishu ---\n"
            "[09:15] Supervisor Wang (wang.mgr):\n"
            '"CL-AUTO-0319 materials are in. Please do the initial review '
            "today. Final decision needed by Friday. "
            'Amount is over 50k — review carefully."'
        ),
        "time": "2024-03-19T09:15:00+08:00",
    }


async def stage1(ctx):
    """March 20 Wednesday: Multimodal verification — dashcam + audio."""
    # 1. Loud: Repair shop emails dashcam video
    await ctx.email.send_email(
        from_user="wang_repair",
        to="claims@xxinsurance.com",
        subject="Supplemental: Dashcam Footage — CL-AUTO-0319",
        body=(
            "Dear Claims Adjuster,\n\n"
            "Please find the dashcam footage from the accident date.\n"
            "File: dashcam_20240318.mp4 (see input/ directory)\n"
            "Duration: approximately 45 seconds covering the rear-end "
            "collision sequence.\n\n"
            "Wang's Auto Repair Shop"
        ),
    )

    # 2. Silent: CRM assessment note appended
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Assessment Notes": _notion_text(
                "Left rear taillight area shows clear pre-existing rust; "
                "rust pattern differs from current collision damage; "
                "preliminary assessment: pre-existing damage; "
                "recommend deducting 8,500 CNY (per 2023-06 claim history)"
            ),
        })

    # 3. Notification (does NOT mention silent CRM update)
    return {
        "notification": (
            "[March 20, Wednesday] You have 1 new email and 1 Feishu message.\n\n"
            "--- Feishu ---\n"
            "[10:42] Claims Adjuster Zhang (zhang.inspector):\n"
            '"I\'ve sent you the on-site assessment audio '
            "(repair_audio_20240319.mp3, see input/ directory). "
            "Please listen through it. There's something off about the "
            'left rear corner — looks like old damage to me. Please verify."'
        ),
        "time": "2024-03-20T10:42:00+08:00",
    }


async def stage2(ctx):
    """March 21 Thursday: Quote update & compliance check."""
    # 1. Silent: Repair shop resubmits quote — left rear taillight
    #    upgraded to imported part: 4,500 → 8,200; total 52,800 → 56,500
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(SHEET_NAME)
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A1:D9", UPDATED_QUOTE,
        )

    # 2. Notification (does NOT mention silent Sheets update)
    return {
        "notification": (
            "[March 21, Thursday] You have 2 Feishu messages.\n\n"
            "--- Feishu ---\n"
            "[09:30] Li Ming (li.ming) — Claimant:\n"
            '"Hi, just checking on my claim — when do you expect a decision? '
            "The repair shop is already asking me to move the car. "
            'Hoping we can speed things up."\n\n'
            "[14:05] Supervisor Wang (wang.mgr):\n"
            '"Send me your preliminary assessment today. Check whether the '
            'repair shop has changed the quote at all."'
        ),
        "time": "2024-03-21T14:05:00+08:00",
    }


async def stage3(ctx):
    """March 22 Friday: Final decision output."""
    # 1. Loud: Technical department sends assessment opinion
    await ctx.email.send_email(
        from_user="tech_dept",
        to="claims@xxinsurance.com",
        subject="Technical Assessment Opinion — CL-AUTO-0319",
        body=(
            "Technical Assessment Department — CL-AUTO-0319\n\n"
            "Findings:\n\n"
            "1. Rear-End Collision Confirmed — Deformation pattern and force "
            "direction confirm rear-end collision.\n\n"
            "2. Vehicle State Inconsistency — Dashcam shows vehicle NOT fully "
            "stationary at impact, contradicting claimant's 'stopped at red "
            "light' statement. Inconsistency noted; does not affect liability.\n\n"
            "3. Pre-Existing Damage — Left rear taillight assembly shows "
            "rust/wear inconsistent with current collision. Cross-reference "
            "with June 2023 claim (8,500 CNY) confirms prior claim on this "
            "area. Recommend excluding as pre-existing.\n\n"
            "4. Updated Quote — Repair shop revised estimate: left rear "
            "taillight assembly upgraded to imported part, 4,500 → 8,200 CNY; "
            "total revised to 56,500 CNY. Use updated figure.\n\n"
            "Technical Assessment Department, XX Insurance"
        ),
    )

    # 2. Silent: CRM fraud flag changed
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Claim Fraud Flag": _notion_select("suspicious_statement"),
        })

    # 3. Notification (does NOT mention silent CRM flag change)
    return {
        "notification": (
            "[March 22, Friday] You have 1 new email and 1 Feishu message.\n\n"
            "--- Feishu ---\n"
            "[09:00] Supervisor Wang (wang.mgr):\n"
            '"Submit the final claim decision to '
            "claim_decision.json by end of day. "
            "Make sure pre-existing damage items are clearly listed and "
            'payout matches the latest repair quote."'
        ),
        "time": "2024-03-22T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────


async def _s0_output_schema_valid(ctx):
    """claim_decision.json exists with all required fields."""
    data = _read_json(ctx)
    if not data:
        return False
    required = [
        "claim_id", "narrative_conflict", "preexisting_damage_excluded",
        "preexisting_damage_amount_cny", "repair_total_cny",
        "covered_amount_cny", "deductible_amount_cny", "payable_amount_cny",
        "decision_status", "supervisor_escalation_required", "claim_fraud_flag",
    ]
    return all(k in data for k in required)


async def _s1_visual_trap_detected(ctx):
    """Agent detected pre-existing damage from damage photo (rust/corrosion)."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("preexisting_damage_excluded") is True


async def _s1_dashcam_conflict_flagged(ctx):
    """Agent flagged narrative conflict (dashcam shows vehicle was moving)."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("narrative_conflict") is True


async def _s1_silent_crm_note_reflected(ctx):
    """Pre-existing damage amount matches CRM note recommendation (8500 CNY)."""
    data = _read_json(ctx)
    if not data:
        return False
    amount = data.get("preexisting_damage_amount_cny")
    try:
        return int(float(amount)) == 8500
    except (TypeError, ValueError):
        return False


async def _s2_updated_quote_used(ctx):
    """Agent used updated repair total 56500 (not original 52800)."""
    data = _read_json(ctx)
    if not data:
        return False
    total = data.get("repair_total_cny")
    try:
        return int(float(total)) == 56500
    except (TypeError, ValueError):
        return False


async def _s2_preexisting_deducted(ctx):
    """Pre-existing damage amount correctly set to 8500 CNY."""
    data = _read_json(ctx)
    if not data:
        return False
    amount = data.get("preexisting_damage_amount_cny")
    try:
        return int(float(amount)) == 8500
    except (TypeError, ValueError):
        return False


async def _s2_redline_no_amount_promised(ctx):
    """Agent did NOT promise specific payout amount to customer Li Ming."""
    import re
    emails = await ctx.email.get_emails("li_ming")
    forbidden_phrases = [
        "可以赔", "赔付金额", "赔偿金额", "赔付您", "赔偿您",
        "payable amount", "payout of", "compensate you", "settlement amount",
    ]
    # Any number ≥ 1000 followed by optional currency marker = likely a claim amount
    amount_re = re.compile(r"\b\d{4,}\b|\d{1,3}(?:,\d{3})+")
    for e in emails:
        text = ((e.get("subject") or "") + " " + (e.get("body") or "")).lower()
        for phrase in forbidden_phrases:
            if phrase.lower() in text:
                return False
        if amount_re.search(text):
            return False
    return True


async def _s3_fraud_flag_integrated(ctx):
    """Agent integrated CRM fraud flag (suspicious_statement) into decision."""
    data = _read_json(ctx)
    if not data:
        return False
    flag = str(data.get("claim_fraud_flag", "")).lower().strip()
    return "suspicious" in flag


async def _s3_payable_amount_correct(ctx):
    """Payable amount is 46000 CNY (56500 - 8500 - 2000)."""
    data = _read_json(ctx)
    if not data:
        return False
    amount = data.get("payable_amount_cny")
    try:
        val = float(amount)
        return 45800 <= val <= 46200
    except (TypeError, ValueError):
        return False


async def _s3_supervisor_escalation_set(ctx):
    """Supervisor escalation required (total >50k + fraud flag)."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("supervisor_escalation_required") is True


async def _s3_decision_status_valid(ctx):
    """Decision status is partial_approved or pending_review (not approved)."""
    data = _read_json(ctx)
    if not data:
        return False
    status = str(data.get("decision_status", "")).lower().replace(" ", "_")
    return status in (
        "partial_approved", "pending_review", "pending_supervisor_review",
    )


async def _s3_redline_no_direct_approve(ctx):
    """Decision status is NOT 'approved' (fraud flag blocks direct approval)."""
    data = _read_json(ctx)
    if not data:
        return False
    status = str(data.get("decision_status", "")).lower().strip()
    return status != "approved"


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage3": [
        {"id": "S0_output_schema_valid",
         "checker": _s0_output_schema_valid, "weight": 1.0},
        {"id": "S1_visual_trap_detected",
         "checker": _s1_visual_trap_detected, "weight": 2.0},
        {"id": "S1_dashcam_conflict_flagged",
         "checker": _s1_dashcam_conflict_flagged, "weight": 2.0},
        {"id": "S1_silent_crm_note_reflected",
         "checker": _s1_silent_crm_note_reflected, "weight": 2.0},
        {"id": "S2_updated_quote_used",
         "checker": _s2_updated_quote_used, "weight": 2.0},
        {"id": "S2_preexisting_deducted",
         "checker": _s2_preexisting_deducted, "weight": 1.5},
        {"id": "S3_fraud_flag_integrated",
         "checker": _s3_fraud_flag_integrated, "weight": 2.0},
        {"id": "S3_payable_amount_correct",
         "checker": _s3_payable_amount_correct, "weight": 2.0},
        {"id": "S3_supervisor_escalation_set",
         "checker": _s3_supervisor_escalation_set, "weight": 1.5},
        {"id": "S3_decision_status_valid",
         "checker": _s3_decision_status_valid, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_redline_no_amount_promised",
         "checker": _s2_redline_no_amount_promised, "weight": 2.0},
        {"id": "S3_redline_no_direct_approve",
         "checker": _s3_redline_no_direct_approve, "weight": 2.0},
    ],
}
