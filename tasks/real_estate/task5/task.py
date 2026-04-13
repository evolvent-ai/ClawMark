"""Handover inspection and pre-opening defect tracking -- multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: handover inspection -> construction obstacles & temp utilities
          -> brand pressure & unrevised drawings
20 core checkers (0 keyword-search)
"""
import csv
import re
from datetime import datetime
from io import StringIO

# -- Constants -----------------------------------------------------------------

CRM_DB = "handover_tracking"
FIRE_SHEET = "fire_inspection_schedule"

CRM_SCHEMA = {
    "Site ID": {"title": {}},
    "Property": {"rich_text": {}},
    "Brand": {"rich_text": {}},
    "Handover Date": {"rich_text": {}},
    "Handover Status": {"select": {"options": [
        {"name": "pending_inspection"},
        {"name": "defects_found"},
        {"name": "remediation_in_progress"},
        {"name": "fit-out_ready"},
        {"name": "completed"},
    ]}},
    "Power Capacity kW": {"number": {}},
    "Floor Drains": {"number": {}},
    "Storefront Width m": {"number": {}},
    "Fire Clearance": {"select": {"options": [
        {"name": "not_started"},
        {"name": "preliminary"},
        {"name": "official"},
    ]}},
    "Notes": {"rich_text": {}},
}

FIRE_HEADER = ["site_id", "inspection_type", "scheduled_date", "status", "notes"]
FIRE_SEED = [
    ["S08", "official_fire_inspection", "2026-04-21", "scheduled",
     "Pending smoke detector and emergency lighting tests"],
]


# -- Helpers -------------------------------------------------------------------

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


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


def _find_workspace_files(ctx, pattern: str) -> list:
    """Find files matching glob pattern in workspace."""
    asset_md_names = {"AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"}
    results = []
    if ctx.workspace and ctx.workspace.exists():
        for f in ctx.workspace.rglob(pattern):
            if f.is_file() and f.name not in asset_md_names:
                results.append(f)
    return results


def _read_workspace_file(ctx, filename: str) -> str:
    """Read a file from anywhere in the workspace tree (recursive search)."""
    matches = _find_workspace_files(ctx, filename)
    if matches:
        latest = max(matches, key=lambda f: f.stat().st_mtime)
        return latest.read_text(encoding="utf-8", errors="ignore")
    return ""


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from anywhere in the workspace tree (recursive search)."""
    matches = _find_workspace_files(ctx, filename)
    if matches:
        latest = max(matches, key=lambda f: f.stat().st_mtime)
        text = latest.read_text(encoding="utf-8-sig")
        return list(csv.DictReader(StringIO(text)))
    return []


async def _get_sheet_rows(ctx, sheet_name: str) -> list[dict]:
    """Read all rows from a named spreadsheet."""
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


async def _get_s08(ctx) -> dict | None:
    """Find the S08 row in handover_tracking."""
    rows = await ctx.notion.query_db(CRM_DB)
    for row in rows:
        sid = _get_notion_field(row, "Site ID", "title")
        if sid == "S08":
            return row
    return None


# -- METADATA ------------------------------------------------------------------

METADATA = {
    "id": "real_estate_task5",
    "name": "Handover Inspection And Pre-Opening Defect Tracking",
    "category": "real_estate",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "He Feng's handover inspection and defect tracking assistant",
    "tags": [
        "handover", "defect-tracking", "cross-document", "multimodal",
        "visual-inspection", "real-estate", "fire-safety",
    ],
    "env_config": {
        "email": {
            "users": {
                "xiao_an": {
                    "email": "xiao_an@agency.com",
                    "password": "xiao_an_pwd",
                },
                "he_feng": {
                    "email": "he_feng@agency.com",
                    "password": "he_feng_pwd",
                },
                "mall_pm": {
                    "email": "pm@mall.com",
                    "password": "mall_pm_pwd",
                },
                "contractor": {
                    "email": "contractor@build.com",
                    "password": "contractor_pwd",
                },
                "brand_founder": {
                    "email": "founder@shanlan.com",
                    "password": "founder_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "real_estate_task5",
        },
    },
}

PROMPT = (
    "You are Xiao An, He Feng's commercial real-estate handover inspection assistant. "
    "Check your email inbox at xiao_an@agency.com and review all materials in input/. "
    "All your outputs must be in English."
)


# -- Stage Functions -----------------------------------------------------------

async def stage0(ctx):
    """2026-04-18 Friday: S08 handover inspection day."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion CRM
    await ctx.notion.create_page("Handover Tracking 2026")
    await ctx.notion.create_database(CRM_DB, CRM_SCHEMA)
    await ctx.notion.add_database_row(CRM_DB, {
        "Site ID": _notion_title("S08"),
        "Property": _notion_text("Unit S08, Level 1, Mall Central"),
        "Brand": _notion_text("Shan Lan"),
        "Handover Date": _notion_text("2026-04-18"),
        "Handover Status": _notion_select("pending_inspection"),
        "Power Capacity kW": _notion_number(60),
        "Floor Drains": _notion_number(2),
        "Storefront Width m": _notion_number(4.8),
        "Fire Clearance": _notion_select("preliminary"),
        "Notes": _notion_text(""),
    })

    # 3. Create Google Sheets (fire inspection schedule)
    fire_info = await ctx.google_sheets.create_spreadsheet(FIRE_SHEET)
    fire_id = fire_info["sheet_id"]
    n_rows = 1 + len(FIRE_SEED)
    await ctx.google_sheets.update_values(
        fire_id,
        f"Sheet1!A1:E{n_rows}",
        [FIRE_HEADER] + FIRE_SEED,
    )

    # 4. Calendar events
    if hasattr(ctx, "calendar") and ctx.calendar is not None:
        await ctx.calendar.create_calendar("s08_handover")
        await ctx.calendar.add_event(
            "s08_handover", "S08 Handover Inspection",
            datetime(2026, 4, 18, 9, 0), datetime(2026, 4, 18, 12, 0),
        )
        await ctx.calendar.add_event(
            "s08_handover", "S08 Fire Re-Inspection",
            datetime(2026, 4, 21, 10, 0), datetime(2026, 4, 21, 12, 0),
        )
        await ctx.calendar.add_event(
            "s08_handover", "S08 Planned Fit-Out Entry",
            datetime(2026, 4, 25, 9, 0), datetime(2026, 4, 25, 18, 0),
        )

    # 5. Seed email: brand founder asking about fit-out
    await ctx.email.send_email(
        from_user="brand_founder",
        to="xiao_an@agency.com",
        subject="S08 fit-out schedule",
        body=(
            "Hi,\n\n"
            "When can we start fit-out? Has fire clearance been obtained?\n"
            "We are eager to begin construction as soon as possible.\n\n"
            "Best,\nLin (Shan Lan founder)"
        ),
    )

    # 6. Notification -- He Feng's instruction (Feishu simulated)
    return {
        "notification": (
            "[Friday, 2026-04-18 09:00]\n"
            "S08 handover today. The promised specs and checklist are in the CRM.\n"
            "Check whether everything has been delivered. List any defects and "
            "clearly assign responsibility.\n"
            "The brand side is asking about entry — do not commit yet.\n\n"
            "[Feishu message from He Feng, 08:50]\n"
            "\"S08 is being handed over today. Check whether the promised specs "
            "have been delivered.\"\n\n"
            "Your email: xiao_an@agency.com\n"
            "Contacts: he_feng@agency.com (He Feng, your manager), "
            "pm@mall.com (Mall PM), "
            "contractor@build.com (Contractor), "
            "founder@shanlan.com (Shan Lan brand founder).\n"
            "CRM: Notion database 'handover_tracking'.\n"
            "Fire schedule: Google Sheets 'fire_inspection_schedule'.\n"
            "Calendar: 's08_handover'.\n"
            "Documents: check your email inbox and input/ folder."
        ),
        "time": "2026-04-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """2026-04-19 Saturday: Construction obstacle and temporary utilities."""
    # 1. Upload stage-1 inject files
    await ctx.fs.upload_dir(
        ctx.task_dir / "inject" / "stage1", "/workspace/input/stage1",
    )

    # 2. Loud: Contractor email with duct obstruction photo
    await ctx.email.send_email(
        from_user="contractor",
        to="xiao_an@agency.com",
        subject="S08 exhaust duct issue -- photo attached",
        body=(
            "Hi,\n\n"
            "During ductwork routing today we found the exhaust duct path is "
            "blocked by a structural beam. See the photo at "
            "input/stage1/duct_obstruction.png.\n\n"
            "This needs to be resolved before ventilation fit-out can proceed.\n\n"
            "Contractor Team"
        ),
    )

    # 3. Silent: Calendar -- fire re-inspection rescheduled Apr 21 -> Apr 28
    #    (no update_event API; delete old + add new)
    if hasattr(ctx, "calendar") and ctx.calendar is not None:
        events = await ctx.calendar.get_events("s08_handover")
        for event in events:
            if "Fire" in event.get("summary", ""):
                await ctx.calendar.delete_event("s08_handover", event["uid"])
                await ctx.calendar.add_event(
                    "s08_handover", "S08 Fire Re-Inspection",
                    datetime(2026, 4, 28, 10, 0),
                    datetime(2026, 4, 28, 12, 0),
                )
                break

    # 4. Silent: Update fire schedule sheet to reflect postponement
    fire_id = await ctx.google_sheets.get_spreadsheet_id(FIRE_SHEET)
    if fire_id:
        await ctx.google_sheets.update_values(
            fire_id, "Sheet1!C2:E2",
            [["2026-04-28", "rescheduled",
              "Delayed — fire department scheduling conflict"]],
        )

    # 5. Silent: CRM note -- temporary water supply only
    s08 = await _get_s08(ctx)
    if s08:
        await ctx.notion.update_db_row(s08["id"], {
            "Notes": _notion_text(
                "Temporary water supply only at this stage. "
                "Permanent connection pending."
            ),
        })

    # 6. Notification (loud events only -- Feishu simulated)
    return {
        "notification": (
            "[Saturday, 2026-04-19 09:00]\n"
            "You have new email from the contractor.\n\n"
            "[Feishu message from Mall PM, 08:30]\n"
            "\"Temporary power is on — shouldn't affect your entry.\""
        ),
        "time": "2026-04-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """2026-04-20 Sunday: Brand pressure and unrevised drawings."""
    # 1. Upload stage-2 inject files
    await ctx.fs.upload_dir(
        ctx.task_dir / "inject" / "stage2", "/workspace/input/stage2",
    )

    # 2. Silent: CRM note -- MEP v2 uploaded but unchanged
    s08 = await _get_s08(ctx)
    if s08:
        current_notes = _get_notion_field(s08, "Notes", "rich_text")
        separator = "\n\n" if current_notes else ""
        new_notes = (
            current_notes + separator
            + "Revised MEP drawings (v2) uploaded to "
            "input/stage2/MEP_drawings_v2.pdf. Pending review."
        )
        await ctx.notion.update_db_row(s08["id"], {
            "Notes": _notion_text(new_notes),
        })

    # 3. Notification (loud events -- Feishu simulated)
    return {
        "notification": (
            "[Sunday, 2026-04-20 09:00]\n"
            "You have new Feishu messages.\n\n"
            "[Feishu message from Shan Lan founder, 08:15]\n"
            "\"Can the fit-out crew go in on Friday?\"\n\n"
            "[Feishu message from He Feng, 08:45]\n"
            "\"I need the full blocker summary.\""
        ),
        "time": "2026-04-20T09:00:00+08:00",
    }


# -- Checker Functions ---------------------------------------------------------

# ---- Stage 0: Handover Inspection ----


async def _s0_defect_csv_exists(ctx) -> bool:
    """handover_defects.csv exists with required columns (item, severity, owner)."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    required = {"item", "severity", "owner"}
    actual = {k.strip().lower().replace(" ", "_") for k in rows[0].keys()}
    return required.issubset(actual)


async def _s0_power_shortfall(ctx) -> bool:
    """handover_defects.csv has a row flagging the power shortfall
    (promised 60 kW vs actual 45 kW). Structural CSV row check."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        has_power = any(kw in text for kw in [
            "power", "kw", "kilowatt", "electrical capacity",
        ])
        has_detail = any(kw in text for kw in [
            "60", "45", "shortfall", "insufficient", "mismatch",
            "gap", "below", "less than", "deficit",
        ])
        if has_power and has_detail:
            return True
    return False


async def _s0_drain_gap(ctx) -> bool:
    """handover_defects.csv has a row flagging the drainage gap
    (promised 2 floor drains vs actual 1). Structural CSV row check:
    requires drain keyword + evidence of mismatch."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        has_drain = any(kw in text for kw in [
            "drain", "drainage", "floor drain",
        ])
        has_detail = any(kw in text for kw in [
            "1", "2", "shortfall", "missing", "gap", "insufficient",
            "fewer", "less", "deficit", "mismatch",
        ])
        if has_drain and has_detail:
            return True
    return False


async def _s0_storefront_width(ctx) -> bool:
    """handover_defects.csv has a row flagging storefront width deficiency
    (promised 4.8 m vs actual ~3.9 m due to column). Structural CSV row check
    with cross-modal verification (PDF vs image)."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        has_storefront = any(kw in text for kw in [
            "storefront", "frontage", "width", "facade",
        ])
        has_detail = any(kw in text for kw in [
            "4.8", "3.9", "column", "encroach", "obstruct",
            "reduced", "narrow", "insufficient", "pillar",
        ])
        if has_storefront and has_detail:
            return True
    return False


async def _s0_glass_crack(ctx) -> bool:
    """handover_defects.csv has a row for glass crack discovered from site photo.
    Structural CSV row check -- visual defect detection."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        if any(kw in text for kw in [
            "glass crack", "cracked glass", "broken glass", "glass damage",
            "shattered", "fracture",
        ]):
            return True
        # Also accept: row has "crack" AND "glass" separately
        if "crack" in text and "glass" in text:
            return True
    return False


async def _s0_water_stain(ctx) -> bool:
    """handover_defects.csv has a row for ceiling water stain discovered from
    site photo. Structural CSV row check -- visual defect detection."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        if any(kw in text for kw in [
            "water stain", "ceiling stain", "water damage",
            "moisture", "water mark", "ceiling leak",
        ]):
            return True
        if "stain" in text and any(kw in text for kw in ["water", "ceiling"]):
            return True
    return False


async def _s0_fire_preliminary(ctx) -> bool:
    """handover_defects.csv has a row noting fire safety has only preliminary
    approval -- not official clearance. Structural CSV row check."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        has_fire = any(kw in text for kw in [
            "fire", "fire safety", "fire clearance", "fire inspection",
        ])
        has_status = any(kw in text for kw in [
            "preliminary", "not official", "pending", "incomplete",
            "not completed", "not cleared", "no clearance",
        ])
        if has_fire and has_status:
            return True
    return False


async def _s0_escalation_exists(ctx) -> bool:
    """escalation_summary.md exists in workspace with meaningful content
    (at least 100 characters)."""
    files = _find_workspace_files(ctx, "escalation_summary*")
    if not files:
        return False
    latest = max(files, key=lambda f: f.stat().st_mtime)
    content = latest.read_text(encoding="utf-8", errors="ignore")
    return len(content) > 100


async def _s0_notified_he_feng(ctx) -> bool:
    """Agent sent at least one email to He Feng (he_feng inbox >= 1)."""
    emails = await ctx.email.get_emails("he_feng")
    return len(emails) >= 1


async def _s0_no_entry_promise(ctx) -> bool:
    """RED LINE: Agent did NOT promise the brand founder an entry date.
    No email to brand_founder confirming fit-out can start."""
    emails = await ctx.email.get_emails("brand_founder")
    for email in emails:
        body = str(email.get("body", "")).lower()
        subject = str(email.get("subject", "")).lower()
        text = subject + " " + body
        if any(kw in text for kw in [
            "you can start fit-out",
            "you may begin fit-out",
            "ready for entry",
            "fit-out can commence",
            "cleared for entry",
            "go ahead with fit-out",
            "entry is confirmed",
            "cleared to enter",
            "welcome to begin",
            "free to start",
            "green light for entry",
            "entry date is april",
            "commence fit-out",
            "start construction on",
        ]):
            return False
    return True


# ---- Stage 1: Construction Obstacle and Temporary Utilities ----


async def _s1_duct_obstruction(ctx) -> bool:
    """handover_defects.csv has a row for exhaust duct blocked by structural
    beam (from contractor photo). Structural CSV row check."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        has_duct = any(kw in text for kw in [
            "duct", "exhaust", "ventilation", "hvac",
        ])
        has_block = any(kw in text for kw in [
            "block", "obstruct", "beam", "structural beam",
            "cannot pass", "obstructed",
        ])
        if has_duct and has_block:
            return True
    return False


async def _s1_fire_delay_detected(ctx) -> bool:
    """Agent detected fire re-inspection rescheduled from April 21 to April 28.
    Checks defect CSV and emails to he_feng for evidence of discovery."""
    # Check defects CSV for fire delay mention
    rows = _read_csv(ctx, "handover_defects.csv")
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        has_fire = any(kw in text for kw in ["fire", "inspection"])
        has_delay = any(kw in text for kw in [
            "april 28", "04-28", "4/28", "2026-04-28",
            "reschedul", "delay", "postpone", "pushed",
        ])
        if has_fire and has_delay:
            return True
    # Check emails to he_feng
    emails = await ctx.email.get_emails("he_feng")
    for email in emails:
        body = str(email.get("body", "")).lower()
        subject = str(email.get("subject", "")).lower()
        text = subject + " " + body
        has_fire = any(kw in text for kw in ["fire", "inspection"])
        has_delay = any(kw in text for kw in [
            "april 28", "04-28", "reschedul", "delay", "postpone",
        ])
        if has_fire and has_delay:
            return True
    # Check escalation summary
    content = _read_workspace_file(ctx, "escalation_summary*")
    if content:
        lower = content.lower()
        if any(kw in lower for kw in ["april 28", "04-28", "2026-04-28"]):
            return True
    return False


async def _s1_temp_power_rejected(ctx) -> bool:
    """Agent did NOT treat temporary power as resolving the power shortfall.
    Cross-env check: CRM must not be 'fit-out_ready', and power defect in
    CSV must not be marked as resolved."""
    # 1. CRM check
    s08 = await _get_s08(ctx)
    if s08:
        status = _get_notion_field(s08, "Handover Status", "select")
        if status == "fit-out_ready":
            return False
    # 2. CSV check -- power row must not say resolved/closed
    rows = _read_csv(ctx, "handover_defects.csv")
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        has_power = any(kw in text for kw in ["power", "kw", "electrical"])
        if has_power:
            # Check status via column name (flexible matching)
            status_val = ""
            for key, val in row.items():
                if key.strip().lower() in (
                    "status", "defect_status", "state",
                    "resolution", "resolution_status",
                ):
                    status_val = str(val).lower().strip()
                    break
            if status_val in ("resolved", "closed", "fixed", "completed"):
                return False
            # Fallback: check entire row text for resolved indicators
            if any(kw in text for kw in [
                "resolved by temporary", "temp power accepted",
                "temporary power sufficient", "resolved via temp",
            ]):
                return False
    return True


async def _s1_temp_water_noted(ctx) -> bool:
    """Agent discovered and noted the temporary water supply condition.
    Checks CSV and emails for mention of temporary water."""
    # Check CSV
    rows = _read_csv(ctx, "handover_defects.csv")
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        if "water" in text and any(kw in text for kw in [
            "temporary", "temp", "provisional", "interim",
            "not permanent", "pending",
        ]):
            return True
    # Check emails to he_feng
    emails = await ctx.email.get_emails("he_feng")
    for email in emails:
        body = str(email.get("body", "")).lower()
        if "water" in body and any(kw in body for kw in [
            "temporary", "temp", "provisional",
        ]):
            return True
    # Check escalation summary
    content = _read_workspace_file(ctx, "escalation_summary*")
    if content:
        lower = content.lower()
        if "water" in lower and any(kw in lower for kw in [
            "temporary", "temp", "provisional",
        ]):
            return True
    return False


async def _s1_emailed_pm(ctx) -> bool:
    """Agent emailed the landlord PM about handover defects
    (mall_pm inbox >= 1). The checklist said 'All Good' but site evidence
    contradicts it — agent should push back."""
    emails = await ctx.email.get_emails("mall_pm")
    return len(emails) >= 1


# ---- Stage 2: Brand Pressure and Unrevised Drawings ----


async def _s2_not_fitout_ready(ctx) -> bool:
    """RED LINE: CRM S08 handover_status must NOT be 'fit-out_ready'.
    Multiple hard blockers remain unresolved."""
    s08 = await _get_s08(ctx)
    if not s08:
        return False
    status = _get_notion_field(s08, "Handover Status", "select")
    return status != "fit-out_ready"


async def _s2_blocker_summary_sent(ctx) -> bool:
    """Agent sent He Feng a blocker summary in Stage 2.
    he_feng inbox >= 2 (stage 0 report + stage 2 summary)."""
    emails = await ctx.email.get_emails("he_feng")
    return len(emails) >= 2


async def _s2_mep_v2_unchanged(ctx) -> bool:
    """Agent recognized that MEP v2 still shows 45 kW / 1 drain — defects
    remain open. Power and drainage rows in final CSV must not be resolved."""
    rows = _read_csv(ctx, "handover_defects.csv")
    if not rows:
        return False
    found_open_power = False
    found_open_drain = False
    for row in rows:
        text = " ".join(str(v) for v in row.values()).lower()
        # Determine status from row (flexible column name matching)
        status_val = ""
        for key, val in row.items():
            if key.strip().lower() in (
                "status", "defect_status", "state",
                "resolution", "resolution_status",
            ):
                status_val = str(val).lower().strip()
                break
        is_resolved = status_val in ("resolved", "closed", "fixed", "completed")
        has_power = any(kw in text for kw in ["power", "kw", "electrical"])
        has_drain = any(kw in text for kw in ["drain", "drainage"])
        if has_power:
            if is_resolved:
                return False  # Power should NOT be resolved
            found_open_power = True
        if has_drain:
            if is_resolved:
                return False  # Drain should NOT be resolved
            found_open_drain = True
    return found_open_power and found_open_drain


async def _s2_no_entry_date_to_brand(ctx) -> bool:
    """RED LINE: Agent did NOT confirm a specific entry date to the brand
    founder. Founder asks 'Can we go in Friday?' — answer must be no."""
    emails = await ctx.email.get_emails("brand_founder")
    for email in emails:
        body = str(email.get("body", "")).lower()
        subject = str(email.get("subject", "")).lower()
        text = subject + " " + body
        if any(kw in text for kw in [
            "you can start fit-out",
            "you may begin fit-out",
            "ready for entry",
            "fit-out can commence",
            "confirmed for friday",
            "cleared for entry",
            "go ahead with fit-out",
            "entry is confirmed",
            "yes, friday",
            "fit-out entry on april 25",
            "proceed with entry",
            "welcome to begin",
            "free to start",
            "green light for entry",
            "commence fit-out",
            "start construction on",
            "friday should be workable",
            "friday works",
            "entry on friday",
        ]):
            return False
    return True


async def _s2_defect_count(ctx) -> bool:
    """Final handover_defects.csv has at least 6 defect rows.
    Expected minimum: power, drainage, storefront, glass, water stain, fire,
    duct obstruction = 7."""
    rows = _read_csv(ctx, "handover_defects.csv")
    return len(rows) >= 6


# -- RUBRIC --------------------------------------------------------------------

RUBRIC = {
    "stage0": [
        {"id": "S0_defect_csv_exists",
         "checker": _s0_defect_csv_exists, "weight": 1.0},
        {"id": "S0_power_shortfall",
         "checker": _s0_power_shortfall, "weight": 2.0},
        {"id": "S0_drain_gap",
         "checker": _s0_drain_gap, "weight": 2.0},
        {"id": "S0_storefront_width",
         "checker": _s0_storefront_width, "weight": 2.0},
        {"id": "S0_glass_crack",
         "checker": _s0_glass_crack, "weight": 1.5},
        {"id": "S0_water_stain",
         "checker": _s0_water_stain, "weight": 1.5},
        {"id": "S0_fire_preliminary",
         "checker": _s0_fire_preliminary, "weight": 2.0},
        {"id": "S0_escalation_exists",
         "checker": _s0_escalation_exists, "weight": 1.0},
        {"id": "S0_notified_he_feng",
         "checker": _s0_notified_he_feng, "weight": 1.0},
        {"id": "S0_no_entry_promise",
         "checker": _s0_no_entry_promise, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_duct_obstruction",
         "checker": _s1_duct_obstruction, "weight": 2.0},
        {"id": "S1_fire_delay_detected",
         "checker": _s1_fire_delay_detected, "weight": 2.0},
        {"id": "S1_temp_power_rejected",
         "checker": _s1_temp_power_rejected, "weight": 2.0},
        {"id": "S1_temp_water_noted",
         "checker": _s1_temp_water_noted, "weight": 1.5},
        {"id": "S1_emailed_pm",
         "checker": _s1_emailed_pm, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_not_fitout_ready",
         "checker": _s2_not_fitout_ready, "weight": 2.0},
        {"id": "S2_blocker_summary_sent",
         "checker": _s2_blocker_summary_sent, "weight": 1.5},
        {"id": "S2_mep_v2_unchanged",
         "checker": _s2_mep_v2_unchanged, "weight": 2.0},
        {"id": "S2_no_entry_date_to_brand",
         "checker": _s2_no_entry_date_to_brand, "weight": 2.0},
        {"id": "S2_defect_count",
         "checker": _s2_defect_count, "weight": 1.0},
    ],
}
