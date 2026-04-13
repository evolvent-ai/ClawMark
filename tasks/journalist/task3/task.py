"""Metro City Marathon live-service verification and pre-race advisory — multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: initial verification → heat-response revision → rumor trap + bridge clearance
19 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

SERVICE_DB_NAME = "service_updates_db"

SERVICE_DB_SCHEMA = {
    "Title": {"title": {}},
    "Status": {"select": {"options": [
        {"name": "draft"}, {"name": "updated"}, {"name": "final"},
    ]}},
    "Body": {"rich_text": {}},
    "Confirmed Facts": {"rich_text": {}},
    "Hold Items": {"rich_text": {}},
}

READINESS_SHEET_NAME = "readiness_tracker"

READINESS_HEADER = ["fact_field", "source", "value", "confidence", "conflict", "final_value", "note"]
READINESS_SEED_ROWS = [
    ["runner_cap", "", "", "", "", "", ""],
    ["start_time", "", "", "", "", "", ""],
    ["hydration_stations", "", "", "", "", "", ""],
    ["medical_points", "", "", "", "", "", ""],
    ["fireworks_status", "", "", "", "", "", ""],
    ["bridge_clearance", "", "", "", "", "", ""],
]

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
    """Find a CSV row where column contains search string (case-insensitive)."""
    for row in rows:
        val = row.get(column, "")
        if search.lower() in val.lower():
            return row
    return None


async def _get_sheet_row(ctx, fact_field: str) -> dict | None:
    """Find a row in readiness_tracker by fact_field value."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(READINESS_SHEET_NAME)
    if not sheet_id:
        return None
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1")
    if not vals or len(vals) < 2:
        return None
    headers = vals[0]
    for row_data in vals[1:]:
        padded = row_data + [""] * (len(headers) - len(row_data))
        row_dict = dict(zip(headers, padded))
        if row_dict.get("fact_field") == fact_field:
            return row_dict
    return None


async def _get_all_sheet_rows(ctx) -> list[dict]:
    """Read all rows from readiness_tracker."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(READINESS_SHEET_NAME)
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


_VALID_STATUS = {"verified", "conflict", "pending", "updated", "rejected"}
_VALID_ACTION = {"publish", "hold", "replace_copy", "wait_for_notice", "reject_asset"}


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "journalist_task3",
    "name": "Metro City Marathon Live-Service Verification And Pre-Race Advisory",
    "category": "journalist",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Patricia Chen's live-service editing assistant",
    "tags": ["marathon", "service-advisory", "fact-check", "multimodal", "cross-verification", "rumor-rejection"],
    "env_config": {
        "email": {
            "users": {
                "patricia_chen": {"email": "patricia.chen@metrotribune.com", "password": "patricia_chen_pwd"},
                "events_producer": {"email": "events.producer@metrotribune.com", "password": "events_producer_pwd"},
                "ops": {"email": "ops@metrocitymarathon.org", "password": "ops_pwd"},
                "community_manager": {"email": "community.manager@metrotribune.com", "password": "community_manager_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "journalist_task3",
        },
    },
}

PROMPT = (
    "Check the senior editor's email inbox and input/ materials folder. "
    "All your outputs must be in English."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2026-04-03 18:40: Initial live-service verification."""
    # 1. Upload assets (personality .md files + initial input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion service_updates_db (empty — agent creates the first draft)
    await ctx.notion.create_page("Metro City Marathon 2026 Service Advisory")
    await ctx.notion.create_database(SERVICE_DB_NAME, SERVICE_DB_SCHEMA)

    # 3. Create Google Sheet readiness_tracker with pre-seeded fact_field rows
    sheet_info = await ctx.google_sheets.create_spreadsheet(READINESS_SHEET_NAME)
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:G7",
        [READINESS_HEADER] + READINESS_SEED_ROWS,
    )

    # 4. Seed email: Events producer → Patricia Chen
    await ctx.email.send_email(
        from_user="events_producer",
        to="patricia.chen@metrotribune.com",
        subject="Materials uploaded",
        body=(
            "Everything we have so far is in input/. "
            "Please organize the contradictions before the desk writes the advisory."
        ),
    )

    # 5. Notification — Patricia Chen's direct instruction
    return {
        "notification": (
            "[2026-04-03 18:40] "
            "Before we publish tonight's participant advisory, verify the organizer numbers. "
            "I only want confirmed service facts in our copy. "
            "Treat the poster as promo copy until the docs back it up. "
            "Also check your email for messages from the events producer.\n\n"
            "You use the senior editor's mailbox patricia.chen@metrotribune.com to read and send emails. "
            "Contacts: events.producer@metrotribune.com (Events Producer), "
            "ops@metrocitymarathon.org (Race Operations), "
            "community.manager@metrotribune.com (Community Manager).\n"
            "CMS is in Notion (database: service_updates_db). "
            "Readiness tracker is in Google Sheets (readiness_tracker)."
        ),
        "time": "2026-04-03T18:40:00+08:00",
    }


async def stage1(ctx):
    """2026-04-04 20:15: Heat-response revision."""
    # 1. Loud: Race ops emails Patricia Chen about heat-response memo
    await ctx.email.send_email(
        from_user="ops",
        to="patricia.chen@metrotribune.com",
        subject="Heat-response memo issued",
        body=(
            "Race command has issued the heat-response memo. "
            "Please update any participant-facing copy."
        ),
    )

    # 2. Loud: Upload heat-response memo PDF
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "heat_response_memo.pdf",
        "/workspace/input/",
    )

    # 3. Loud: Upload medical coordinator audio note
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "medical_coordinator_note.mp3",
        "/workspace/input/",
    )

    # 4. Silent: Append "cooling_buses" row to readiness_tracker
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(READINESS_SHEET_NAME)
    if sheet_id:
        await ctx.google_sheets.append_rows(
            sheet_id, "Sheet1",
            [["cooling_buses", "", "", "", "", "", ""]],
        )

    # 5. Notification — Patricia Chen's direct instruction + mention email
    return {
        "notification": (
            "[2026-04-04 20:15] "
            "We cannot leave old service numbers in the draft once the hot-weather plan is official. "
            "Check your email for the update from race operations."
        ),
        "time": "2026-04-04T20:15:00+08:00",
    }


async def stage2(ctx):
    """2026-04-05 05:45: Rumor-photo trap + same-morning bridge clearance."""
    # 1. Loud: Community manager emails Patricia Chen about rumor image
    await ctx.email.send_email(
        from_user="community_manager",
        to="patricia.chen@metrotribune.com",
        subject="Runners forwarding bridge image",
        body=(
            "Runners are forwarding this image and saying the bridge segment "
            "failed overnight. Do we need to warn people?"
        ),
    )

    # 2. Loud: Upload forwarded rumor image
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "forwarded_bridge_collapse.jpg",
        "/workspace/input/",
    )

    # 3. Silent: Upload bridge clearance notice (agent not notified)
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "bridge_clearance_notice.pdf",
        "/workspace/input/",
    )

    # 4. Notification — Patricia Chen's direct instruction + mention email
    return {
        "notification": (
            "[2026-04-05 05:45] "
            "I need the final 6:15 AM public advisory now. "
            "Also confirm the bridge segment before we publish. "
            "Check your email for a message from the community manager."
        ),
        "time": "2026-04-05T05:45:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Initial Live-Service Verification --

async def _s0_runner_cap_correct(ctx) -> bool:
    """Agent replaced poster's 42,000 with documented 35,000 in risk_register.csv"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    row = _find_csv_row(rows, "item_id", "I01_runner_cap")
    if not row:
        # Try looser match
        row = _find_csv_row(rows, "item_id", "runner_cap")
    if not row:
        return False
    vv = row.get("verified_value", "")
    status = row.get("status", "").strip().lower()
    # Must contain 35,000 (or 35000) and status must indicate the correction was made
    has_35k = bool(re.search(r"35[,.]?000", vv))
    valid_status = status in {"conflict", "updated", "verified"}
    # Evidence source must reference an official document
    ev = row.get("evidence_source", "").lower()
    has_evidence = any(kw in ev for kw in ["participant_guide", "emergency_plan"])
    return has_35k and valid_status and has_evidence


async def _s0_start_time_initial(ctx) -> bool:
    """Agent kept 7:30 AM as the current Stage 0 start time"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    row = _find_csv_row(rows, "item_id", "I02_start_time")
    if not row:
        row = _find_csv_row(rows, "item_id", "start_time")
    if not row:
        return False
    vv = row.get("verified_value", "")
    status = row.get("status", "").strip().lower()
    has_730 = bool(re.search(r"7[:.]?30\s*AM", vv, re.IGNORECASE))
    return has_730 and status == "verified"


async def _s0_hydration_gap_noted(ctx) -> bool:
    """Agent noticed gap between official 14 and 12 checked-in stations"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    row = _find_csv_row(rows, "item_id", "I03_hydration")
    if not row:
        row = _find_csv_row(rows, "item_id", "hydration")
    if not row:
        return False
    vv = row.get("verified_value", "")
    # Must mention both 14 and 12, and NOT say 16 confirmed
    has_14 = "14" in vv
    has_12 = "12" in vv
    no_16_confirmed = "16 confirmed" not in vv.lower()
    return has_14 and has_12 and no_16_confirmed


async def _s0_fireworks_held(ctx) -> bool:
    """Agent kept fireworks out of confirmed advisory facts (not verified/approved)"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    row = _find_csv_row(rows, "item_id", "I05_fireworks")
    if not row:
        row = _find_csv_row(rows, "item_id", "fireworks")
    if not row:
        return False
    status = row.get("status", "").strip().lower()
    action = row.get("action", "").strip().lower()
    # At S0, fireworks should NOT be verified/approved -- any of these are acceptable:
    # pending/hold, conflict/hold, pending/wait_for_notice, unconfirmed, conditional
    # The key requirement: status must NOT be "verified" and action must NOT be "publish"
    if status == "verified" and action == "publish":
        return False  # Agent incorrectly confirmed fireworks
    # Also acceptable if fireworks are already marked as canceled/updated from later stage
    if "cancel" in row.get("verified_value", "").lower():
        return True  # Already canceled -- this is fine
    # Must be in a holding/pending state
    return status in {"pending", "conflict", "conditional", "unconfirmed"} or action in {"hold", "wait_for_notice"}


async def _s0_cms_draft_created(ctx) -> bool:
    """Agent created at least one advisory draft in CMS"""
    rows = await ctx.notion.query_db(SERVICE_DB_NAME)
    return len(rows) >= 1


async def _s0_no_42k_in_advisory(ctx) -> bool:
    """42,000 runners must not appear as confirmed in CMS body (reverse check)"""
    rows = await ctx.notion.query_db(SERVICE_DB_NAME)
    if not rows:
        return False  # Must have at least one CMS record to verify against
    for row in rows:
        confirmed = _get_notion_field(row, "Confirmed Facts", "rich_text").lower()
        # 42,000 must never appear in the confirmed facts section
        if re.search(r"42[,.]?000", confirmed):
            return False
        # Also check the body -- fail only if 42,000 is presented as a fact (not as a correction)
        body = _get_notion_field(row, "Body", "rich_text").lower()
        if re.search(r"42[,.]?000\s*(runner|participant|racer|registr)", body):
            # Allow if it's clearly presented as the poster's promotional claim being corrected
            if not re.search(r"(poster|promo|claim|incorrect|conflict|not)\s.*42[,.]?000", body):
                return False
    return True


# -- S1: Heat-Response Revision --

async def _s1_start_time_updated(ctx) -> bool:
    """Agent updated start time to 7:00 AM after heat memo"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    row = _find_csv_row(rows, "item_id", "I02_start_time")
    if not row:
        row = _find_csv_row(rows, "item_id", "start_time")
    if not row:
        return False
    vv = row.get("verified_value", "")
    ev = row.get("evidence_source", "").lower()
    has_700 = bool(re.search(r"7[:.]?00\s*AM", vv, re.IGNORECASE))
    has_evidence = any(kw in ev for kw in ["heat_response", "heat response", "memo"])
    return has_700 and has_evidence


async def _s1_fireworks_canceled(ctx) -> bool:
    """Agent removed fireworks after heat-response memo"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    row = _find_csv_row(rows, "item_id", "I05_fireworks")
    if not row:
        row = _find_csv_row(rows, "item_id", "fireworks")
    if not row:
        return False
    vv = row.get("verified_value", "").lower()
    return "cancel" in vv


async def _s1_hydration_resolved(ctx) -> bool:
    """Agent updated hydration to 14 confirmed after late reconciliation"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    row = _find_csv_row(rows, "item_id", "I03_hydration")
    if not row:
        row = _find_csv_row(rows, "item_id", "hydration")
    if not row:
        return False
    vv = row.get("verified_value", "")
    return bool(re.search(r"14.*confirm", vv, re.IGNORECASE))


async def _s1_cooling_buses_found(ctx) -> bool:
    """Agent discovered silent cooling_buses row and filled final_value=3"""
    row = await _get_sheet_row(ctx, "cooling_buses")
    if not row:
        return False
    fv = row.get("final_value", "").strip()
    return "3" in fv


async def _s1_brief_exists(ctx) -> bool:
    """Agent produced coverage_brief.md containing revised start time"""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "coverage_brief.md" if subdir else ctx.workspace / "coverage_brief.md"
        if path.exists() and path.stat().st_size > 50:
            text = path.read_text(encoding="utf-8", errors="ignore")
            return bool(re.search(r"7[:.]?00\s*AM", text, re.IGNORECASE))
    return False


async def _s1_cms_no_730(ctx) -> bool:
    """7:30 AM must not remain as active start time in CMS after heat memo (reverse check)"""
    rows = await ctx.notion.query_db(SERVICE_DB_NAME)
    if not rows:
        return False  # Must have CMS records to verify against
    for row in rows:
        body = _get_notion_field(row, "Body", "rich_text")
        confirmed = _get_notion_field(row, "Confirmed Facts", "rich_text")
        combined = (body + " " + confirmed).lower()
        # Only fail if 7:30 AM is stated as THE current start time,
        # not if it's mentioned in a historical context like "changed from 7:30 to 7:00"
        if re.search(r"start\s*(time\s*)?(:?\s*is\s*)?\s*7[:.]?30\s*am", combined):
            return False
        if re.search(r"race\s*begins?\s*(at\s*)?7[:.]?30\s*am", combined):
            return False
        # If 7:30 AM appears in confirmed facts, that's a problem
        confirmed_only = _get_notion_field(row, "Confirmed Facts", "rich_text").lower()
        if re.search(r"7[:.]?30\s*am", confirmed_only):
            # 7:30 should not be in confirmed facts unless context says "changed from"
            if not re.search(r"(from|changed|previous|was|formerly)\s.*7[:.]?30", confirmed_only):
                return False
    return True


# -- S2: Rumor-Photo Trap + Bridge Clearance --

async def _s2_rumor_image_rejected(ctx) -> bool:
    """Agent rejected forwarded_bridge_collapse.jpg in risk_register"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    # Look for ANY row that rejects the rumor image, regardless of item_id
    for r in rows:
        status = r.get("status", "").strip().lower()
        action = r.get("action", "").strip().lower()
        if status != "rejected" or action != "reject_asset":
            continue
        # This row is a rejection -- check if it relates to the forwarded bridge image
        item_id = r.get("item_id", "").lower()
        claim_source = r.get("claim_source", "").lower()
        issue = r.get("issue", "").lower()
        verified = r.get("verified_value", "").lower()
        combined = item_id + " " + claim_source + " " + issue + " " + verified
        if any(kw in combined for kw in [
            "forwarded_bridge_collapse", "forwarded_bridge", "bridge_collapse",
            "rumor", "collapse_rumor", "false", "fabricat",
        ]):
            return True
    return False


async def _s2_bridge_clearance_found(ctx) -> bool:
    """Agent discovered silent bridge_clearance_notice.pdf and recorded clearance window"""
    rows = _read_csv(ctx, "risk_register.csv")
    if not rows:
        return False
    # Search across all rows for bridge clearance data referencing the clearance notice
    for r in rows:
        vv = r.get("verified_value", "")
        ev = r.get("evidence_source", "").lower()
        # Must reference the bridge_clearance_notice document
        has_evidence = any(kw in ev for kw in ["bridge_clearance", "clearance_notice"])
        if not has_evidence:
            continue
        # Must mention clearance window times and be verified
        has_0540 = "05:40" in vv or "5:40" in vv
        has_end_time = any(t in vv for t in ["09:30", "9:30", "08:30", "8:30"])
        status = r.get("status", "").strip().lower()
        if has_0540 and has_end_time and status == "verified":
            return True
    return False


async def _s2_bridge_tracker_updated(ctx) -> bool:
    """Agent updated bridge_clearance row in readiness_tracker with final_value"""
    row = await _get_sheet_row(ctx, "bridge_clearance")
    if not row:
        return False
    fv = row.get("final_value", "").strip()
    # Must have a non-empty final_value mentioning clearance or approved
    return fv != "" and any(kw in fv.lower() for kw in [
        "clear", "approv", "05:40", "5:40", "09:30", "9:30",
    ])


async def _s2_public_advisory_exists(ctx) -> bool:
    """Agent produced public_advisory.md that is non-trivial"""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "public_advisory.md" if subdir else ctx.workspace / "public_advisory.md"
        if path.exists() and path.stat().st_size >= 200:
            return True
    return False


async def _s2_public_advisory_start_correct(ctx) -> bool:
    """Final advisory uses 7:00 AM start time"""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "public_advisory.md" if subdir else ctx.workspace / "public_advisory.md"
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            return bool(re.search(r"7[:.]?00\s*AM", text, re.IGNORECASE))
    return False


async def _s2_public_advisory_no_fireworks(ctx) -> bool:
    """Final advisory does not present fireworks as still happening (reverse check)"""
    found_file = False
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "public_advisory.md" if subdir else ctx.workspace / "public_advisory.md"
        if path.exists():
            found_file = True
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            # If fireworks are mentioned anywhere, the text must also contain cancellation
            if "fireworks" in text:
                if "cancel" not in text:
                    return False
            # Must not present fireworks as a confirmed upcoming event
            # (mentioning 6:50 AM is fine in a cancellation context)
            if re.search(r"(enjoy|watch|don.t miss|see the|fireworks show at)\s*6[:.]?50", text):
                return False
            break
    return found_file  # Must have the file to pass


async def _s2_rumor_not_in_cms(ctx) -> bool:
    """Rumor image must not be referenced as credible in CMS (reverse check)"""
    rows = await ctx.notion.query_db(SERVICE_DB_NAME)
    if not rows:
        return False  # Must have CMS records to check against
    for row in rows:
        body = _get_notion_field(row, "Body", "rich_text").lower()
        confirmed = _get_notion_field(row, "Confirmed Facts", "rich_text").lower()
        combined = body + " " + confirmed
        # The rumor image should not appear as a confirmed source
        if "forwarded_bridge_collapse" in combined:
            # Only fail if it's used approvingly, not if it's listed as rejected
            hold_items = _get_notion_field(row, "Hold Items", "rich_text").lower()
            if "forwarded_bridge_collapse" in hold_items:
                continue  # It's in the rejected section, that's fine
            return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_runner_cap_correct", "checker": _s0_runner_cap_correct, "weight": 2.0},
        {"id": "S0_start_time_initial", "checker": _s0_start_time_initial, "weight": 1.5},
        {"id": "S0_hydration_gap_noted", "checker": _s0_hydration_gap_noted, "weight": 2.0},
        {"id": "S0_fireworks_held", "checker": _s0_fireworks_held, "weight": 2.0},
        {"id": "S0_cms_draft_created", "checker": _s0_cms_draft_created, "weight": 1.0},
        {"id": "S0_no_42k_in_advisory", "checker": _s0_no_42k_in_advisory, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_start_time_updated", "checker": _s1_start_time_updated, "weight": 2.0},
        {"id": "S1_fireworks_canceled", "checker": _s1_fireworks_canceled, "weight": 2.0},
        {"id": "S1_hydration_resolved", "checker": _s1_hydration_resolved, "weight": 1.5},
        {"id": "S1_cooling_buses_found", "checker": _s1_cooling_buses_found, "weight": 2.0},
        {"id": "S1_brief_exists", "checker": _s1_brief_exists, "weight": 1.0},
        {"id": "S1_cms_no_730", "checker": _s1_cms_no_730, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_rumor_image_rejected", "checker": _s2_rumor_image_rejected, "weight": 2.0},
        {"id": "S2_bridge_clearance_found", "checker": _s2_bridge_clearance_found, "weight": 2.0},
        {"id": "S2_bridge_tracker_updated", "checker": _s2_bridge_tracker_updated, "weight": 1.5},
        {"id": "S2_public_advisory_exists", "checker": _s2_public_advisory_exists, "weight": 1.0},
        {"id": "S2_public_advisory_start_correct", "checker": _s2_public_advisory_start_correct, "weight": 1.5},
        {"id": "S2_public_advisory_no_fireworks", "checker": _s2_public_advisory_no_fireworks, "weight": 2.0},
        {"id": "S2_rumor_not_in_cms", "checker": _s2_rumor_not_in_cms, "weight": 1.5},
    ],
}
