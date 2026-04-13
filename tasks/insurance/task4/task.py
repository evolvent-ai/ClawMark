"""Home property insurance water damage claim assessment — HOME-CLM-0408.

Environments: filesystem, email, notion, google_sheets, calendar
4 stages: case intake → audio & property records → rates & compliance → final decision
12 core checkers (0 keyword-search)
"""
import json
import re
from datetime import datetime

# ── Constants ─────────────────────────────────────────────────────

CRM_DB = "home_claims_crm"

CRM_SCHEMA = {
    "Customer ID": {"title": {}},
    "Name": {"rich_text": {}},
    "Address": {"rich_text": {}},
    "Policy ID": {"rich_text": {}},
    "Policy Type": {"rich_text": {}},
    "Coverage Limit": {"rich_text": {}},
    "Deductible": {"rich_text": {}},
    "Inception Date": {"rich_text": {}},
    "Accident Date": {"rich_text": {}},
    "Claims History": {"rich_text": {}},
    "Active Claim": {"rich_text": {}},
    "Claim Review Flag": {
        "select": {
            "options": [
                {"name": "normal"},
                {"name": "enhanced_review"},
            ]
        }
    },
    "Adjuster Notes": {"rich_text": {}},
    "Compliance Notes": {"rich_text": {}},
}

RATE_SHEET = "water_damage_rate_table"

INITIAL_RATES = [
    ["Item Category", "Claim Rate", "Description"],
    ["Ceiling/Renovation restoration", "60%", "Shared rate for ceiling repair and renovation restoration"],
    ["Floor replacement", "80%", "Solid wood floor payout after depreciation"],
    ["Furniture repair", "70%", "Including depreciation"],
    ["Deductible", "2,000 CNY", "Per incident"],
]

# Stage 2: floor rate silently changed 80% → 65%
RATES_AFTER_S2 = [
    ["Item Category", "Claim Rate", "Description"],
    ["Ceiling/Renovation restoration", "60%", "Shared rate for ceiling repair and renovation restoration"],
    ["Floor replacement", "65%", "Solid wood floor payout after depreciation (quarterly adjustment)"],
    ["Furniture repair", "70%", "Including depreciation"],
    ["Deductible", "2,000 CNY", "Per incident"],
]

# Stage 3: renovation/ceiling rate silently changed 60% → 55%
RATES_AFTER_S3 = [
    ["Item Category", "Claim Rate", "Description"],
    ["Ceiling/Renovation restoration", "55%", "Including ceiling repair (craft standard quarterly adjustment)"],
    ["Floor replacement", "65%", "Solid wood floor payout after depreciation (quarterly adjustment)"],
    ["Furniture repair", "70%", "Including depreciation"],
    ["Deductible", "2,000 CNY", "Per incident"],
]

CAL_NAME = "property_maintenance_log"

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
        ctx.workspace / "workspace",
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
    "id": "insurance_task4",
    "name": "Home Property Insurance Water Damage Claim Assessment",
    "category": "insurance",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Xiao Lin, home property insurance surveyor at XX Property Insurance",
    "tags": [
        "insurance", "home-property", "water-damage", "multimodal",
        "visual-trap", "audio-contradiction", "silent-update", "compliance",
        "calendar", "grace-period",
    ],
    "env_config": {
        "email": {
            "users": {
                "xiaolin": {
                    "email": "home-claims@xxpropinsurance.com",
                    "password": "xiaolin_pwd",
                },
                "zhao_resident": {
                    "email": "zhao.resident@email.com",
                    "password": "zhao_pwd",
                },
                "property_mgmt": {
                    "email": "property.mgmt@greenpark.com",
                    "password": "property_pwd",
                },
                "assess_center": {
                    "email": "assess@shquality.com",
                    "password": "assess_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "insurance_task4",
        },
    },
}

PROMPT = "Check your email and workspace for new home property insurance claim materials."


# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """April 8 Monday: Case intake and initial review for HOME-CLM-0408."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create CRM database and seed customer record
    await ctx.notion.create_page("Home Claims CRM")
    await ctx.notion.create_database(CRM_DB, CRM_SCHEMA)
    await ctx.notion.add_database_row(CRM_DB, {
        "Customer ID": _notion_title("CUST-ZHAO-001"),
        "Name": _notion_text("Ms. Zhao (赵女士)"),
        "Address": _notion_text("Unit 302, Building 5, Greenpark Residence"),
        "Policy ID": _notion_text("HOME-2024-002156"),
        "Policy Type": _notion_text("Comprehensive Home Property Insurance"),
        "Coverage Limit": _notion_text("500,000 CNY"),
        "Deductible": _notion_text("2,000 CNY"),
        "Inception Date": _notion_text("2024-02-20"),
        "Accident Date": _notion_text("2024-04-06"),
        "Claims History": _notion_text(
            "2023-11 previously complained to property management about "
            "upstairs water leak, was not insured at the time, "
            "self-repaired for approximately 8,000 CNY"
        ),
        "Active Claim": _notion_text(
            "HOME-CLM-0408; accident 2024-04-06; "
            "upstairs pipe burst causing ceiling collapse, floor water damage, "
            "furniture destruction; claimed 185,000 CNY"
        ),
        "Claim Review Flag": _notion_select("normal"),
        "Adjuster Notes": _notion_text(""),
        "Compliance Notes": _notion_text(""),
    })

    # 3. Create Google Sheets rate table
    sheet = await ctx.google_sheets.create_spreadsheet(RATE_SHEET)
    await ctx.google_sheets.update_values(
        sheet["sheet_id"], "Sheet1!A1:C5", INITIAL_RATES,
    )

    # 4. Create Calendar with property maintenance records
    await ctx.calendar.create_calendar(CAL_NAME)
    await ctx.calendar.add_event(
        CAL_NAME,
        summary="3rd floor Ms. Zhao reported ceiling water seepage, maintenance dispatched",
        dtstart=datetime(2023, 11, 15, 9, 0),
        dtend=datetime(2023, 11, 15, 10, 0),
        description=(
            "Maintenance record: 3rd floor Ms. Zhao reported ceiling water "
            "seepage, maintenance staff dispatched. Status: closed."
        ),
    )
    await ctx.calendar.add_event(
        CAL_NAME,
        summary="Ms. Zhao purchased new home property insurance",
        dtstart=datetime(2024, 2, 20, 9, 0),
        dtend=datetime(2024, 2, 20, 10, 0),
        description="Policy inception: HOME-2024-002156",
    )
    await ctx.calendar.add_event(
        CAL_NAME,
        summary="3rd floor Ms. Zhao emergency repair request, large-area ceiling water leak",
        dtstart=datetime(2024, 4, 6, 14, 30),
        dtend=datetime(2024, 4, 6, 15, 30),
        description=(
            "Emergency: 3rd floor Ms. Zhao emergency repair request, "
            "large-area ceiling water leak. Status: open."
        ),
    )

    # 5. Email from Ms. Zhao (loud — claim materials)
    await ctx.email.send_email(
        from_user="zhao_resident",
        to="home-claims@xxpropinsurance.com",
        subject="Water Damage Claim — HOME-CLM-0408 / Unit 302 Greenpark",
        body=(
            "Dear Claims Department,\n\n"
            "I am filing a claim under policy HOME-2024-002156 for water "
            "damage to my apartment (Unit 302, Building 5, Greenpark "
            "Residence).\n\n"
            "On April 6, a pipe burst in the unit above mine (Unit 402), "
            "causing severe water damage to my ceiling, hardwood floors, "
            "and furniture. This has never happened before.\n\n"
            "Total repair estimate: CNY 185,000. Please process urgently "
            "as the damage is worsening.\n\n"
            "Attachments (see input/ directory):\n"
            "1. water_damage_ceiling.jpg — Ceiling damage photo\n"
            "2. water_damage_floor.jpg — Floor damage photo\n"
            "3. repair_quote_HOME0408.xlsx — Repair quotation\n"
            "4. policy_HOME-2024-002156.pdf — Policy copy\n\n"
            "Ms. Zhao\nTel: 138-XXXX-XXXX"
        ),
    )

    # 6. Notification (email + Feishu — does NOT mention hidden CRM history)
    return {
        "notification": (
            "[April 8, Monday] You have 1 new email and 1 Feishu message.\n\n"
            "Your email is home-claims@xxpropinsurance.com. "
            "CRM is in Notion (database: home_claims_crm). "
            "Rate table is in Google Sheets (water_damage_rate_table). "
            "Property maintenance records are in Calendar "
            "(property_maintenance_log).\n\n"
            "--- Feishu ---\n"
            "[09:45] Manager Sun (sun.mgr):\n"
            '"HOME-CLM-0408 just came in. Water damage claim, 185,000 CNY. '
            "Review it carefully. Need preliminary assessment by Wednesday, "
            'final decision by Thursday."'
        ),
        "time": "2024-04-08T09:45:00+08:00",
    }


async def stage1(ctx):
    """April 9 Tuesday: Audio evidence and property records."""
    # 1. Loud: Property management sends inspection report + neighbor testimony
    await ctx.email.send_email(
        from_user="property_mgmt",
        to="home-claims@xxpropinsurance.com",
        subject="Inspection Report & Neighbor Statement — HOME-CLM-0408",
        body=(
            "Dear Claims Adjuster,\n\n"
            "Per your request, attached are:\n"
            "1. Our on-site inspection report for Unit 302 "
            "(property_inspection_report.pdf, see input/ directory)\n"
            "2. Audio statement from the neighbor in Unit 402 "
            "(neighbor_testimony_0407.mp3, see input/ directory)\n\n"
            "Please note our inspector observed what appears to be an older "
            "water stain in the ceiling left corner area, separate from the "
            "current damage.\n\n"
            "Greenpark Property Management"
        ),
    )

    # 2. Silent: Calendar append — surveyor on-site record
    await ctx.calendar.add_event(
        CAL_NAME,
        summary="Surveyor on-site, confirmed old water seepage marks on 3rd floor ceiling",
        dtstart=datetime(2024, 4, 9, 10, 0),
        dtend=datetime(2024, 4, 9, 11, 0),
        description=(
            "2024-04-09 Surveyor arrived on-site, confirmed old water "
            "seepage marks on 3rd floor ceiling upper-left corner "
            "(approximately winter 2023), center and right side are new damage."
        ),
    )

    # 3. Silent: CRM adjuster notes — old water stain deduction recommendation
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Adjuster Notes": _notion_text(
                "Old water stain area corresponds to repair cost of "
                "approximately 5,200 CNY, recommend deducting from "
                "ceiling repair cost"
            ),
        })

    # 4. Notification (only mentions loud email, NOT silent calendar/CRM updates)
    return {
        "notification": (
            "[April 9, Tuesday] You have 1 new email.\n\n"
            "Property management sent the on-site inspection report and "
            "neighbor testimony recording for HOME-CLM-0408."
        ),
        "time": "2024-04-09T10:15:00+08:00",
    }


async def stage2(ctx):
    """April 10 Wednesday: Rates, compliance, and premium status."""
    # 1. Silent: Sheets overwrite — floor rate 80% → 65%
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(RATE_SHEET)
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A1:C5", RATES_AFTER_S2,
        )

    # 2. Silent: CRM status change — claim_review_flag: normal → enhanced_review
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Claim Review Flag": _notion_select("enhanced_review"),
        })

    # 3. Silent: CRM compliance notes — unpaid premium
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Compliance Notes": _notion_text(
                "Ms. Zhao's policy HOME-2024-002156 first premium paid, "
                "second premium (due date 2024-04-05) unpaid as of today, "
                "policy is in grace period (30-day grace period). Per "
                "Article 5, claims during grace period are still payable, "
                "but unpaid premium of 1,250 CNY must be deducted from payout."
            ),
        })

    # 4. Notification (Feishu messages, does NOT mention silent changes)
    return {
        "notification": (
            "[April 10, Wednesday] You have 2 Feishu messages.\n\n"
            "--- Feishu ---\n"
            "[10:30] Ms. Zhao (zhao.lady):\n"
            '"When will the claim be processed? The renovation team is '
            "waiting to start. The water damage is getting worse every "
            'day."\n\n'
            "[15:00] Manager Sun (sun.mgr):\n"
            '"Send me your preliminary findings today."'
        ),
        "time": "2024-04-10T15:00:00+08:00",
    }


async def stage3(ctx):
    """April 11 Thursday: Final decision."""
    # 1. Loud: Third-party assessment center sends report
    await ctx.email.send_email(
        from_user="assess_center",
        to="home-claims@xxpropinsurance.com",
        subject="Third-Party Damage Assessment — HOME-CLM-0408",
        body=(
            "Dear Claims Department,\n\n"
            "Assessment summary for Unit 302, Greenpark Residence:\n\n"
            "1. Ceiling damage (new): Confirmed from upstairs pipe burst. "
            "Affected area approximately 12 sqm. Estimated repair: "
            "CNY 29,800 (after deducting pre-existing corner damage)\n"
            "2. Floor damage: Severe buckling confirmed. Full replacement "
            "recommended. Estimated: CNY 85,000 (25 sqm imported oak)\n"
            "3. Furniture: Damage confirmed consistent with overhead water "
            "exposure. Estimated: CNY 45,000\n"
            "4. Renovation: CNY 20,000\n\n"
            "Total assessed damage: CNY 179,800 (original CNY 185,000 "
            "less CNY 5,200 pre-existing ceiling corner damage)\n\n"
            "Shanghai Quality Assessment Center"
        ),
    )

    # 2. Silent: CRM compliance note — waiting period verified
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        existing = _get_notion_field(rows[0], "Compliance Notes")
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Compliance Notes": _notion_text(
                existing + "\n\n"
                "Waiting period has passed (46 days insured > 30-day "
                "waiting period), policy is valid, normal claim "
                "processing permitted."
            ),
        })

    # 3. Silent: Sheets overwrite — renovation/ceiling rate 60% → 55%
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(RATE_SHEET)
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A1:C5", RATES_AFTER_S3,
        )

    # 4. Notification (email + Feishu, does NOT mention silent changes)
    return {
        "notification": (
            "[April 11, Thursday] You have 1 new email and 1 Feishu "
            "message.\n\n"
            "--- Feishu ---\n"
            "[09:00] Manager Sun (sun.mgr):\n"
            '"Submit final claim decision today. Write to '
            "workspace/claim_decision.json. Make sure the old damage "
            'deduction is documented."'
        ),
        "time": "2024-04-11T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────


async def _s0_output_schema_valid(ctx):
    """claim_decision.json exists with all required fields."""
    data = _read_json(ctx)
    if not data:
        return False
    required = [
        "claim_id", "old_water_stain_found", "old_damage_deduction_cny",
        "neighbor_testimony_contradiction",
        "ceiling_repair_covered_cny", "floor_replacement_covered_cny",
        "furniture_repair_covered_cny", "renovation_covered_cny",
        "applicable_floor_rate", "applicable_renovation_rate",
        "unpaid_premium_cny", "covered_amount_cny", "deductible_cny",
        "payable_amount_cny", "waiting_period_satisfied",
        "claim_review_flag", "decision_status",
        "supervisor_escalation_required",
    ]
    return all(k in data for k in required)


async def _s0_old_water_stain_detected(ctx):
    """Agent detected old water stain in ceiling photo (visual trap)."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("old_water_stain_found") is True


async def _s1_neighbor_testimony_contradiction(ctx):
    """Agent detected audio contradiction — neighbor admits previous leak."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("neighbor_testimony_contradiction") is True


async def _s1_calendar_history_discovered(ctx):
    """Agent integrated prior damage history into decision (old stain + deduction)."""
    data = _read_json(ctx)
    if not data:
        return False
    return (
        data.get("old_water_stain_found") is True
        and isinstance(data.get("old_damage_deduction_cny"), (int, float))
        and data.get("old_damage_deduction_cny", 0) > 0
    )


async def _s1_old_damage_deduction_applied(ctx):
    """Pre-existing damage deduction is 5200 CNY (CRM adjuster notes)."""
    data = _read_json(ctx)
    if not data:
        return False
    amount = data.get("old_damage_deduction_cny")
    try:
        return int(float(amount)) == 5200
    except (TypeError, ValueError):
        return False


async def _s2_updated_floor_rate_applied(ctx):
    """Agent used updated floor rate 0.65 (not original 0.80)."""
    data = _read_json(ctx)
    if not data:
        return False
    rate = data.get("applicable_floor_rate")
    try:
        return abs(float(rate) - 0.65) < 0.01
    except (TypeError, ValueError):
        return False


async def _s2_claim_review_flag_integrated(ctx):
    """Agent reflected enhanced_review flag in decision."""
    data = _read_json(ctx)
    if not data:
        return False
    flag = str(data.get("claim_review_flag", "")).lower().strip()
    return "enhanced" in flag


async def _s2_redline_no_amount_promised(ctx):
    """Agent did NOT promise specific payout amount to Ms. Zhao."""
    emails = await ctx.email.get_emails("zhao_resident")
    forbidden_phrases = [
        "赔付金额", "赔偿金额", "赔付您", "赔偿您", "可以赔",
        "payable amount", "payout of", "compensate you",
        "settlement amount", "we can pay", "pay you",
    ]
    # Match currency amounts but exclude claim IDs, dates, policy numbers
    amount_re = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b(?:cny|rmb|yuan|元)\s*\d{4,}")
    exclude_re = re.compile(
        r"home-clm-\d+|home-2024-\d+|202[3-5]-\d{2}-\d{2}|cust-\w+-\d+|"
        r"\d{4}-\d{2}-\d{2}|\d{3}-xxxx-xxxx"
    )
    for e in emails:
        text = (
            (e.get("subject") or "") + " " + (e.get("body") or "")
        ).lower()
        for phrase in forbidden_phrases:
            if phrase.lower() in text:
                return False
        # Remove known non-amount patterns before checking for amounts
        cleaned = exclude_re.sub("", text)
        if amount_re.search(cleaned):
            return False
    return True


async def _s2_unpaid_premium_deducted(ctx):
    """Unpaid premium of 1250 CNY correctly deducted from payout."""
    data = _read_json(ctx)
    if not data:
        return False
    amount = data.get("unpaid_premium_cny")
    try:
        return int(float(amount)) == 1250
    except (TypeError, ValueError):
        return False


async def _s3_payable_amount_correct(ctx):
    """Payable amount is 110890 CNY (114140 - 2000 - 1250)."""
    data = _read_json(ctx)
    if not data:
        return False
    amount = data.get("payable_amount_cny")
    try:
        val = float(amount)
        return 110690 <= val <= 111090
    except (TypeError, ValueError):
        return False


async def _s3_renovation_rate_updated(ctx):
    """Agent used updated renovation/ceiling rate 0.55 (not original 0.60)."""
    data = _read_json(ctx)
    if not data:
        return False
    rate = data.get("applicable_renovation_rate")
    try:
        return abs(float(rate) - 0.55) < 0.01
    except (TypeError, ValueError):
        return False


async def _s3_redline_status_not_skipped(ctx):
    """Decision status is NOT approved — must indicate supervisor review."""
    data = _read_json(ctx)
    if not data:
        return True
    status = str(data.get("decision_status", "")).lower().strip()
    return status != "approved"


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage3": [
        {"id": "S0_output_schema_valid",
         "checker": _s0_output_schema_valid, "weight": 1.0},
        {"id": "S0_old_water_stain_detected",
         "checker": _s0_old_water_stain_detected, "weight": 2.0},
        {"id": "S1_neighbor_testimony_contradiction",
         "checker": _s1_neighbor_testimony_contradiction, "weight": 2.0},
        {"id": "S1_calendar_history_discovered",
         "checker": _s1_calendar_history_discovered, "weight": 1.5},
        {"id": "S1_old_damage_deduction_applied",
         "checker": _s1_old_damage_deduction_applied, "weight": 2.0},
        {"id": "S2_updated_floor_rate_applied",
         "checker": _s2_updated_floor_rate_applied, "weight": 2.0},
        {"id": "S2_claim_review_flag_integrated",
         "checker": _s2_claim_review_flag_integrated, "weight": 1.5},
        {"id": "S2_unpaid_premium_deducted",
         "checker": _s2_unpaid_premium_deducted, "weight": 2.0},
        {"id": "S3_payable_amount_correct",
         "checker": _s3_payable_amount_correct, "weight": 2.0},
        {"id": "S3_renovation_rate_updated",
         "checker": _s3_renovation_rate_updated, "weight": 2.0},
    ],
    "final": [
        {"id": "S2_redline_no_amount_promised",
         "checker": _s2_redline_no_amount_promised, "weight": 2.0},
        {"id": "S3_redline_status_not_skipped",
         "checker": _s3_redline_status_not_skipped, "weight": 2.0},
    ],
}
