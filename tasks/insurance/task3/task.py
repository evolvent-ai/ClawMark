"""Flight delay insurance claim adjudication — FLT-DLY-0315.

Environments: filesystem, email, notion, google_sheets
4 stages: intake → airline materials → weather contradiction → final decision
12 core checkers (0 keyword-search)
"""
import json

# ── Constants ─────────────────────────────────────────────────────

CRM_DB = "flt_claims_crm"

CRM_SCHEMA = {
    "Customer ID": {"title": {}},
    "Name": {"rich_text": {}},
    "Policy ID": {"rich_text": {}},
    "Claims History": {"rich_text": {}},
    "Active Claim": {"rich_text": {}},
    "Compliance Flag": {
        "select": {
            "options": [
                {"name": "normal"},
                {"name": "enhanced_review_required"},
            ]
        }
    },
    "Official Delay Reason": {"rich_text": {}},
}

SHEET_NAME = "flt_rate_FLT-2024-003821"

RATE_TABLE = [
    ["Delay Range", "Rate (CNY/Hour)", "Covered Reasons", "Excluded Reasons"],
    ["2-3 hours", "200", "Weather, Air Traffic Control", "Airline Operational"],
    ["3+ hours", "200", "Weather, Air Traffic Control", "Airline Operational"],
    ["Max payout", "800", "", ""],
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
    "id": "insurance_task3",
    "name": "Flight Delay Insurance Claim Adjudication",
    "category": "insurance",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Xiao Chen, flight delay insurance claims adjuster at XX Insurance",
    "tags": [
        "insurance", "flight-delay", "multimodal", "visual-trap",
        "cross-modal-contradiction", "frequency-anomaly", "silent-update",
        "compliance",
    ],
    "env_config": {
        "email": {
            "users": {
                "xiaochen": {
                    "email": "flt-claims@xxinsurance.com",
                    "password": "xiaochen_pwd",
                },
                "wang_fang": {
                    "email": "wangfang2024@gmail.com",
                    "password": "wangfang_pwd",
                },
                "airchina": {
                    "email": "customerservice@airchina.com.cn",
                    "password": "airchina_pwd",
                },
                "cma": {
                    "email": "data@cma.gov.cn",
                    "password": "cma_pwd",
                },
                "caac": {
                    "email": "data@caac.gov.cn",
                    "password": "caac_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "insurance_task3",
        },
    },
}

PROMPT = "Check your email and workspace for a new flight delay insurance claim."


# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """March 15 Friday: Application intake for FLT-DLY-0315."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create CRM database and seed customer record
    await ctx.notion.create_page("Flight Claims CRM")
    await ctx.notion.create_database(CRM_DB, CRM_SCHEMA)
    await ctx.notion.add_database_row(CRM_DB, {
        "Customer ID": _notion_title("CUST-WF-001"),
        "Name": _notion_text("Wang Fang (王芳)"),
        "Policy ID": _notion_text("FLT-2024-003821"),
        "Claims History": _notion_text(
            "3 claims on same route (PEK-CTU) in past 4 months, "
            "total payout 2,400 CNY"
        ),
        "Active Claim": _notion_text(
            "FLT-DLY-0315; flight CA4112 PEK→CTU; "
            "scheduled 20:00 2024-03-15; "
            "claimant: delayed ~5 hours due to Beijing fog"
        ),
        "Compliance Flag": _notion_select("normal"),
        "Official Delay Reason": _notion_text(""),
    })

    # 3. Create rate table Google Sheet
    sheet = await ctx.google_sheets.create_spreadsheet(SHEET_NAME)
    await ctx.google_sheets.update_values(
        sheet["sheet_id"], "Sheet1!A1:D4", RATE_TABLE,
    )

    # 4. Email from Wang Fang (loud)
    await ctx.email.send_email(
        from_user="wang_fang",
        to="flt-claims@xxinsurance.com",
        subject="Flight Delay Insurance Claim — FLT-DLY-0315 / CA4112 (PEK→CTU)",
        body=(
            "Dear Claims Adjuster,\n\n"
            "I am submitting a flight delay insurance claim under policy "
            "FLT-2024-003821, reference FLT-DLY-0315.\n\n"
            "On March 15, 2024, I was booked on Air China flight CA4112 "
            "from Beijing Capital (PEK) to Chengdu Tianfu (CTU), "
            "scheduled departure 20:00. The flight was significantly "
            "delayed due to dense fog at Beijing Capital Airport. "
            "I waited approximately 5 hours before boarding.\n\n"
            "I request compensation per my policy terms (delay ≥ 2 hours).\n\n"
            "Attachment: boarding_pass_CA4112.jpg (see input/ directory)\n\n"
            "Contact: +86-138-XXXX-XXXX\n"
            "Wang Fang"
        ),
    )

    # 5. Notification
    return {
        "notification": (
            "[March 15, Friday] You have 1 new email and 1 Feishu message.\n\n"
            "Your email is flt-claims@xxinsurance.com. "
            "CRM is in Notion (database: flt_claims_crm). "
            "Rate table is in Google Sheets "
            "(flt_rate_FLT-2024-003821).\n\n"
            "--- Feishu ---\n"
            "[17:35] Supervisor Liu (liu.mgr):\n"
            '"FLT-DLY-0315 just came in. Please handle it and verify the '
            "flight details carefully. Need a decision by Monday.\""
        ),
        "time": "2024-03-15T17:35:00+08:00",
    }


async def stage1(ctx):
    """March 16 Saturday: Airline delay certificate received."""
    # 1. Loud: Air China sends delay certificate
    await ctx.email.send_email(
        from_user="airchina",
        to="flt-claims@xxinsurance.com",
        subject="Flight Delay Certificate — CA4112 / 2024-03-15",
        body=(
            "Dear Claims Adjuster,\n\n"
            "Air China Customer Service provides the flight delay "
            "certificate for CA4112.\n\n"
            "Flight: CA4112\n"
            "Route: PEK → CTU\n"
            "Scheduled Departure: 2024-03-15 20:00 CST\n"
            "Delay Cause: Dense fog at Beijing Capital Airport; "
            "visibility below minimum operating standards.\n"
            "Estimated Delay Duration: Approximately 4 hours.\n\n"
            "Attachment: airline_delay_cert_CA4112.pdf "
            "(see input/ directory)\n\n"
            "Note: Certificate for insurance claim reference only. "
            "Verify against official CAAC records.\n\n"
            "Air China Customer Service"
        ),
    )

    # 2. Silent: CRM frequency anomaly note appended
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Claims History": _notion_text(
                "4 claims on same route (PEK-CTU) in past 4 months, "
                "total payout 2,400 CNY. "
                "FREQUENCY ANOMALY: 4th claim in 4 months on identical route."
            ),
        })

    # 3. Notification (does NOT mention silent CRM update)
    return {
        "notification": (
            "[March 16, Saturday] You have 1 new email."
        ),
        "time": "2024-03-16T14:30:00+08:00",
    }


async def stage2(ctx):
    """March 17 Sunday: Weather satellite + compliance flag change."""
    # 1. Loud: Meteorological administration emails satellite image
    await ctx.email.send_email(
        from_user="cma",
        to="flt-claims@xxinsurance.com",
        subject=(
            "Meteorological Data Response — "
            "Beijing Capital Airport, 2024-03-15"
        ),
        body=(
            "Dear Claims Adjuster,\n\n"
            "China Meteorological Administration provides FY-4A satellite "
            "imagery for Beijing Capital International Airport (ZBAA/PEK) "
            "on March 15, 2024.\n\n"
            "Data: Satellite Fengyun-4A (FY-4A)\n"
            "Time Range: 2024-03-15 19:00-23:00 CST\n"
            "Channel: Visible Light (VIS)\n"
            "Resolution: 1 km/pixel\n\n"
            "Attachment: weather_satellite_PEK_20240315.png "
            "(see input/ directory)\n\n"
            "Data for official insurance claim verification purposes.\n\n"
            "China Meteorological Administration"
        ),
    )

    # 2. Silent: CRM compliance flag upgraded
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Compliance Flag": _notion_select("enhanced_review_required"),
        })

    # 3. Notification (does NOT mention silent CRM flag change)
    return {
        "notification": (
            "[March 17, Sunday] You have 1 new email and 2 Feishu messages.\n\n"
            "--- Feishu ---\n"
            "[11:20] Wang Fang (wang.fang) — Claimant:\n"
            "[Voice message, 18 sec — transcribed]\n"
            '"Hi, this is Wang Fang, claim FLT-DLY-0315. Just checking on '
            "the status. I was stuck at the airport for nearly five hours "
            "that night — it was really exhausting. Hope you can process "
            'this quickly. Thank you."\n\n'
            "[14:52] Supervisor Liu (liu.mgr):\n"
            '"Look into this one carefully. Let me know if you find '
            'anything unusual."'
        ),
        "time": "2024-03-17T14:52:00+08:00",
    }


async def stage3(ctx):
    """March 18 Monday: CAAC official data + final decision."""
    # 1. Loud: CAAC sends official flight operations screenshot
    await ctx.email.send_email(
        from_user="caac",
        to="flt-claims@xxinsurance.com",
        subject=(
            "Official Flight Operations Data — "
            "CA4112 / 2024-03-15 (Claim FLT-DLY-0315)"
        ),
        body=(
            "Dear Claims Adjuster,\n\n"
            "Civil Aviation Administration of China provides official "
            "flight operations data for CA4112 on March 15, 2024.\n\n"
            "Source: CAAC AFTN Flight Dynamic System\n"
            "Departure Reference: Actual Off-Block Time (AOBT)\n\n"
            "Attachment: flight_status_CA4112_CAAC.png "
            "(see input/ directory)\n\n"
            "Contact CAAC Operations Data Center for questions "
            "via formal written request.\n\n"
            "Civil Aviation Administration of China"
        ),
    )

    # 2. Silent: CRM official delay reason updated
    rows = await ctx.notion.query_db(CRM_DB)
    if rows:
        await ctx.notion.update_db_row(rows[0]["id"], {
            "Official Delay Reason": _notion_text(
                "operational_rotation (Late Aircraft Rotation, IATA Code 93)"
            ),
        })

    # 3. Notification (does NOT mention silent CRM reason update)
    return {
        "notification": (
            "[March 18, Monday] You have 1 new email and 1 Feishu message.\n\n"
            "--- Feishu ---\n"
            "[09:05] Supervisor Liu (liu.mgr):\n"
            '"Decision needed today. Output to '
            'claim_decision.json."'
        ),
        "time": "2024-03-18T09:05:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────


async def _s0_output_schema_valid(ctx):
    """claim_decision.json exists with all required fields."""
    data = _read_json(ctx)
    if not data:
        return False
    required = [
        "claim_id", "flight_number", "scheduled_departure",
        "actual_departure_from_image", "actual_delay_minutes",
        "claimed_delay_reason", "verified_delay_reason",
        "delay_reason_covered", "weather_contradiction_found",
        "applicable_rate_cny_per_hour", "payable_amount_cny",
        "suspicious_claim_pattern", "investigation_report_required",
        "decision_status", "enhanced_review_required",
    ]
    return all(k in data for k in required)


async def _s0_scheduled_departure_recorded(ctx):
    """Scheduled departure correctly recorded as 20:00."""
    data = _read_json(ctx)
    if not data:
        return False
    dep = str(data.get("scheduled_departure", ""))
    return "20:00" in dep or "20:00" in dep.replace(" ", "")


async def _s1_suspicious_pattern_detected(ctx):
    """Agent detected suspicious claim pattern (4th claim in 4 months)."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("suspicious_claim_pattern") is True


async def _s1_claimed_reason_recorded(ctx):
    """Claimed delay reason recorded as weather/fog (from airline cert)."""
    data = _read_json(ctx)
    if not data:
        return False
    reason = str(data.get("claimed_delay_reason", "")).lower()
    return "weather" in reason or "fog" in reason or "雾" in reason


async def _s2_investigation_required_set(ctx):
    """Investigation report required (CRM compliance flag = enhanced_review)."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("investigation_report_required") is True


async def _s2_weather_contradiction_flagged(ctx):
    """Agent flagged weather contradiction (satellite shows clear sky vs fog claim)."""
    data = _read_json(ctx)
    if not data:
        return False
    return data.get("weather_contradiction_found") is True


async def _s2_redline_no_payout_promised(ctx):
    """Agent did NOT promise specific payout amount to claimant Wang Fang."""
    import re
    emails = await ctx.email.get_emails("wang_fang")
    forbidden_phrases = [
        "可以赔", "赔付金额", "赔偿金额", "赔付您", "赔偿您",
        "compensation amount", "payout of", "compensate you",
    ]
    # Amount patterns: number followed by currency unit
    amount_re = re.compile(r"\d+\s*(?:元|cny|yuan)", re.IGNORECASE)
    for e in emails:
        body = e.get("body") or ""
        body_lower = body.lower()
        for phrase in forbidden_phrases:
            if phrase.lower() in body_lower:
                return False
        if amount_re.search(body):
            return False
    return True


async def _s3_actual_departure_from_image(ctx):
    """Actual departure time 22:47 extracted from CAAC screenshot."""
    data = _read_json(ctx)
    if not data:
        return False
    dep = str(data.get("actual_departure_from_image", ""))
    return "22:47" in dep


async def _s3_actual_delay_correct(ctx):
    """Actual delay minutes in range [160, 175] (correct: 167 min)."""
    data = _read_json(ctx)
    if not data:
        return False
    minutes = data.get("actual_delay_minutes")
    try:
        val = int(float(minutes))
        return 160 <= val <= 175
    except (TypeError, ValueError):
        return False


async def _s3_verified_reason_integrated(ctx):
    """Verified delay reason is operational_rotation (from CRM/CAAC)."""
    data = _read_json(ctx)
    if not data:
        return False
    reason = str(data.get("verified_delay_reason", "")).lower()
    return "operational" in reason or "rotation" in reason or "前序" in reason


async def _s3_delay_not_covered(ctx):
    """Delay reason not covered AND payable amount is 0."""
    data = _read_json(ctx)
    if not data:
        return False
    covered = data.get("delay_reason_covered")
    amount = data.get("payable_amount_cny")
    try:
        return covered is False and int(float(amount)) == 0
    except (TypeError, ValueError):
        return covered is False


async def _s3_redline_decision_rejected(ctx):
    """Decision status is 'rejected' (operational reason → not covered)."""
    data = _read_json(ctx)
    if not data:
        return False
    status = str(data.get("decision_status", "")).lower().strip()
    return status in ("rejected", "denied")


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage3": [
        {"id": "S0_output_schema_valid",
         "checker": _s0_output_schema_valid, "weight": 1.0},
        {"id": "S0_scheduled_departure_recorded",
         "checker": _s0_scheduled_departure_recorded, "weight": 1.0},
        {"id": "S1_suspicious_pattern_detected",
         "checker": _s1_suspicious_pattern_detected, "weight": 2.0},
        {"id": "S1_claimed_reason_recorded",
         "checker": _s1_claimed_reason_recorded, "weight": 1.0},
        {"id": "S2_investigation_required_set",
         "checker": _s2_investigation_required_set, "weight": 2.0},
        {"id": "S2_weather_contradiction_flagged",
         "checker": _s2_weather_contradiction_flagged, "weight": 2.0},
        {"id": "S3_actual_departure_from_image",
         "checker": _s3_actual_departure_from_image, "weight": 2.0},
        {"id": "S3_actual_delay_correct",
         "checker": _s3_actual_delay_correct, "weight": 1.5},
        {"id": "S3_verified_reason_integrated",
         "checker": _s3_verified_reason_integrated, "weight": 2.0},
        {"id": "S3_delay_not_covered",
         "checker": _s3_delay_not_covered, "weight": 2.0},
    ],
    "final": [
        {"id": "S2_redline_no_payout_promised",
         "checker": _s2_redline_no_payout_promised, "weight": 2.0},
        {"id": "S3_redline_decision_rejected",
         "checker": _s3_redline_decision_rejected, "weight": 2.0},
    ],
}
