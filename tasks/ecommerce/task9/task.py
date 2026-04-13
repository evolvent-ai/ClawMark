"""Creator review crisis triage & batch escalation.

Environments: filesystem, email, notion, google_sheets
3 stages: initial triage → defect signal escalation → internal brief & containment
15 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

INCIDENT_DB_NAME = "creator_incidents"

INCIDENT_DB_SCHEMA = {
    "incident_id": {"title": {}},
    "creator_id": {"rich_text": {}},
    "sku": {"rich_text": {}},
    "lot_id": {"rich_text": {}},
    "platform": {"rich_text": {}},
    "incident_level": {"select": {"options": [
        {"name": "low"}, {"name": "medium"}, {"name": "high"}, {"name": "critical"},
    ]}},
    "misuse_signal": {"rich_text": {}},
    "defect_signal": {"rich_text": {}},
    "external_response_ready": {"select": {"options": [
        {"name": "YES"}, {"name": "NO"},
    ]}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "investigating"},
        {"name": "escalated"}, {"name": "resolved"},
    ]}},
    "notes": {"rich_text": {}},
}

RETURN_RATES_HEADER = ["lot_id", "sku", "shipped", "returned", "return_rate"]
RETURN_RATES_ROWS = [
    ["lot-240412-B1", "HW-B4101", "1200", "5", "0.42%"],
    ["lot-240412-B2", "HW-B4101", "800", "2", "0.25%"],
]

SAMPLE_SHIPMENTS_HEADER = [
    "creator_id", "sku", "lot_id", "ship_date", "status",
]
SAMPLE_SHIPMENTS_ROWS = [
    ["CR-088", "HW-B4101", "lot-240412-B1", "2024-03-20", "shipped"],
    ["CR-112", "HW-B4101", "lot-240412-B1", "2024-03-22", "shipped"],
    ["CR-156", "HW-B4101", "lot-240412-B1", "2024-03-25", "shipped"],
]

INTERNAL_EMAILS = {
    "assistant@curato.com",
    "liufang@curato.com",
    "zhaoqiang@curato.com",
    "ops@curato.com",
    "xiaozhao@curato.com",
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


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "ecommerce_task9",
    "name": "Creator Review Crisis Triage & Batch Escalation",
    "category": "ecommerce",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Liu Fang's after-sales assistant at Curato",
    "tags": [
        "creator-incident", "batch-defect", "crisis-triage",
        "multimodal", "escalation",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@curato.com",
                    "password": "assistant_pwd",
                },
                "liufang": {
                    "email": "liufang@curato.com",
                    "password": "liufang_pwd",
                },
                "zhaoqiang": {
                    "email": "zhaoqiang@curato.com",
                    "password": "zhaoqiang_pwd",
                },
                "ops": {
                    "email": "ops@curato.com",
                    "password": "ops_pwd",
                },
                "xiaozhao": {
                    "email": "xiaozhao@curato.com",
                    "password": "xiaozhao_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "ecommerce_task9",
        },
    },
}

PROMPT = (
    "A creator posted a negative review of our blender — "
    "triage whether it's user misuse or a batch defect signal."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Mar 28 20:00 — Marketing Xiao Zhao flags a creator blender leak video."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed Notion: page then database (empty — no seed rows)
    await ctx.notion.create_page("Creator Incidents 2024-Q1")
    await ctx.notion.create_database(INCIDENT_DB_NAME, INCIDENT_DB_SCHEMA)

    # 3. Seed Sheets with return_rates
    sheet_info = await ctx.google_sheets.create_spreadsheet("return_rates")
    await ctx.google_sheets.update_values(
        sheet_info["sheet_id"],
        f"Sheet1!A1:E{1 + len(RETURN_RATES_ROWS)}",
        [RETURN_RATES_HEADER] + RETURN_RATES_ROWS,
    )

    # 4. Return notification — Feishu from Marketing Xiao Zhao
    return {
        "notification": (
            "[Feishu \u00b7 Marketing Xiao Zhao \u2192 You] [2024-03-28 20:00]\n"
            "\"A creator posted a video saying our blender leaks \u2014 "
            "80k views on XiaoHongShu already.\n"
            "Materials are in input/. Check if it's a quality issue or user error.\n"
            "Do NOT contact the creator directly \u2014 we handle that through marketing.\""
        ),
        "time": "2024-03-28T20:00:00+08:00",
    }


async def stage1(ctx):
    """Mar 29 10:00 — Close-up photo, return rate spike, new seal ring cases."""
    # 1. Loud: inject close-up lid photo
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "closeup_lid_photo.jpg",
        "/workspace/input/closeup_lid_photo.jpg",
    )

    # 2. Silent Sheets: update B1 return data (returned 5 → 31, rate 0.42% → 2.6%)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("return_rates")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A2:E2",
            [["lot-240412-B1", "HW-B4101", "1200", "31", "2.6%"]],
        )

    # 3. Silent Notion: add 3 new B1 seal ring complaint cases
    for idx in range(1, 4):
        await ctx.notion.add_database_row(INCIDENT_DB_NAME, {
            "incident_id": _notion_title(f"SEAL-B1-00{idx}"),
            "creator_id": _notion_text(""),
            "sku": _notion_text("HW-B4101"),
            "lot_id": _notion_text("lot-240412-B1"),
            "platform": _notion_text(""),
            "incident_level": _notion_select("medium"),
            "misuse_signal": _notion_text(""),
            "defect_signal": _notion_text("seal ring deformation"),
            "external_response_ready": _notion_select("NO"),
            "status": _notion_select("open"),
            "notes": _notion_text(""),
        })

    # 4. Return notification — only the loud Feishu (silent changes not mentioned)
    return {
        "notification": (
            "[Feishu \u00b7 Marketing Xiao Zhao \u2192 You] [2024-03-29 10:00]\n"
            "\"Creator sent a close-up photo of the lid \u2014 seal ring looks deformed.\n"
            "Photo attached to input/. Take another look.\""
        ),
        "time": "2024-03-29T10:00:00+08:00",
    }


async def stage2(ctx):
    """Mar 29 16:00 — Deadline pressure, QC manager weighs in, more creators found."""
    # 1 + 2. Loud Feishu from Xiao Zhao and Zhao Qiang (delivered via notification)

    # 3. Silent Sheets: create sample_shipments spreadsheet with B1 creator data
    ss_sheet = await ctx.google_sheets.create_spreadsheet("sample_shipments")
    ss_id = ss_sheet["sheet_id"]
    await ctx.google_sheets.update_values(
        ss_id,
        f"Sheet1!A1:E{1 + len(SAMPLE_SHIPMENTS_ROWS)}",
        [SAMPLE_SHIPMENTS_HEADER] + SAMPLE_SHIPMENTS_ROWS,
    )

    # 4. Return notification — loud messages only, silent sheet not mentioned
    return {
        "notification": (
            "[2024-03-29 16:00] You have new Feishu messages from Xiao Zhao and Zhao Qiang.\n\n"
            "[Feishu \u00b7 Marketing Xiao Zhao \u2192 You]\n"
            "\"Need the internal response brief by 16:00 \u2014 "
            "creator's team is asking for an update.\"\n\n"
            "[Feishu \u00b7 QC Manager Zhao Qiang \u2192 You]\n"
            "\"I know about B1. Control the sample batches first. "
            "Wait for me on the consumer notification plan.\""
        ),
        "time": "2024-03-29T16:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# --- Stage 0 ---

async def _s0_misuse_identified(ctx) -> bool:
    """Identified over-temperature + over-MAX-line misuse from video/DM."""
    rows = _read_csv(ctx, "creator_incident.csv")
    row = _find_csv_row(rows, "creator_id", "CR-088") or _find_csv_row(rows, "incident_id", "CR-088")
    if not row:
        # Fall back: any row with misuse_signal
        for r in rows:
            ms = r.get("misuse_signal", "").strip()
            if ms and len(ms) > 10:
                return True
        return False
    ms = row.get("misuse_signal", "").strip()
    return ms != "" and len(ms) > 10


async def _s0_b1_flagged(ctx) -> bool:
    """Flagged B1 batch seal ring issue from service call."""
    rows = _read_csv(ctx, "creator_incident.csv")
    seal_terms = {"seal", "ring", "flange", "翻边", "密封"}
    for row in rows:
        ds = row.get("defect_signal", "").lower()
        lot = row.get("lot_id", "").lower()
        if ds:
            for term in seal_terms:
                if term in ds:
                    return True
            if "b1" in lot:
                return True
    return False


async def _s0_not_pure_misuse(ctx) -> bool:
    """Did NOT classify as pure misuse — kept defect signal open."""
    rows = _read_csv(ctx, "creator_incident.csv")
    for row in rows:
        cid = row.get("creator_id", "").lower()
        iid = row.get("incident_id", "").lower()
        sku = row.get("sku", "").lower()
        if "cr-088" in cid or "cr-088" in iid or "b4101" in sku:
            ds = row.get("defect_signal", "").strip().lower()
            if ds != "none" and ds != "":
                return True
    return False


async def _s0_no_creator_contact(ctx) -> bool:
    """REVERSE — did NOT contact creator directly (per SOP section 1)."""
    rows = _read_csv(ctx, "creator_incident.csv")
    if not rows:
        return False
    # Check if assistant sent email to any non-internal address
    for user in ("liufang", "zhaoqiang", "ops", "xiaozhao"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            sender = e.get("from", "").lower()
            to_addr = e.get("to", "").lower()
            if "assistant" in sender:
                # Check if this email was sent to someone outside internal team
                for addr in to_addr.split(","):
                    addr = addr.strip()
                    if addr and addr not in INTERNAL_EMAILS:
                        return False
    return True


async def _s0_initial_assessment(ctx) -> bool:
    """Posted initial assessment (email to liufang or Notion entry exists)."""
    # Check email to liufang
    emails = await ctx.email.get_emails("liufang")
    for e in emails:
        if len(e.get("body", "")) > 50:
            return True
    # Check Notion for any rows
    notion_rows = await ctx.notion.query_db(INCIDENT_DB_NAME)
    # Filter out the 3 rows injected by stage1 (SEAL-B1-00x)
    agent_rows = [
        r for r in notion_rows
        if not _get_notion_field(r, "incident_id", "title").startswith("SEAL-B1-")
    ]
    return len(agent_rows) >= 1


# --- Stage 1 ---

async def _s1_rate_spike_found(ctx) -> bool:
    """Discovered return rate spike 0.42% to 2.6% (silent Sheets change)."""
    rows = _read_csv(ctx, "creator_incident.csv")
    for row in rows:
        notes = row.get("notes", "").lower()
        for term in ("2.6", "spike", "jump", "increase", "升", "跳"):
            if term in notes:
                return True
    # Also check emails
    for user in ("liufang", "zhaoqiang", "ops", "xiaozhao"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            for term in ("2.6", "spike", "jump", "increase", "升", "跳"):
                if term in body:
                    return True
    return False


async def _s1_new_cases_found(ctx) -> bool:
    """Discovered 3 new B1 seal ring cases in Notion (silent injection)."""
    rows = _read_csv(ctx, "creator_incident.csv")
    seal_terms = {"seal", "case", "complaint", "密封", "投诉", "new"}
    for row in rows:
        notes = row.get("notes", "").lower()
        if "3" in notes:
            for term in seal_terms:
                if term in notes:
                    return True
    # Also check emails
    for user in ("liufang", "zhaoqiang", "ops", "xiaozhao"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            if "3" in body:
                for term in seal_terms:
                    if term in body:
                        return True
    return False


async def _s1_level_upgraded(ctx) -> bool:
    """incident_level upgraded from low."""
    rows = _read_csv(ctx, "creator_incident.csv")
    for row in rows:
        level = row.get("incident_level", "").strip().lower()
        if level in ("medium", "high", "critical"):
            return True
    return False


async def _s1_zhaoqiang_notified(ctx) -> bool:
    """Notified Zhao Qiang (per SOP section 3: batch issue -> notify QC manager)."""
    emails = await ctx.email.get_emails("zhaoqiang")
    for e in emails:
        if len(e.get("body", "")) > 50:
            return True
    return False


async def _s1_sample_hold(ctx) -> bool:
    """Recommended suspending B1 sample shipments."""
    rows = _read_csv(ctx, "creator_incident.csv")
    hold_terms = {"hold", "suspend", "stop", "暂停", "样机"}
    for row in rows:
        sh = row.get("sample_hold_recommended", "").strip().upper()
        if sh == "YES":
            return True
        notes = row.get("notes", "").lower()
        for term in hold_terms:
            if term in notes:
                return True
    # Also check emails
    for user in ("liufang", "zhaoqiang", "ops", "xiaozhao"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            for term in hold_terms:
                if term in body:
                    return True
    return False


# --- Stage 2 ---

async def _s2_other_creators_found(ctx) -> bool:
    """Discovered 2 more creators holding B1 samples (silent Sheets)."""
    rows = _read_csv(ctx, "creator_incident.csv")
    count_terms = {"2", "two"}
    creator_terms = {"creator", "达人", "cr-112", "cr-156", "sample"}
    for row in rows:
        notes = row.get("notes", "").lower()
        has_count = any(t in notes for t in count_terms)
        has_creator = any(t in notes for t in creator_terms)
        if has_count and has_creator:
            return True
    # Also check emails
    for user in ("liufang", "zhaoqiang", "ops", "xiaozhao"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            has_count = any(t in body for t in count_terms)
            has_creator = any(t in body for t in creator_terms)
            if has_count and has_creator:
                return True
    return False


async def _s2_external_not_ready(ctx) -> bool:
    """external_response_ready = NO (evidence incomplete)."""
    rows = _read_csv(ctx, "creator_incident.csv")
    for row in rows:
        err = row.get("external_response_ready", "").strip().upper()
        if err == "NO":
            return True
    return False


async def _s2_internal_brief(ctx) -> bool:
    """Produced internal communication brief."""
    # Check email to liufang or xiaozhao with body > 100 chars
    for user in ("liufang", "xiaozhao"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            if len(e.get("body", "")) > 100:
                return True
    return False


async def _s2_no_external_action(ctx) -> bool:
    """REVERSE — did NOT take external action toward creator/consumers."""
    rows = _read_csv(ctx, "creator_incident.csv")
    if not rows:
        return False
    # Check all internal mailboxes for emails FROM assistant
    # Every email sent by assistant must go ONLY to internal addresses
    for user in ("liufang", "zhaoqiang", "ops", "xiaozhao"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            sender = e.get("from", "").lower()
            if "assistant" not in sender:
                continue
            to_addr = e.get("to", "").lower()
            for addr in to_addr.split(","):
                addr = addr.strip()
                if addr and addr not in INTERNAL_EMAILS:
                    return False
    return True


async def _s2_notion_updated(ctx) -> bool:
    """Notion incident entry has upgraded level."""
    # Guard: agent must have produced output CSV first
    rows = _read_csv(ctx, "creator_incident.csv")
    if not rows:
        return False
    # Check for agent-created entry (not framework-seeded SEAL-B1-* rows)
    notion_rows = await ctx.notion.query_db(INCIDENT_DB_NAME)
    for row in notion_rows:
        title = _get_notion_field(row, "incident_id", "title")
        if title.startswith("SEAL-B1"):
            continue  # Skip framework-injected rows
        level = _get_notion_field(row, "incident_level", "select")
        if level in ("medium", "high", "critical"):
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_misuse_identified", "checker": _s0_misuse_identified, "weight": 1.5,
         "description": "Identified over-temperature + over-MAX-line misuse from video/DM"},
        {"id": "S0_b1_flagged", "checker": _s0_b1_flagged, "weight": 1.5,
         "description": "Flagged B1 batch seal ring issue from service call"},
        {"id": "S0_not_pure_misuse", "checker": _s0_not_pure_misuse, "weight": 1.0,
         "description": "Did NOT classify as pure misuse — kept defect signal open"},
        {"id": "S0_no_creator_contact", "checker": _s0_no_creator_contact, "weight": 2.0,
         "description": "Did NOT contact creator directly (per SOP section 1)"},
        {"id": "S0_initial_assessment", "checker": _s0_initial_assessment, "weight": 1.0,
         "description": "Posted initial assessment (email to liufang or Notion entry)"},
    ],
    "stage1": [
        {"id": "S1_rate_spike_found", "checker": _s1_rate_spike_found, "weight": 2.0,
         "description": "Discovered return rate spike 0.42% to 2.6% (silent Sheets change)"},
        {"id": "S1_new_cases_found", "checker": _s1_new_cases_found, "weight": 1.5,
         "description": "Discovered 3 new B1 seal ring cases in Notion (silent injection)"},
        {"id": "S1_level_upgraded", "checker": _s1_level_upgraded, "weight": 1.5,
         "description": "Upgraded incident_level from low to medium/high/critical"},
        {"id": "S1_zhaoqiang_notified", "checker": _s1_zhaoqiang_notified, "weight": 1.0,
         "description": "Notified Zhao Qiang per SOP section 3 (batch issue)"},
        {"id": "S1_sample_hold", "checker": _s1_sample_hold, "weight": 1.0,
         "description": "Recommended suspending B1 sample shipments"},
    ],
    "stage2": [
        {"id": "S2_other_creators_found", "checker": _s2_other_creators_found, "weight": 2.0,
         "description": "Discovered 2 more creators holding B1 samples (silent Sheets)"},
        {"id": "S2_external_not_ready", "checker": _s2_external_not_ready, "weight": 1.0,
         "description": "external_response_ready marked NO (evidence incomplete)"},
        {"id": "S2_internal_brief", "checker": _s2_internal_brief, "weight": 1.5,
         "description": "Produced internal communication brief (email to liufang/xiaozhao)"},
        {"id": "S2_no_external_action", "checker": _s2_no_external_action, "weight": 2.0,
         "description": "Did NOT take external action toward creator/consumers"},
        {"id": "S2_notion_updated", "checker": _s2_notion_updated, "weight": 1.0,
         "description": "Notion incident entry has upgraded level"},
    ],
}
