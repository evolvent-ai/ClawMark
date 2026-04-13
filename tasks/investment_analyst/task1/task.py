"""JPMorgan Chase 1Q24 — basis separation, outlook cross-check, silent peer monitor.

Environments: filesystem, email, notion, google_sheets
3 stages: initial read → follow-up + silent LP question → overnight peer framing
18 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

WATCHLIST_DB = "JPM_watchlist"
LP_QUESTIONS_DB = "LP_questions"

WATCHLIST_DB_SCHEMA = {
    "company": {"title": {}},
    "reported_net_income": {"rich_text": {}},
    "adjusted_net_income": {"rich_text": {}},
    "difference_driver": {"rich_text": {}},
    "fy24_nii_ex_markets": {"rich_text": {}},
    "street_view": {"rich_text": {}},
    "lp_followup_answer": {"rich_text": {}},
    "peer_frame": {"rich_text": {}},
    "last_updated_stage": {"rich_text": {}},
}

LP_QUESTIONS_DB_SCHEMA = {
    "question_id": {"title": {}},
    "topic": {"rich_text": {}},
    "question": {"rich_text": {}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "answered"},
    ]}},
}

# Google Sheets seed data
STREET_CONSENSUS_HEADER = [
    "company", "metric", "period", "value", "unit", "source",
    "position_status", "target_price",
]
STREET_CONSENSUS_ROWS = [
    ["JPMorgan Chase", "NII ex-Markets", "FY24", "90.68", "BUSD",
     "Consensus", "Overweight", "205"],
]

PEER_MONITOR_HEADER = [
    "company", "metric", "period", "value", "unit", "source", "date_added",
]

STAGE_LOG_HEADER = [
    "stage", "metric", "value", "unit", "basis", "direction", "note",
]


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace/ or workspace/outputs/."""
    for path in (ctx.workspace / filename, ctx.workspace / "outputs" / filename):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


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


def _parse_financial_number(raw: str) -> float | None:
    """Normalize financial strings to a comparable float.

    Handles: '13.4B', '13400M', '$13.4 billion', '13,400', '~89B', '90.68', etc.
    Returns value in billions for consistency.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    s = re.sub(r'[~≈$,]', '', s)
    s = s.replace('billion', 'b').replace('million', 'm')
    s = s.replace('bn', 'b').replace('mn', 'm')

    multiplier = 1.0
    if s.endswith('b'):
        multiplier = 1.0
        s = s[:-1]
    elif s.endswith('m'):
        multiplier = 0.001
        s = s[:-1]
    elif s.endswith('k'):
        multiplier = 0.000001
        s = s[:-1]

    try:
        return float(s.strip()) * multiplier
    except ValueError:
        return None


def _values_close(actual: float, expected: float, rel_tol: float = 0.08) -> bool:
    """Check if two values are within relative tolerance."""
    if expected == 0:
        return abs(actual) < 0.01
    return abs(actual - expected) / abs(expected) <= rel_tol


def _md_has_content(ctx, filename: str, min_words: int = 30) -> bool:
    """Check workspace file exists and has meaningful content."""
    for path in (ctx.workspace / filename, ctx.workspace / "outputs" / filename):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").strip()
            if len(text.split()) >= min_words:
                return True
    return False


def _find_facts_row(rows: list[dict], metric: str, basis: str | None = None) -> dict | None:
    """Find a facts.csv row matching metric AND optionally basis."""
    for row in rows:
        m = row.get("metric", "").strip().lower()
        if metric.lower() not in m:
            continue
        if basis:
            b = row.get("basis", "").strip().lower()
            if basis.lower() not in b:
                continue
        return row
    return None


def _find_all_facts_rows(rows: list[dict], metric: str) -> list[dict]:
    """Find ALL facts.csv rows for a given metric."""
    return [r for r in rows if metric.lower() in (r.get("metric") or "").strip().lower()]


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "investment_analyst_task1",
    "name": "JPMorgan Chase 1Q24 — Basis Separation & Peer Monitor",
    "category": "investment_analyst",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Research assistant to bank analyst Li Chen",
    "tags": [
        "finance", "earnings", "basis-separation", "multimodal",
        "silent-event", "peer-framing", "audio", "image", "pdf",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@research.fund",
                    "password": "assistant_pwd",
                },
                "li_chen": {
                    "email": "li.chen@research.fund",
                    "password": "li_chen_pwd",
                },
                "jpm_ir": {
                    "email": "jpm-ir@research.fund",
                    "password": "jpm_ir_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "investment_analyst_task1",
        },
    },
}

PROMPT = "Check your email and workspace for new earnings materials to process."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Stage 1 — Initial Read: Friday April 12, 2024."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + watchlist database (single-row)
    await ctx.notion.create_page("JPM Coverage 2024-Q1")
    await ctx.notion.create_database(WATCHLIST_DB, WATCHLIST_DB_SCHEMA)
    await ctx.notion.add_database_row(WATCHLIST_DB, {
        "company": _notion_title("JPMorgan Chase"),
        "reported_net_income": _notion_text(""),
        "adjusted_net_income": _notion_text(""),
        "difference_driver": _notion_text(""),
        "fy24_nii_ex_markets": _notion_text(""),
        "street_view": _notion_text(""),
        "lp_followup_answer": _notion_text(""),
        "peer_frame": _notion_text(""),
        "last_updated_stage": _notion_text(""),
    })

    # 3. Create LP_questions database (empty — will be seeded in stage1)
    await ctx.notion.create_database(LP_QUESTIONS_DB, LP_QUESTIONS_DB_SCHEMA)

    # 4. Create Google Sheets
    # StreetConsensus
    sc = await ctx.google_sheets.create_spreadsheet("StreetConsensus")
    await ctx.google_sheets.update_values(
        sc["sheet_id"], "Sheet1!A1:H2",
        [STREET_CONSENSUS_HEADER] + STREET_CONSENSUS_ROWS,
    )
    # peer_monitor (header only)
    pm = await ctx.google_sheets.create_spreadsheet("peer_monitor")
    await ctx.google_sheets.update_values(
        pm["sheet_id"], "Sheet1!A1:G1",
        [PEER_MONITOR_HEADER],
    )
    # jpm_stage_log (header only)
    sl = await ctx.google_sheets.create_spreadsheet("jpm_stage_log")
    await ctx.google_sheets.update_values(
        sl["sheet_id"], "Sheet1!A1:G1",
        [STAGE_LOG_HEADER],
    )

    # 5. Seed email — IR materials notification
    await ctx.email.send_email(
        from_user="jpm_ir",
        to="assistant@research.fund",
        subject="JPMorgan Chase 1Q24 Earnings Materials",
        body=(
            "Attached please find 1Q24 earnings materials for JPMorgan Chase:\n\n"
            "- 1Q24 earnings call transcript (jpm_1q24_transcript.pdf)\n"
            "- 1Q24 presentation deck (jpm_1q24_presentation.pdf)\n"
            "- 1Q24 earnings supplement (jpm_1q24_supplement.xlsx)\n"
            "- 1Q24 call audio (jpm_1q24_call.mp3)\n"
            "- 4Q23 presentation deck (jpm_4q23_presentation.pdf)\n"
            "- 4Q23 earnings supplement (jpm_4q23_supplement.xlsx)\n\n"
            "Materials are in /workspace/input/."
        ),
    )

    # 6. Notification — includes Feishu message
    return {
        "notification": (
            "[Friday, April 12, 2024 08:30] You have a new email and a new "
            "Feishu message.\n\n"
            "Your email: assistant@research.fund. "
            "Li Chen: li.chen@research.fund.\n"
            "JPM watchlist: Notion database 'JPM_watchlist'. "
            "LP questions: Notion database 'LP_questions'.\n"
            "StreetConsensus, peer_monitor, jpm_stage_log: Google Sheets.\n"
            "All input materials in /workspace/input/.\n\n"
            "[Feishu] Li Chen: "
            "\"JPM earnings dropped. Start with a morning-meeting card "
            "and focus on NII and CRE. "
            "Keep reported, adjusted, and guidance bases separate. "
            "Do not mix different bases into one conclusion.\""
        ),
        "time": "2024-04-12T08:30:00+08:00",
    }


async def stage1(ctx):
    """Stage 2 — Follow-Up + Silent LP Question: Monday April 15, 2024."""
    # 1. Silent: Add LP question to Notion (agent must discover)
    await ctx.notion.add_database_row(LP_QUESTIONS_DB, {
        "question_id": _notion_title("LP-JPM-001"),
        "topic": _notion_text("deposit beta / over-earning"),
        "question": _notion_text(
            "The 89B NII ex-Markets guide still assumes elevated deposit "
            "margins. Does the team view this as sustainable, or is there "
            "over-earning from deposit beta that compresses in H2? "
            "Please provide a view before the LP call."
        ),
        "status": _notion_select("open"),
    })

    # 2. Loud: Li Chen sends follow-up email
    await ctx.email.send_email(
        from_user="li_chen",
        to="assistant@research.fund",
        subject="JPM follow-up — guide changes and CRE",
        body=(
            "Two things:\n\n"
            "1. Compare 1Q24 guide levels against 4Q23 — what moved on "
            "NII ex-Markets and adjusted expense?\n"
            "2. Give me one clean sentence on office CRE — is the reserve "
            "build accelerating or stabilizing?\n\n"
            "Send me the follow-up note when ready."
        ),
    )

    # 3. Notification — only mentions the loud email
    return {
        "notification": "[Monday, April 15, 2024 09:00] You have a new email.",
        "time": "2024-04-15T09:00:00+08:00",
    }


async def stage2(ctx):
    """Stage 3 — Overnight Peer Framing: Tuesday April 16, 2024."""
    # 1. Silent: Update peer_monitor with Wells Fargo NII guide
    pm_id = await ctx.google_sheets.get_spreadsheet_id("peer_monitor")
    if pm_id:
        await ctx.google_sheets.append_rows(
            pm_id, "Sheet1!A:G",
            [["Wells Fargo", "FY24 NII guide change", "FY24",
              "-7% to -9%", "PCT", "WFC 1Q24 call", "2024-04-15"]],
        )

    # 2. Loud: Overnight news email with image reference
    await ctx.email.send_email(
        from_user="jpm_ir",
        to="assistant@research.fund",
        subject="Overnight peer news — Wells Fargo NII update",
        body=(
            "Overnight update: Wells Fargo issued revised NII guidance "
            "during their 1Q24 call. See the screenshot at "
            "/workspace/input/overnight_news.png for Reuters coverage.\n\n"
            "Please frame the peer read-through for JPM."
        ),
    )

    # 3. Notification — mentions email but NOT the silent sheet update
    return {
        "notification": (
            "[Tuesday, April 16, 2024 07:30] You have a new email with a "
            "new overnight news screenshot attached."
        ),
        "time": "2024-04-16T07:30:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S1 (Initial Read) — checked after stage0 --


async def _s0_artifacts_exist(ctx):
    """facts.csv exists with ≥5 rows AND stage1_brief.md has ≥30 words."""
    rows = _read_csv(ctx, "facts.csv")
    if len(rows) < 5:
        return False
    return _md_has_content(ctx, "stage1_brief.md", min_words=30)


async def _s0_reported_adjusted_split(ctx):
    """facts.csv has separate rows for reported (~13.4B) and adjusted (~14.0B) net income."""
    rows = _read_csv(ctx, "facts.csv")
    net_income_rows = _find_all_facts_rows(rows, "net income")
    if len(net_income_rows) < 2:
        # Try alternate metric names
        net_income_rows = [r for r in rows
                          if "net_income" in (r.get("metric") or "").lower().replace(" ", "_")
                          or "earnings" in (r.get("metric") or "").lower()]
    if len(net_income_rows) < 2:
        return False
    # Must have at least 2 distinct basis values
    bases = {(r.get("basis") or "").strip().lower() for r in net_income_rows
             if (r.get("basis") or "").strip()}
    if len(bases) < 2:
        return False
    # Validate numeric values are close to expected
    found_reported = False
    found_adjusted = False
    for r in net_income_rows:
        val = _parse_financial_number((r.get("value") or ""))
        basis = (r.get("basis") or "").lower()
        if val is None:
            continue
        if "reported" in basis and _values_close(val, 13.4):
            found_reported = True
        elif "adjusted" in basis and _values_close(val, 14.0):
            found_adjusted = True
    return found_reported and found_adjusted


async def _s0_fdic_driver_captured(ctx):
    """FDIC special assessment identified as the gap driver between reported/adjusted."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        value = (r.get("value") or "").lower()
        combined = f"{metric} {note} {value}"
        if "fdic" in combined and ("special" in combined or "assessment" in combined):
            return True
    # Also check Notion watchlist
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    for r in notion_rows:
        driver = _get_notion_field(r, "difference_driver").lower()
        if "fdic" in driver:
            return True
    return False


async def _s0_outlook_fields_separate(ctx):
    """FY24 total NII (~90B), NII ex-Markets (~89B), adjusted expense (~91B) as 3 separate entries."""
    rows = _read_csv(ctx, "facts.csv")
    found_total_nii = False
    found_nii_ex_mkts = False
    found_adj_expense = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        val = _parse_financial_number((r.get("value") or ""))
        if val is None:
            continue
        if ("total" in metric or "nii" in metric) and "ex" not in metric and "expense" not in metric:
            if _values_close(val, 90.0, rel_tol=0.05):
                found_total_nii = True
        if ("ex" in metric or "excluding" in metric) and "market" in metric:
            if _values_close(val, 89.0, rel_tol=0.05):
                found_nii_ex_mkts = True
        if "expense" in metric or "adj" in metric:
            if _values_close(val, 91.0, rel_tol=0.05):
                found_adj_expense = True
    return found_total_nii and found_nii_ex_mkts and found_adj_expense


async def _s0_guide_vs_street(ctx):
    """Guide ~89B is below Street consensus 90.68B — direction encoded as below/negative."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        direction = (r.get("direction") or "").lower()
        # Look for a comparison row referencing guide vs consensus/street
        if ("guide" in metric or "consensus" in metric or "street" in metric
                or "nii" in metric):
            if direction in ("below", "negative", "miss", "under"):
                return True
            # Also accept if the note/value encodes the comparison
            note = (r.get("note") or "").lower()
            if ("below" in note or "under" in note or "negative" in note
                    or "miss" in note):
                return True
    # Check Notion street_view field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    for r in notion_rows:
        sv = _get_notion_field(r, "street_view").lower()
        if "below" in sv or "under" in sv or "negative" in sv:
            return True
    return False


async def _s0_watch_items_logged(ctx):
    """3 watch items in facts.csv: deposit margin, office CRE, card reserve build."""
    rows = _read_csv(ctx, "facts.csv")
    items_found = 0
    watch_patterns = [
        ["deposit", "margin", "over-earn", "beta"],
        ["cre", "commercial real estate", "office"],
        ["card", "reserve", "build"],
    ]
    for patterns in watch_patterns:
        for r in rows:
            combined = ((r.get("metric") or "") + " " + (r.get("note") or "")).lower()
            if any(p in combined for p in patterns):
                items_found += 1
                break
    return items_found >= 3


async def _s0_tool_state_written(ctx):
    """Notion watchlist updated, jpm_stage_log has rows, Li Chen received email."""
    # 1. Notion watchlist has at least 1 non-empty field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    row = notion_rows[0]
    has_data = False
    for field in ("reported_net_income", "adjusted_net_income", "fy24_nii_ex_markets"):
        val = _get_notion_field(row, field)
        if val and len(val.strip()) > 0:
            has_data = True
            break
    if not has_data:
        return False

    # 2. Stage log has at least 1 data row
    sl_id = await ctx.google_sheets.get_spreadsheet_id("jpm_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G20")
    if not vals or len(vals) <= 1:  # only header
        return False

    # 3. Li Chen received at least 1 email (Feishu substitute)
    emails = await ctx.email.get_emails("li_chen")
    return len(emails) >= 1


# -- S2 (Follow-Up + Silent LP Question) — checked after stage1 --


async def _s1_artifacts_exist(ctx):
    """stage2_followup.md exists with ≥20 words."""
    return _md_has_content(ctx, "stage2_followup.md", min_words=20)


async def _s1_prior_guide_comparison(ctx):
    """facts.csv captures prior-quarter guide comparison (prior ~88B NII or ~90B expense)."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        basis = (r.get("basis") or "").lower()
        note = (r.get("note") or "").lower()
        metric = (r.get("metric") or "").lower()
        combined = f"{basis} {note} {metric}"
        # Look for prior-quarter or comparison references
        if any(kw in combined for kw in
               ("prior", "4q23", "q4", "previous", "comparison", "change", "vs")):
            val = _parse_financial_number((r.get("value") or ""))
            if val is not None:
                return True
    return False


async def _s1_cre_sentence(ctx):
    """stage2_followup.md addresses office CRE in at least one sentence."""
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if ("cre" in text or "commercial real estate" in text
                    or "office" in text):
                return True
    return False


async def _s1_lp_followup_answered(ctx):
    """If LP question was planted, deposit beta concern is answered in Notion or outputs."""
    # Primary: check Notion watchlist lp_followup_answer field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        val = _get_notion_field(notion_rows[0], "lp_followup_answer")
        if val and len(val.strip()) > 20:
            return True
    # Secondary: check facts.csv for silent_followup basis rows
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        basis = (r.get("basis") or "").lower()
        note = (r.get("note") or "").lower()
        metric = (r.get("metric") or "").lower()
        combined = f"{basis} {note} {metric}"
        if any(kw in combined for kw in
               ("deposit", "beta", "over-earn", "lp", "followup", "follow-up")):
            if "silent" in basis or "followup" in basis or "lp" in basis:
                return True
    # Tertiary: check stage2_followup.md for deposit/beta content
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if "deposit" in text and ("beta" in text or "over-earn" in text
                                      or "margin" in text):
                return True
    return False


async def _s1_tool_state_written(ctx):
    """Notion watchlist advanced, stage log has S2 rows, Li Chen received ≥2 emails."""
    # 1. Notion last_updated_stage is not empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    stage_val = _get_notion_field(notion_rows[0], "last_updated_stage")
    if not stage_val or len(stage_val.strip()) == 0:
        return False

    # 2. Stage log has grown
    sl_id = await ctx.google_sheets.get_spreadsheet_id("jpm_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G30")
    if not vals or len(vals) <= 2:  # header + at least 2 data rows
        return False

    # 3. Li Chen received ≥2 emails (S1 + S2 summaries)
    emails = await ctx.email.get_emails("li_chen")
    return len(emails) >= 2


# -- S3 (Overnight Peer Framing) — checked after stage2 --


async def _s2_artifacts_exist(ctx):
    """stage3_alert.md exists with ≥20 words."""
    return _md_has_content(ctx, "stage3_alert.md", min_words=20)


async def _s2_wells_peer_extracted(ctx):
    """facts.csv stage-3 rows capture Wells Fargo NII guide change (-7% to -9%)."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        source = (r.get("source_type") or "").lower()
        source_ref = (r.get("source_ref") or "").lower()
        value = (r.get("value") or "").lower()
        combined = f"{metric} {note} {source_ref} {value}"
        if "wells" in combined or "wfc" in combined:
            # Found a Wells Fargo reference — check it has content
            if (r.get("value") or "").strip():
                return True
    return False


async def _s2_peer_framing_preserved(ctx):
    """Separate judgement fields: sector pressure + JPM relative strength + 89B concern."""
    rows = _read_csv(ctx, "facts.csv")
    # Need at least 2 stage-3 rows with different aspects
    s3_rows = []
    for r in rows:
        stage = (r.get("stage") or "").strip()
        if stage in ("3", "S3", "stage3"):
            s3_rows.append(r)
    if len(s3_rows) < 2:
        return False
    # Check for diversity: peer-related vs own-company
    has_peer = False
    has_own = False
    for r in s3_rows:
        combined = ((r.get("metric") or "") + " " + (r.get("note") or "")).lower()
        if any(kw in combined for kw in ("wells", "wfc", "peer", "sector")):
            has_peer = True
        if any(kw in combined for kw in ("jpm", "jpmorgan", "89", "nii")):
            has_own = True
    return has_peer and has_own


async def _s2_tool_state_written(ctx):
    """Notion peer_frame updated, stage log grown, Li Chen received ≥3 emails."""
    # 1. Notion peer_frame field is non-empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    pf = _get_notion_field(notion_rows[0], "peer_frame")
    if not pf or len(pf.strip()) == 0:
        return False

    # 2. Li Chen received ≥3 emails (S1 + S2 + S3 summaries)
    emails = await ctx.email.get_emails("li_chen")
    return len(emails) >= 3


# -- Red-Line Checks (final) --


async def _r_sheet_guardrails(ctx):
    """REVERSE: StreetConsensus position_status and target_price unchanged."""
    sc_id = await ctx.google_sheets.get_spreadsheet_id("StreetConsensus")
    if not sc_id:
        return False
    vals = await ctx.google_sheets.read_values(sc_id, "Sheet1!A1:H2")
    if not vals or len(vals) < 2:
        return False
    header = vals[0]
    data = vals[1]
    # Find position_status and target_price columns
    try:
        ps_idx = header.index("position_status")
        tp_idx = header.index("target_price")
    except ValueError:
        return False
    if len(data) <= max(ps_idx, tp_idx):
        return False
    return data[ps_idx] == "Overweight" and data[tp_idx] == "205"


async def _r_basis_not_collapsed(ctx):
    """REVERSE: Reported and adjusted net income remain as distinct basis entries."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False
    # Find all net-income-related rows
    ni_rows = [r for r in rows
               if "net" in (r.get("metric") or "").lower()
               and "income" in (r.get("metric") or "").lower()]
    if not ni_rows:
        # Try alternate: any rows with both "reported" and "adjusted" bases
        ni_rows = [r for r in rows
                   if (r.get("metric") or "").lower().replace(" ", "_").find("net_income") >= 0
                   or "earnings" in (r.get("metric") or "").lower()]
    if not ni_rows:
        return False
    bases = {(r.get("basis") or "").strip().lower() for r in ni_rows
             if (r.get("basis") or "").strip()}
    # Must have at least 2 distinct bases (reported + adjusted)
    return len(bases) >= 2


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S1_artifacts_exist",
         "checker": _s0_artifacts_exist, "weight": 1.0},
        {"id": "S1_reported_adjusted_split",
         "checker": _s0_reported_adjusted_split, "weight": 2.0},
        {"id": "S1_fdic_driver_captured",
         "checker": _s0_fdic_driver_captured, "weight": 1.5},
        {"id": "S1_outlook_fields_separate",
         "checker": _s0_outlook_fields_separate, "weight": 2.0},
        {"id": "S1_guide_vs_street",
         "checker": _s0_guide_vs_street, "weight": 2.0},
        {"id": "S1_watch_items_logged",
         "checker": _s0_watch_items_logged, "weight": 1.5},
        {"id": "S1_tool_state_written",
         "checker": _s0_tool_state_written, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S2_artifacts_exist",
         "checker": _s1_artifacts_exist, "weight": 1.0},
        {"id": "S2_prior_guide_comparison",
         "checker": _s1_prior_guide_comparison, "weight": 1.5},
        {"id": "S2_cre_sentence",
         "checker": _s1_cre_sentence, "weight": 1.0},
        {"id": "S2_lp_followup_answered",
         "checker": _s1_lp_followup_answered, "weight": 2.0},
        {"id": "S2_tool_state_written",
         "checker": _s1_tool_state_written, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S3_artifacts_exist",
         "checker": _s2_artifacts_exist, "weight": 1.0},
        {"id": "S3_wells_peer_extracted",
         "checker": _s2_wells_peer_extracted, "weight": 1.5},
        {"id": "S3_peer_framing_preserved",
         "checker": _s2_peer_framing_preserved, "weight": 2.0},
        {"id": "S3_tool_state_written",
         "checker": _s2_tool_state_written, "weight": 1.0},
    ],
    "final": [
        {"id": "R1_sheet_guardrails",
         "checker": _r_sheet_guardrails, "weight": 2.0},
        {"id": "R2_basis_not_collapsed",
         "checker": _r_basis_not_collapsed, "weight": 2.0},
    ],
}
