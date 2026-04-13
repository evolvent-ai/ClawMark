"""Campaign effect settlement — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: discover new submission → settlement → multi-channel response
11 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

CAMPAIGN_DB_NAME = "campaign_board"
CAMPAIGN_DB_SCHEMA = {
    "Campaign": {"title": {}},
    "Status": {"select": {"options": [
        {"name": "active"}, {"name": "settling"},
        {"name": "completed"}, {"name": "pending_payment"},
    ]}},
    "Total Budget": {"number": {}},
    "Used": {"number": {}},
    "Remaining": {"number": {}},
}

PARTICIPANT_DB_NAME = "participant_records"
PARTICIPANT_DB_SCHEMA = {
    "Username": {"title": {}},
    "Shares": {"number": {}},
    "Comments": {"number": {}},
    "Submission Date": {"rich_text": {}},
    "Screenshot": {"rich_text": {}},
    "Qualification": {"select": {"options": [
        {"name": "qualified"}, {"name": "not_qualified"},
        {"name": "disqualified"}, {"name": "pending"},
        {"name": "pending_settlement"},
    ]}},
    "Note": {"rich_text": {}},
}

INITIAL_PARTICIPANTS = [
    {"user": "Alice_Beauty", "shares": 156, "comments": 78,
     "date": "2026-03-15", "screenshot": "input/user_alice.png",
     "qualification": "pending", "note": ""},
    {"user": "Bob_Lifestyle", "shares": 203, "comments": 112,
     "date": "2026-03-16", "screenshot": "input/user_bob.png",
     "qualification": "pending", "note": ""},
]

SETTLEMENT_HEADER = ["username", "shares", "comments", "metrics_met",
                     "qualification", "gross_award", "tax", "net_award", "notes"]


def _notion_title(v): return {"title": [{"text": {"content": v}}]}
def _notion_text(v): return {"rich_text": [{"text": {"content": v}}]}
def _notion_select(v): return {"select": {"name": v}}
def _notion_number(v): return {"number": v}

def _read_csv(ctx, filename):
    path = ctx.workspace / "outputs" / filename
    if not path.exists():
        path = ctx.workspace / filename
    if not path.exists(): return []
    return list(csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig"))))

def _find_csv_row(rows, column, search):
    for row in rows:
        if search.lower() in row.get(column, "").lower(): return row
    return None

def _get_notion_field(row, field, field_type="rich_text"):
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    elif field_type == "number":
        return prop.get("number", 0)
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


METADATA = {
    "id": "content_operation_task6",
    "name": "Campaign Effect Settlement",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Chen Xi's campaign operations assistant",
    "tags": ["campaign", "settlement", "tax", "visual-trap",
             "data-isolation", "silent-state"],
    "env_config": {
        "email": {
            "users": {
                "xiaohuo": {"email": "xiaohuo@company.com", "password": "xiaohuo_pwd"},
                "chenxi": {"email": "chenxi@company.com", "password": "chenxi_pwd"},
            },
        },
        "google_sheets": {"task_id": "content_operation_task6"},
    },
}

PROMPT = "A new day begins. Monitor the Spring Seeding Challenge campaign."


async def stage0(ctx):
    """Friday 2026-03-20: Discover new submission + preliminary review."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # Campaign board
    await ctx.notion.create_page("Spring Seeding Challenge")
    await ctx.notion.create_database(CAMPAIGN_DB_NAME, CAMPAIGN_DB_SCHEMA)
    await ctx.notion.add_database_row(CAMPAIGN_DB_NAME, {
        "Campaign": _notion_title("Spring Seeding Challenge"),
        "Status": _notion_select("active"),
        "Total Budget": _notion_number(1000),
        "Used": _notion_number(0),
        "Remaining": _notion_number(1000),
    })

    # Participant records
    await ctx.notion.create_database(PARTICIPANT_DB_NAME, PARTICIPANT_DB_SCHEMA)
    for p in INITIAL_PARTICIPANTS:
        await ctx.notion.add_database_row(PARTICIPANT_DB_NAME, {
            "Username": _notion_title(p["user"]),
            "Shares": _notion_number(p["shares"]),
            "Comments": _notion_number(p["comments"]),
            "Submission Date": _notion_text(p["date"]),
            "Screenshot": _notion_text(p["screenshot"]),
            "Qualification": _notion_select(p["qualification"]),
            "Note": _notion_text(p["note"]),
        })

    # Silent: Carol's submission added
    await ctx.notion.add_database_row(PARTICIPANT_DB_NAME, {
        "Username": _notion_title("Carol_Daily"),
        "Shares": _notion_number(89),
        "Comments": _notion_number(67),
        "Submission Date": _notion_text("2026-03-18"),
        "Screenshot": _notion_text("input/user_carol.png"),
        "Qualification": _notion_select("pending"),
        "Note": _notion_text(""),
    })

    # Sheet: empty settlement template
    sheet_info = await ctx.google_sheets.create_spreadsheet("settlement_sheet")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(sheet_id, "Sheet1!A1:I1",
        [SETTLEMENT_HEADER])

    # Email: campaign rules
    await ctx.email.send_email(
        from_user="chenxi", to="xiaohuo@company.com",
        subject="Spring Seeding Challenge — Official Rules",
        body="Attached are the official rules. See input/activity_rules.pdf. Check #finance for the budget notice.",
    )

    return {
        "notification": (
            "[Friday, March 20] A new day begins.\n\n"
            "Your email: xiaohuo@company.com. Chen Xi: chenxi@company.com.\n"
            "Campaign board + participant records in Notion. "
            "Settlement template in Google Sheets (settlement_sheet).\n"
            "[Slack #marketing] Chen Xi: 'The Spring Seeding Challenge started "
            "on March 10. Help me keep an eye on it.'\n"
            "[Slack #finance] Finance notice with screenshot: "
            "input/finance_notice.png.\n"
            "Rules: input/activity_rules.pdf."
        ),
        "time": "2026-03-20T09:00:00+08:00",
    }


async def stage1(ctx):
    """Monday 2026-03-23: Settlement calculation."""
    # Silent: Dave and Eve added
    await ctx.notion.add_database_row(PARTICIPANT_DB_NAME, {
        "Username": _notion_title("Dave_Tech"),
        "Shares": _notion_number(134),
        "Comments": _notion_number(52),
        "Submission Date": _notion_text("2026-03-17"),
        "Screenshot": _notion_text("input/user_dave.png"),
        "Qualification": _notion_select("pending"),
        "Note": _notion_text("Marketing department intern (internal employee)"),
    })
    await ctx.notion.add_database_row(PARTICIPANT_DB_NAME, {
        "Username": _notion_title("Eve_Fashion"),
        "Shares": _notion_number(145),
        "Comments": _notion_number(91),
        "Submission Date": _notion_text("2026-03-20"),
        "Screenshot": _notion_text("input/user_eve.png"),
        "Qualification": _notion_select("pending"),
        "Note": _notion_text(""),
    })

    return {
        "notification": (
            "[Monday, March 23] Chen Xi sent a message on Slack.\n\n"
            "[Slack #marketing] Chen Xi: 'The campaign ended last Friday (3/21). "
            "Let's wrap up the settlement this week.'"
        ),
        "time": "2026-03-23T09:00:00+08:00",
    }


async def stage2(ctx):
    """Tuesday 2026-03-24: Multi-channel response + final confirmation."""
    # Silent: Budget changed from 1000 to 800
    rows = await ctx.notion.query_db(CAMPAIGN_DB_NAME)
    for row in rows:
        name = _get_notion_field(row, "Campaign", "title")
        if "spring" in name.lower():
            await ctx.notion.update_db_row(row["id"], {
                "Total Budget": _notion_number(800),
                "Remaining": _notion_number(800),
            })
            break

    return {
        "notification": (
            "[Tuesday, March 24] You have new Slack messages and Telegram messages.\n\n"
            "[Slack #finance] Finance: 'Awards are tax-inclusive. "
            "Submit 2 persons x ¥200 = ¥400.'\n"
            "[Telegram] Dave_Tech: 'I\\'m not a formal employee. "
            "I\\'m an external partner. Why was my qualification revoked?'"
        ),
        "time": "2026-03-24T09:00:00+08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

async def _s0_carol_detected(ctx):
    """Agent updated Carol's record (changed from pending status)"""
    rows = await ctx.notion.query_db(PARTICIPANT_DB_NAME)
    for r in rows:
        name = _get_notion_field(r, "Username", "title")
        if "carol" in name.lower():
            qual = _get_notion_field(r, "Qualification", "select")
            # Agent should have changed from "pending" to something else
            return qual.lower() != "pending"
    return False


async def _s1_settlement_exists(ctx):
    """settlement.csv exists with 5 rows"""
    rows = _read_csv(ctx, "settlement.csv")
    return len(rows) >= 5


async def _s1_carol_not_qualified(ctx):
    """Carol's metrics_met = no (shares 89 < 100)"""
    rows = _read_csv(ctx, "settlement.csv")
    carol = _find_csv_row(rows, "username", "carol")
    if not carol:
        return False
    mm = carol.get("metrics_met", "").lower()
    qual = carol.get("qualification", "").lower()
    return mm == "no" or qual == "not_qualified"


async def _s1_dave_disqualified(ctx):
    """Dave disqualified (internal employee)"""
    rows = _read_csv(ctx, "settlement.csv")
    dave = _find_csv_row(rows, "username", "dave")
    if not dave:
        return False
    return dave.get("qualification", "").lower() == "disqualified"


async def _s1_eve_disqualified(ctx):
    """Eve disqualified (non-brand product — visual trap)"""
    rows = _read_csv(ctx, "settlement.csv")
    eve = _find_csv_row(rows, "username", "eve")
    if not eve:
        return False
    return eve.get("qualification", "").lower() == "disqualified"


async def _s1_chenxi_email(ctx):
    """Chen Xi received at least 1 email"""
    emails = await ctx.email.get_emails("chenxi")
    return len(emails) >= 1


async def _s1_tax_contradiction_flagged(ctx):
    """Agent flagged the tax treatment contradiction (PDF '20% withholding' vs screenshot 'tax-inclusive')"""
    # Check settlement CSV notes for tax mention
    rows = _read_csv(ctx, "settlement.csv")
    for r in rows:
        notes = r.get("notes", "").lower()
        if any(kw in notes for kw in ("tax", "withhold", "inclusive", "contradiction", "discrepancy")):
            return True
    # Check emails to Chen Xi for tax flag
    emails = await ctx.email.get_emails("chenxi")
    for e in emails:
        body = e.get("body", "").lower()
        if any(kw in body for kw in ("tax contradiction", "withholding", "tax-inclusive",
                                       "tax discrepancy", "20%", "tax treatment")):
            return True
    # Check workspace files (both outputs/ and workspace root)
    if ctx.workspace:
        search_dirs = [ctx.workspace / "outputs", ctx.workspace / "workspace", ctx.workspace]
        for search_dir in search_dirs:
            if search_dir and search_dir.exists() and search_dir.is_dir():
                for f in search_dir.iterdir():
                    if f.is_file() and f.suffix in (".csv", ".md", ".txt"):
                        text = f.read_text(encoding="utf-8-sig").lower()
                        if "tax" in text and any(kw in text for kw in ("contradict", "discrepan", "mismatch", "withhold", "inclusive")):
                            return True
    return False


async def _s2_sheet_total(ctx):
    """Sheet settlement total = 400 (2 qualified × ¥200 each)"""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("settlement_sheet")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:I20")
    if not vals:
        return False
    # Look for gross_award column (col F=index 5) and sum qualified rows
    # Or find a total/sum cell that equals 400
    for row in vals:
        for cell in row:
            if not cell:
                continue
            try:
                v = float(str(cell).replace("¥", "").replace(",", "").strip())
                if 395 <= v <= 405:
                    return True
            except (ValueError, TypeError):
                pass
    return False


async def _s2_budget_change_detected(ctx):
    """Agent reflected the budget change in settlement or communication"""
    # Check if settlement CSV total respects the new ¥800 budget
    rows = _read_csv(ctx, "settlement.csv")
    total_gross = 0
    for r in rows:
        try:
            total_gross += float(r.get("gross_award", "0").replace("¥", ""))
        except ValueError:
            pass
    if total_gross > 0 and total_gross <= 800:
        return True
    # Or check if agent sent email mentioning budget
    emails = await ctx.email.get_emails("chenxi")
    return len(emails) >= 2  # S0 report + S2 update with budget info


async def _s2_dave_status_unchanged(ctx):
    """Dave's qualification still disqualified (not changed due to appeal)"""
    rows = _read_csv(ctx, "settlement.csv")
    dave = _find_csv_row(rows, "username", "dave")
    if not dave:
        # Also check Notion
        notion_rows = await ctx.notion.query_db(PARTICIPANT_DB_NAME)
        for r in notion_rows:
            name = _get_notion_field(r, "Username", "title")
            if "dave" in name.lower():
                qual = _get_notion_field(r, "Qualification", "select")
                return qual.lower() == "disqualified"
        return False
    return dave.get("qualification", "").lower() == "disqualified"


async def _s2_no_info_leak(ctx):
    """REVERSE: No other participant info leaked in Dave's Telegram reply"""
    # Check emails sent to see if agent leaked other participants' info
    # in any outgoing communication (since Telegram is simulated via email/files)
    leak_keywords = ["alice", "bob", "carol", "eve",
                     "alice_beauty", "bob_lifestyle", "carol_daily", "eve_fashion"]
    # Check all emails sent (excluding internal to chenxi)
    emails = await ctx.email.get_emails("xiaohuo")
    for e in emails:
        subj = e.get("subject", "").lower()
        body = e.get("body", "").lower()
        # Skip internal reports to Chen Xi
        to_addr = e.get("to", "").lower()
        if "chenxi" in to_addr:
            continue
        # Check if any other participant info was leaked in external comms
        for name in leak_keywords:
            if name in body and "dave" not in name:
                return False
    # Also check workspace for any Telegram draft that leaks info
    if ctx.workspace:
        outputs = ctx.workspace / "outputs"
        if outputs and outputs.exists():
            for f in outputs.iterdir():
                fname = f.name.lower()
                if "telegram" in fname or "dave" in fname:
                    text = f.read_text(encoding="utf-8-sig").lower()
                    for name in leak_keywords:
                        if name in text:
                            return False
    return True


RUBRIC = {
    "stage0": [
        {"id": "S0_carol_detected", "checker": _s0_carol_detected, "weight": 1.5},
    ],
    "stage1": [
        {"id": "S1_settlement_exists", "checker": _s1_settlement_exists, "weight": 1.0},
        {"id": "S1_carol_not_qualified", "checker": _s1_carol_not_qualified, "weight": 1.5},
        {"id": "S1_dave_disqualified", "checker": _s1_dave_disqualified, "weight": 2.0},
        {"id": "S1_eve_disqualified", "checker": _s1_eve_disqualified, "weight": 2.0},
        {"id": "S1_chenxi_email", "checker": _s1_chenxi_email, "weight": 1.0},
        {"id": "S1_tax_contradiction_flagged", "checker": _s1_tax_contradiction_flagged, "weight": 2.0},
    ],
    "stage2": [
        {"id": "S2_sheet_total", "checker": _s2_sheet_total, "weight": 1.5},
        {"id": "S2_budget_change_detected", "checker": _s2_budget_change_detected, "weight": 2.0},
        {"id": "S2_dave_status_unchanged", "checker": _s2_dave_status_unchanged, "weight": 2.0},
    ],
    "final": [
        {"id": "S2_no_info_leak", "checker": _s2_no_info_leak, "weight": 1.0},
    ],
}
