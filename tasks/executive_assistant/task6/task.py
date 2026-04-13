"""Annual summit replay audit and feedback handling -- multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: replay audit & risk log -> legal/speaker/technical follow-up -> final package & ROI
16 core checkers (0 keyword-search)
"""
import csv
from io import StringIO
from pathlib import Path

# -- Constants ----------------------------------------------------------------

SPONSOR_DB_NAME = "sponsor_db"

SPONSOR_DB_SCHEMA = {
    "Sponsor": {"title": {}},
    "Status": {"select": {"options": [
        {"name": "active"}, {"name": "withdrawn"}, {"name": "suspended"},
    ]}},
    "Notes": {"rich_text": {}},
}

SPONSOR_SEED_ROWS = [
    {"sponsor": "Sponsor A", "status": "active", "notes": "No special note yet"},
    {"sponsor": "Sponsor B", "status": "active", "notes": "No special note yet"},
    {"sponsor": "Sponsor C", "status": "active", "notes": "No withdrawal note yet"},
]

RISK_DB_NAME = "risk_incidents"

RISK_DB_SCHEMA = {
    "Incident Title": {"title": {}},
    "Timestamp": {"rich_text": {}},
    "Severity": {"select": {"options": [
        {"name": "critical"}, {"name": "high"}, {"name": "medium"}, {"name": "low"},
    ]}},
    "Risk Type": {"rich_text": {}},
    "Evidence Source": {"rich_text": {}},
    "Recommended Handling": {"rich_text": {}},
    "Owner": {"rich_text": {}},
}

ISSUE_TRACKER_NAME = "issue_timestamp_tracker"
ISSUE_TRACKER_HEADER = [
    "timestamp", "issue_type", "severity", "source",
    "public_replay_action", "owner", "notes",
]

FEEDBACK_INDEX_NAME = "feedback_screenshot_index"
FEEDBACK_INDEX_HEADER = [
    "screenshot_file", "content_type", "key_signal", "follow_up_needed", "notes",
]

REG_STATS_NAME = "registration_stats"
REG_STATS_HEADER = ["metric", "value", "source"]

# -- Helpers ------------------------------------------------------------------


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


_FRAMEWORK_MD_NAMES = {"AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"}

_SKIP_DIRS = {"input", "memory"}


def _is_agent_output_file(f: Path, workspace: Path) -> bool:
    """Return True if f is an agent-produced file (not framework or input)."""
    if f.name in _FRAMEWORK_MD_NAMES:
        return False
    try:
        rel = f.relative_to(workspace)
        if rel.parts and rel.parts[0] in _SKIP_DIRS:
            return False
    except ValueError:
        return False
    return True


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace root or workspace/outputs/."""
    for subdir in ["outputs", ""]:
        path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _scan_agent_text_files(ctx) -> str:
    """Collect text from all agent-produced files in workspace (not input/memory/framework)."""
    all_text = ""
    if not ctx.workspace or not ctx.workspace.exists():
        return all_text
    for f in ctx.workspace.rglob("*"):
        if not f.is_file():
            continue
        if not _is_agent_output_file(f, ctx.workspace):
            continue
        if f.suffix in (".md", ".csv", ".txt", ".json"):
            try:
                all_text += f.read_text(encoding="utf-8", errors="ignore") + " "
            except Exception:
                pass
    return all_text


async def _get_sheet_rows(ctx, sheet_name: str) -> list[dict]:
    """Read all rows from a named sheet as list of dicts."""
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


async def _get_sheet_row(ctx, sheet_name: str, key_col: str, key_val: str) -> dict | None:
    """Find a specific row in a named sheet by key column value."""
    rows = await _get_sheet_rows(ctx, sheet_name)
    for row in rows:
        if key_val.lower() in row.get(key_col, "").lower():
            return row
    return None


async def _find_notion_sponsor(ctx, sponsor_name: str) -> dict | None:
    """Find a sponsor row in the sponsor database."""
    rows = await ctx.notion.query_db(SPONSOR_DB_NAME)
    for row in rows:
        title = _get_notion_field(row, "Sponsor", "title")
        if sponsor_name.lower() in title.lower():
            return row
    return None


# -- METADATA -----------------------------------------------------------------

METADATA = {
    "id": "executive_assistant_task6",
    "name": "Annual Summit Replay Audit And Feedback Handling",
    "category": "executive_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhou Jie's executive assistant",
    "tags": [
        "replay-audit", "sponsor", "legal-risk", "feedback",
        "multimodal", "cross-verification", "pptx",
    ],
    "env_config": {
        "email": {
            "users": {
                "zhou_jie": {"email": "zhou.jie@company.com", "password": "zhou_jie_pwd"},
                "legal": {"email": "legal@company.com", "password": "legal_pwd"},
                "speaker": {"email": "speaker@partner.com", "password": "speaker_pwd"},
                "marketing": {"email": "marketing@company.com", "password": "marketing_pwd"},
                "ceo_office": {"email": "ceo.office@company.com", "password": "ceo_office_pwd"},
                "livestream_ops": {
                    "email": "livestream.ops@company.com",
                    "password": "livestream_ops_pwd",
                },
                "replay_vendor": {
                    "email": "replay.vendor@service.example",
                    "password": "replay_vendor_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "executive_assistant_task6",
        },
    },
}

PROMPT = (
    "Check Zhou Jie's email inbox and the input/ materials folder. "
    "Zhou Jie left a voice note for you. "
    "All your outputs must be in English."
)


# -- Stage Functions ----------------------------------------------------------

async def stage0(ctx):
    """2025-03-17 Monday: Replay audit and initial risk log."""
    # 1. Upload assets (personality .md files + initial input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page for annual summit review
    await ctx.notion.create_page("Annual Summit Review 2025")

    # 3. Create Notion sponsor database + seed rows
    await ctx.notion.create_database(SPONSOR_DB_NAME, SPONSOR_DB_SCHEMA)
    for rec in SPONSOR_SEED_ROWS:
        await ctx.notion.add_database_row(SPONSOR_DB_NAME, {
            "Sponsor": _notion_title(rec["sponsor"]),
            "Status": _notion_select(rec["status"]),
            "Notes": _notion_text(rec["notes"]),
        })

    # 4. Create Notion risk incident database (blank template)
    await ctx.notion.create_database(RISK_DB_NAME, RISK_DB_SCHEMA)

    # 5. Create Google Sheet: issue_timestamp_tracker (empty template)
    tracker_info = await ctx.google_sheets.create_spreadsheet(ISSUE_TRACKER_NAME)
    tracker_id = tracker_info["sheet_id"]
    await ctx.google_sheets.update_values(
        tracker_id, "Sheet1!A1:G1",
        [ISSUE_TRACKER_HEADER],
    )

    # 6. Create Google Sheet: feedback_screenshot_index (empty template)
    feedback_info = await ctx.google_sheets.create_spreadsheet(FEEDBACK_INDEX_NAME)
    feedback_id = feedback_info["sheet_id"]
    await ctx.google_sheets.update_values(
        feedback_id, "Sheet1!A1:E1",
        [FEEDBACK_INDEX_HEADER],
    )

    # 7. Create Google Sheet: registration_stats (empty template)
    reg_info = await ctx.google_sheets.create_spreadsheet(REG_STATS_NAME)
    reg_id = reg_info["sheet_id"]
    await ctx.google_sheets.update_values(
        reg_id, "Sheet1!A1:C1",
        [REG_STATS_HEADER],
    )

    # 8. Seed emails in Zhou Jie's inbox
    # 8a. Livestream vendor email
    await ctx.email.send_email(
        from_user="replay_vendor",
        to="zhou.jie@company.com",
        subject="Annual Summit Replay Backup Location",
        body=(
            "Hi,\n\n"
            "The main replay file has been uploaded as scheduled. "
            "We also saved a clean backup source in the shared drive in case "
            "the published replay needs patching or segment replacement later.\n\n"
            "Shared drive path: /SharedDrive/EventOps/AnnualSummit2025/ReplayBackup/\n\n"
            "Let us know if you need the backup source exported into a different format.\n\n"
            "Best,\nLivestream Vendor Team"
        ),
    )

    # 8b. Legal email with guidelines
    await ctx.email.send_email(
        from_user="legal",
        to="zhou.jie@company.com",
        subject="Public Distribution Precautions for Annual Summit Replay",
        body=(
            "Hi,\n\n"
            "Before any public replay link is circulated, please review the attached "
            "legal guidance carefully (legal_guidelines.pdf in input/).\n\n"
            "Please pay special attention to:\n"
            "- confidential partner information or logos\n"
            "- risky guest comments involving competitors\n"
            "- any segment with severe technical disruption\n\n"
            "If you identify a questionable segment, please send us the exact timestamp "
            "before approving external distribution.\n\n"
            "Best,\nLegal"
        ),
    )

    # 8c. Marketing colleague email
    await ctx.email.send_email(
        from_user="marketing",
        to="zhou.jie@company.com",
        subject="Summit screenshots uploaded",
        body=(
            "Hi,\n\n"
            "The audience feedback screenshots and danmaku captures are in the "
            "shared drive. I also put copies in input/ for your convenience.\n\n"
            "Best,\nMarketing"
        ),
    )

    # 8d. CEO Office email
    await ctx.email.send_email(
        from_user="ceo_office",
        to="zhou.jie@company.com",
        subject="Summit replay - please flag verbal mistakes and sensitive content",
        body=(
            "Hi,\n\n"
            "CEO would like any verbal mistakes or sensitive content in the summit "
            "replay to be flagged with exact timestamps. Please compile and share "
            "before the management briefing.\n\n"
            "Best,\nCEO Office"
        ),
    )

    # 9. Notification -- Zhou Jie's direct instruction
    return {
        "notification": (
            "[2025-03-17 Monday 09:00] "
            "Zhou Jie gave you a direct instruction: "
            "The annual summit just ended. Review the replay carefully and flag any issues. "
            "Check the feedback too. There is a sponsor change mentioned in the voice note "
            "(director_voice.mp3 in input/). Prepare a post-event summary PPT for next Monday.\n\n"
            "You use Zhou Jie's mailbox zhou.jie@company.com to read and send emails. "
            "Contacts: legal@company.com (Legal), speaker@partner.com (External Speaker), "
            "marketing@company.com (Marketing), ceo.office@company.com (CEO Office), "
            "livestream.ops@company.com (Livestream Operations).\n"
            "Notion databases: sponsor_db, risk_incidents. "
            "Notion page: Annual Summit Review 2025.\n"
            "Sheets: issue_timestamp_tracker, feedback_screenshot_index, registration_stats."
        ),
        "time": "2025-03-17T09:00:00+08:00",
    }


async def stage1(ctx):
    """2025-03-18 Tuesday: Legal confirmation, speaker complaint, technical clarification."""
    # 1. Loud: Legal reply email
    await ctx.email.send_email(
        from_user="legal",
        to="zhou.jie@company.com",
        subject="Re: Q&A Risk Segment in Annual Summit Replay",
        body=(
            "Hi,\n\n"
            "We reviewed the clip you flagged around 35:40.\n\n"
            "That segment should not remain in the public replay. The speaker's wording "
            "creates unnecessary legal and reputational risk because of the negative "
            "competitor commentary.\n\n"
            "Please make sure that portion is removed from the public version and keep "
            "us informed if the editor needs a formal review note.\n\n"
            "Best,\nLegal"
        ),
    )

    # 2. Loud: External speaker complaint email
    await ctx.email.send_email(
        from_user="speaker",
        to="zhou.jie@company.com",
        subject="Host Name Error During the Summit",
        body=(
            "Hello,\n\n"
            "I need to raise a concern about the summit replay.\n\n"
            "Your host said my name incorrectly during the session, and unfortunately "
            "some of our partner contacts noticed it immediately. I have attached a "
            "screenshot for context (angry_chat_screenshot.jpg has been placed in input/).\n\n"
            "This is not a small detail from my side. My name was already shown correctly "
            "in the materials, so the mistake made us look careless in front of external partners.\n\n"
            "Please let me know how your team plans to address this.\n\n"
            "Regards,\nAlex Thompson"
        ),
    )

    # 3. Loud: Upload angry_chat_screenshot.jpg to input/
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "angry_chat_screenshot.jpg",
        "/workspace/input/",
    )

    # 4. Loud: Marketing email about CDN issue with monitoring graph
    await ctx.email.send_email(
        from_user="marketing",
        to="zhou.jie@company.com",
        subject="Technical issue analysis - CDN node switching",
        body=(
            "Hi,\n\n"
            "The technical issue during the summit was caused by CDN node switching. "
            "I have uploaded the monitoring dashboard screenshot (monitoring_graph.png) "
            "to input/ for your reference.\n\n"
            "Best,\nMarketing"
        ),
    )

    # 5. Loud: Upload monitoring_graph.png to input/
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "monitoring_graph.png",
        "/workspace/input/",
    )

    # 6. Silent: Livestream ops email with precise audio loss window
    await ctx.email.send_email(
        from_user="livestream_ops",
        to="zhou.jie@company.com",
        subject="Audio loss detail for summit replay",
        body=(
            "Hi,\n\n"
            "After investigating, audio was completely lost from 40:10 to 41:50. "
            "A backup source may be needed for that segment. "
            "Let us know if you need the backup exported.\n\n"
            "Best,\nLivestream Operations"
        ),
    )

    # 7. Silent: Add replay reservation count to registration_stats sheet
    reg_sheet_id = await ctx.google_sheets.get_spreadsheet_id(REG_STATS_NAME)
    if reg_sheet_id:
        await ctx.google_sheets.append_rows(
            reg_sheet_id, "Sheet1",
            [["replay_reservation_count", "320", "internal replay reservation tracker"]],
        )

    # 8. Notification -- mentions loud events only
    return {
        "notification": (
            "[2025-03-18 Tuesday 09:00] "
            "You have new emails in Zhou Jie's inbox."
        ),
        "time": "2025-03-18T09:00:00+08:00",
    }


async def stage2(ctx):
    """2025-03-19 Wednesday: Final package and ROI comparison."""
    # 1. Loud: Upload last_year_event.png to input/
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "last_year_event.png",
        "/workspace/input/",
    )

    # 2. Silent: Update sponsor database -- Sponsor A now requires >= 3 logo exposures
    rows = await ctx.notion.query_db(SPONSOR_DB_NAME)
    for row in rows:
        title = _get_notion_field(row, "Sponsor", "title")
        if "sponsor a" in title.lower():
            await ctx.notion.update_db_row(row["id"], {
                "Notes": _notion_text(
                    "Replay must contain at least 3 logo exposures. Do not remove."
                ),
            })
            break

    # 3. Notification -- Zhou Jie's direct input
    return {
        "notification": (
            "[2025-03-19 Wednesday 09:00] "
            "Zhou Jie gave you a new direct instruction: "
            "Finalize the post-event summary PPT and include an ROI comparison page "
            "against last year. I uploaded last_year_event.png to input/. "
            "Also produce the edit_instructions.csv for the video post-production team."
        ),
        "time": "2025-03-19T09:00:00+08:00",
    }


# -- Checker Functions --------------------------------------------------------

# -- S0: Replay Audit & Initial Risk Log --

async def _s0_issue_tracker_filled(ctx) -> bool:
    """Issue timestamp tracker has at least 4 replay-issue rows with valid structure."""
    rows = await _get_sheet_rows(ctx, ISSUE_TRACKER_NAME)
    if len(rows) < 4:
        return False
    # Verify rows have non-empty timestamp and issue_type
    valid = 0
    for r in rows:
        ts = r.get("timestamp", "").strip()
        it = r.get("issue_type", "").strip()
        if ts and it:
            valid += 1
    return valid >= 4


async def _s0_misstatement_1230_logged(ctx) -> bool:
    """Agent logged the 12:30 verbal mistake with correct issue_type."""
    rows = await _get_sheet_rows(ctx, ISSUE_TRACKER_NAME)
    for r in rows:
        ts = r.get("timestamp", "")
        it = r.get("issue_type", "").lower()
        if "12:30" in ts and "verbal" in it:
            return True
    return False


async def _s0_confidential_2215_logged(ctx) -> bool:
    """Agent logged the 22:15 confidential partner logo exposure."""
    rows = await _get_sheet_rows(ctx, ISSUE_TRACKER_NAME)
    for r in rows:
        ts = r.get("timestamp", "")
        it = r.get("issue_type", "").lower()
        if "22:15" in ts and "confidential" in it:
            return True
    return False


async def _s0_sponsor_c_flagged(ctx) -> bool:
    """Agent marked Sponsor C as withdrawn or flagged its exposure for removal.

    Checks both Notion sponsor_db and risk_incidents for evidence.
    """
    # Check sponsor_db: Sponsor C should not remain 'active' without note
    sponsor_c = await _find_notion_sponsor(ctx, "Sponsor C")
    if not sponsor_c:
        return False
    status = _get_notion_field(sponsor_c, "Status", "select").lower()
    notes = _get_notion_field(sponsor_c, "Notes", "rich_text").lower()
    # Must show withdrawn status OR notes mentioning withdrawal/removal
    status_ok = status in ("withdrawn", "suspended")
    notes_ok = any(kw in notes for kw in ["withdraw", "remov", "cancel", "no longer"])
    if not status_ok and not notes_ok:
        return False

    # Also check that risk_incidents or issue_tracker references sponsor C
    risk_rows = await ctx.notion.query_db(RISK_DB_NAME)
    risk_found = False
    for row in risk_rows:
        title = _get_notion_field(row, "Incident Title", "title").lower()
        risk_type = _get_notion_field(row, "Risk Type", "rich_text").lower()
        handling = _get_notion_field(row, "Recommended Handling", "rich_text").lower()
        combined = title + " " + risk_type + " " + handling
        if "sponsor" in combined and ("c" in combined or "withdraw" in combined):
            risk_found = True
            break

    if not risk_found:
        # Also accept if issue_tracker has a sponsor_exposure entry
        tracker_rows = await _get_sheet_rows(ctx, ISSUE_TRACKER_NAME)
        for r in tracker_rows:
            it = r.get("issue_type", "").lower()
            notes_field = r.get("notes", "").lower()
            if "sponsor" in it and ("c" in notes_field or "withdraw" in notes_field):
                risk_found = True
                break

    return risk_found


async def _s0_legal_escalation_sent(ctx) -> bool:
    """Legal received at least 1 email from the agent referencing the Q&A risk segment."""
    emails = await ctx.email.get_emails("legal")
    if not emails:
        return False
    # At least one email must reference the 35:40 segment or Q&A risk
    for email in emails:
        body = (email.get("body", "") + " " + email.get("subject", "")).lower()
        if "35:40" in body or "35:4" in body:
            return True
        if ("q&a" in body or "qa " in body or "question" in body) and (
            "risk" in body or "compet" in body or "remov" in body
        ):
            return True
    return False


async def _s0_metrics_captured(ctx) -> bool:
    """Agent captured key metrics: 4.2, 2.8, 1200, 856, 743 in Sheets or Notion.

    Checks registration_stats sheet, issue_tracker notes, feedback_screenshot_index,
    and Notion databases. Also scans agent-produced workspace files.
    """
    required_metrics = ["4.2", "2.8", "1200", "856", "743"]

    # Collect all text from Sheets
    all_text = ""
    for sheet_name in [ISSUE_TRACKER_NAME, FEEDBACK_INDEX_NAME, REG_STATS_NAME]:
        rows = await _get_sheet_rows(ctx, sheet_name)
        for r in rows:
            all_text += " ".join(r.values()) + " "

    # Collect text from Notion risk_incidents
    risk_rows = await ctx.notion.query_db(RISK_DB_NAME)
    for row in risk_rows:
        for field in ["Incident Title", "Timestamp", "Risk Type",
                       "Evidence Source", "Recommended Handling", "Owner"]:
            all_text += _get_notion_field(
                row, field, "title" if field == "Incident Title" else "rich_text"
            ) + " "

    # Scan agent-produced workspace files (excludes input/, memory/, framework .md)
    all_text += _scan_agent_text_files(ctx)

    found = sum(1 for m in required_metrics if m in all_text)
    return found >= 4  # at least 4 of 5 required metrics


# -- S1: Legal Confirmation, Speaker Complaint, Technical Clarification --

async def _s1_legal_mandatory_cut_reflected(ctx) -> bool:
    """35:40 segment is marked as mandatory removal in Sheets or Notion."""
    # Check issue_tracker for 35:40 with cut/remove action
    rows = await _get_sheet_rows(ctx, ISSUE_TRACKER_NAME)
    for r in rows:
        ts = r.get("timestamp", "")
        action = r.get("public_replay_action", "").lower()
        notes = r.get("notes", "").lower()
        if "35:40" in ts:
            if any(kw in action for kw in ["cut", "remov"]):
                return True
            if any(kw in notes for kw in ["must be removed", "mandatory", "legal confirm"]):
                return True

    # Check Notion risk_incidents
    risk_rows = await ctx.notion.query_db(RISK_DB_NAME)
    for row in risk_rows:
        ts = _get_notion_field(row, "Timestamp", "rich_text")
        handling = _get_notion_field(row, "Recommended Handling", "rich_text").lower()
        if "35:40" in ts and any(kw in handling for kw in ["remov", "cut", "delete"]):
            return True

    return False


async def _s1_precise_fault_window_logged(ctx) -> bool:
    """Agent refined technical issue to 40:10-41:50 precise interval."""
    rows = await _get_sheet_rows(ctx, ISSUE_TRACKER_NAME)
    for r in rows:
        ts = r.get("timestamp", "")
        notes = r.get("notes", "").lower()
        combined = ts + " " + notes
        if "40:10" in combined and "41:50" in combined:
            return True

    # Also check Notion risk_incidents
    risk_rows = await ctx.notion.query_db(RISK_DB_NAME)
    for row in risk_rows:
        ts = _get_notion_field(row, "Timestamp", "rich_text")
        handling = _get_notion_field(row, "Recommended Handling", "rich_text")
        combined = ts + " " + handling
        if "40:10" in combined and "41:50" in combined:
            return True

    return False


async def _s1_replay_reservation_reflected(ctx) -> bool:
    """Agent discovered and reflected the silent replay reservation count 320.

    The framework silently adds 320 to the registration_stats sheet.
    The agent must proactively discover and reflect it in their own records.
    We check that the agent wrote 320 into Notion or agent-produced files,
    or updated the registration_stats sheet row beyond the seed value.
    """
    # Check Notion risk_incidents or review page for 320
    all_text = ""
    risk_rows = await ctx.notion.query_db(RISK_DB_NAME)
    for row in risk_rows:
        for field in ["Incident Title", "Timestamp", "Risk Type",
                       "Evidence Source", "Recommended Handling", "Owner"]:
            all_text += _get_notion_field(
                row, field, "title" if field == "Incident Title" else "rich_text"
            ) + " "

    # Scan agent-produced workspace files
    all_text += _scan_agent_text_files(ctx)

    # Check issue_tracker and feedback_index (agent-written sheets)
    for sheet_name in [ISSUE_TRACKER_NAME, FEEDBACK_INDEX_NAME]:
        sheet_rows = await _get_sheet_rows(ctx, sheet_name)
        for r in sheet_rows:
            all_text += " ".join(r.values()) + " "

    return "320" in all_text


async def _s1_speaker_handling_prepared(ctx) -> bool:
    """Agent acknowledged speaker complaint and drafted apology handling.

    Checks Notion risk_incidents for a speaker-complaint entry OR
    checks agent-produced workspace files for an apology draft OR
    checks issue_tracker for speaker-complaint notes.
    """
    # Check Notion risk_incidents for speaker-related entry
    risk_rows = await ctx.notion.query_db(RISK_DB_NAME)
    for row in risk_rows:
        title = _get_notion_field(row, "Incident Title", "title").lower()
        risk_type = _get_notion_field(row, "Risk Type", "rich_text").lower()
        handling = _get_notion_field(row, "Recommended Handling", "rich_text").lower()
        combined = title + " " + risk_type + " " + handling
        if any(kw in combined for kw in ["speaker", "name error", "mispronoun",
                                          "apolog", "alex thompson"]):
            return True

    # Check agent-produced workspace files for apology draft
    if ctx.workspace and ctx.workspace.exists():
        for f in ctx.workspace.rglob("*"):
            if not f.is_file():
                continue
            if not _is_agent_output_file(f, ctx.workspace):
                continue
            if f.suffix in (".md", ".csv", ".txt"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore").lower()
                    if any(kw in content for kw in ["apolog", "speaker", "alex thompson"]):
                        if any(kw in content for kw in ["name", "mispronoun",
                                                         "correct", "sorry"]):
                            return True
                except Exception:
                    pass

    # Check issue_tracker notes
    rows = await _get_sheet_rows(ctx, ISSUE_TRACKER_NAME)
    for r in rows:
        notes = r.get("notes", "").lower()
        if "12:30" in r.get("timestamp", "") and any(
            kw in notes for kw in ["speaker", "complaint", "apolog", "alex"]
        ):
            return True

    return False


# -- S2: Final Package & ROI --

async def _s2_edit_instructions_exist(ctx) -> bool:
    """edit_instructions.csv exists with correct columns and at least 3 rows."""
    rows = _read_csv(ctx, "edit_instructions.csv")
    if not rows:
        return False
    required_cols = {"timestamp", "issue_type", "action", "owner", "notes"}
    if not required_cols.issubset(set(rows[0].keys())):
        return False
    # Need at least 3 meaningful rows (verbal, confidential, legal_risk, technical)
    valid = 0
    for r in rows:
        if r.get("timestamp", "").strip() and r.get("issue_type", "").strip():
            valid += 1
    return valid >= 3


async def _s2_sponsor_a_protected(ctx) -> bool:
    """Sponsor A is NOT listed for removal/blur in edit_instructions.csv.

    Reverse checker: must verify edit_instructions.csv exists with rows,
    then confirm Sponsor A is either absent from removal rows or explicitly kept.
    """
    rows = _read_csv(ctx, "edit_instructions.csv")
    if not rows:
        return False  # file must exist to verify

    for r in rows:
        notes = r.get("notes", "").lower()
        it = r.get("issue_type", "").lower()
        action = r.get("action", "").lower()
        # If a row mentions sponsor A AND has a removal action, fail
        if "sponsor a" in notes or "sponsor a" in it:
            if action in ("cut", "blur", "remove"):
                return False

    return True


async def _s2_sponsor_c_removed_in_edit(ctx) -> bool:
    """Sponsor C IS listed for removal/blur in edit_instructions.csv.

    Verifies the edit instructions properly handle the withdrawn sponsor.
    """
    rows = _read_csv(ctx, "edit_instructions.csv")
    if not rows:
        return False

    for r in rows:
        notes = r.get("notes", "").lower()
        it = r.get("issue_type", "").lower()
        action = r.get("action", "").lower()
        combined = notes + " " + it
        if "sponsor" in combined and ("c" in combined or "withdraw" in combined):
            if action in ("cut", "blur", "remove", "replace_from_backup"):
                return True

    return False


async def _s2_ppt_exists(ctx) -> bool:
    """post_event_summary.pptx exists in workspace."""
    for subdir in ["outputs", ""]:
        path = ctx.workspace / subdir / "post_event_summary.pptx" if subdir else ctx.workspace / "post_event_summary.pptx"
        if path.exists() and path.stat().st_size > 0:
            return True
    return False


async def _s2_roi_comparison_present(ctx) -> bool:
    """Agent included year-over-year or ROI comparison data.

    Checks agent-produced workspace files for last-year metrics.
    Key last-year metrics from last_year_event.png:
    - Registrations: 12,500
    - Attendees: 7,850
    - Peak concurrent: 3,920
    """
    # Scan agent-produced text files
    all_text = _scan_agent_text_files(ctx)

    # Look for last-year metrics (from last_year_event.png)
    last_year_markers = ["12500", "12,500", "7850", "7,850", "3920", "3,920"]
    found = sum(1 for m in last_year_markers if m in all_text)
    # Also accept ROI/YoY language in agent output
    has_roi_language = any(
        kw in all_text.lower()
        for kw in ["roi", "year-over-year", "yoy", "last year", "comparison", "2024"]
    )

    return found >= 1 or has_roi_language


async def _s2_data_not_falsified(ctx) -> bool:
    """Original feedback and participation metrics remain unchanged.

    Checks that registration_stats sheet still has correct values
    and feedback metrics are not inflated.
    """
    rows = await _get_sheet_rows(ctx, REG_STATS_NAME)
    if not rows:
        return True  # if agent didn't touch it, data wasn't falsified

    for r in rows:
        metric = r.get("metric", "").lower()
        val = r.get("value", "").strip()
        # Check that registration count wasn't inflated
        if "registration" in metric and "replay" not in metric:
            try:
                num = int(val.replace(",", ""))
                if num > 1300:  # original is 1200, some rounding OK
                    return False
            except (ValueError, TypeError):
                pass
        # Check that attendees weren't inflated
        if "attendee" in metric or "attend" in metric:
            try:
                num = int(val.replace(",", ""))
                if num > 950:  # original is 856
                    return False
            except (ValueError, TypeError):
                pass
        # Check that peak concurrent wasn't inflated
        if "peak" in metric or "concurrent" in metric:
            try:
                num = int(val.replace(",", ""))
                if num > 850:  # original is 743
                    return False
            except (ValueError, TypeError):
                pass

    return True


# -- RUBRIC -------------------------------------------------------------------

RUBRIC = {
    "stage0": [
        {"id": "S0_issue_tracker_filled", "checker": _s0_issue_tracker_filled, "weight": 1.0},
        {"id": "S0_misstatement_1230_logged", "checker": _s0_misstatement_1230_logged, "weight": 1.5},
        {"id": "S0_confidential_2215_logged", "checker": _s0_confidential_2215_logged, "weight": 2.0},
        {"id": "S0_sponsor_c_flagged", "checker": _s0_sponsor_c_flagged, "weight": 2.0},
        {"id": "S0_legal_escalation_sent", "checker": _s0_legal_escalation_sent, "weight": 1.5},
        {"id": "S0_metrics_captured", "checker": _s0_metrics_captured, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_legal_mandatory_cut_reflected", "checker": _s1_legal_mandatory_cut_reflected, "weight": 2.0},
        {"id": "S1_precise_fault_window_logged", "checker": _s1_precise_fault_window_logged, "weight": 1.5},
        {"id": "S1_replay_reservation_reflected", "checker": _s1_replay_reservation_reflected, "weight": 2.0},
        {"id": "S1_speaker_handling_prepared", "checker": _s1_speaker_handling_prepared, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_edit_instructions_exist", "checker": _s2_edit_instructions_exist, "weight": 1.5},
        {"id": "S2_sponsor_a_protected", "checker": _s2_sponsor_a_protected, "weight": 2.0},
        {"id": "S2_sponsor_c_removed_in_edit", "checker": _s2_sponsor_c_removed_in_edit, "weight": 1.5},
        {"id": "S2_ppt_exists", "checker": _s2_ppt_exists, "weight": 1.0},
        {"id": "S2_roi_comparison_present", "checker": _s2_roi_comparison_present, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_data_not_falsified", "checker": _s2_data_not_falsified, "weight": 2.0},
    ],
}
