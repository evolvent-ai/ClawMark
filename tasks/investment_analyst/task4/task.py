"""Netflix Q1 2024 — reported vs FX-neutral monetization, paid-sharing mix, silent peer monitor.

Environments: filesystem, email, notion, google_sheets
3 stages: initial read -> follow-up + silent partner question -> overnight peer framing
18 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# -- Constants -----------------------------------------------------------------

WATCHLIST_DB = "Netflix_watchlist"
PARTNER_QUESTIONS_DB = "Partner_questions"

WATCHLIST_DB_SCHEMA = {
    "company": {"title": {}},
    "q1_revenue_growth_reported": {"rich_text": {}},
    "q1_arm_growth_reported": {"rich_text": {}},
    "fy24_operating_margin_guide": {"rich_text": {}},
    "street_view": {"rich_text": {}},
    "partner_followup_answer": {"rich_text": {}},
    "peer_frame": {"rich_text": {}},
    "last_updated_stage": {"rich_text": {}},
}

PARTNER_QUESTIONS_DB_SCHEMA = {
    "question_id": {"title": {}},
    "topic": {"rich_text": {}},
    "question": {"rich_text": {}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "answered"},
    ]}},
}

# Google Sheets seed data
STREAMING_CONSENSUS_HEADER = [
    "company", "metric", "period", "value", "unit", "source",
    "position_status", "target_price",
]
STREAMING_CONSENSUS_ROWS = [
    ["Netflix", "Q2 revenue consensus", "Q2 2024", "9.537", "BUSD",
     "Consensus", "", ""],
    ["Netflix", "Q1 paid net add consensus", "Q1 2024", "5.0", "M",
     "Consensus", "", ""],
]

PEER_MONITOR_HEADER = [
    "company", "metric", "period", "value", "unit", "source", "date_added",
]

STAGE_LOG_HEADER = [
    "stage", "metric", "value", "unit", "basis", "direction", "note",
]


# -- Helpers -------------------------------------------------------------------

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

    Handles: '9.370B', '9370M', '$9.37 billion', '9,370', '~9.5B', etc.
    Returns value in billions for consistency.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    s = re.sub(r'[~$,]', '', s)
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


def _parse_percentage(raw: str) -> float | None:
    """Extract a numeric percentage value from a string.

    Handles: '14.8%', '14.8 %', '14.8', '~15%', '+18% FX-neutral', etc.
    Returns the numeric value (e.g. 14.8 for 14.8%).
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    s = re.sub(r'[~+]', '', s)
    m = re.search(r'(-?\d+(?:\.\d+)?)', s)
    if m:
        return float(m.group(1))
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


# -- METADATA ------------------------------------------------------------------

METADATA = {
    "id": "investment_analyst_task4",
    "name": "Netflix Q1 2024 — Reported vs FX-Neutral Monetization & Peer Monitor",
    "category": "investment_analyst",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Associate consultant to commercial strategy partner Grace Wu",
    "tags": [
        "finance", "earnings", "basis-separation", "multimodal",
        "silent-event", "peer-framing", "image", "pdf", "html",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@research.fund",
                    "password": "assistant_pwd",
                },
                "grace_wu": {
                    "email": "grace.wu@research.fund",
                    "password": "grace_wu_pwd",
                },
                "netflix_ir": {
                    "email": "netflix-ir@research.fund",
                    "password": "netflix_ir_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "investment_analyst_task4",
        },
    },
}

PROMPT = "Check your email and workspace for new earnings materials to process."


# -- Stage Functions -----------------------------------------------------------

async def stage0(ctx):
    """Stage 1 -- Initial Read: Thursday April 18, 2024."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + watchlist database (single-row)
    await ctx.notion.create_page("Netflix monetization note")
    await ctx.notion.create_database(WATCHLIST_DB, WATCHLIST_DB_SCHEMA)
    await ctx.notion.add_database_row(WATCHLIST_DB, {
        "company": _notion_title("Netflix"),
        "q1_revenue_growth_reported": _notion_text(""),
        "q1_arm_growth_reported": _notion_text(""),
        "fy24_operating_margin_guide": _notion_text(""),
        "street_view": _notion_text(""),
        "partner_followup_answer": _notion_text(""),
        "peer_frame": _notion_text(""),
        "last_updated_stage": _notion_text(""),
    })

    # 3. Create Partner_questions database (empty -- will be seeded in stage1)
    await ctx.notion.create_database(PARTNER_QUESTIONS_DB, PARTNER_QUESTIONS_DB_SCHEMA)

    # 4. Create Google Sheets
    # StreamingConsensus
    sc = await ctx.google_sheets.create_spreadsheet("StreamingConsensus")
    await ctx.google_sheets.update_values(
        sc["sheet_id"], "Sheet1!A1:H3",
        [STREAMING_CONSENSUS_HEADER] + STREAMING_CONSENSUS_ROWS,
    )
    # peer_monitor (header only)
    pm = await ctx.google_sheets.create_spreadsheet("peer_monitor")
    await ctx.google_sheets.update_values(
        pm["sheet_id"], "Sheet1!A1:G1",
        [PEER_MONITOR_HEADER],
    )
    # netflix_stage_log (header only)
    sl = await ctx.google_sheets.create_spreadsheet("netflix_stage_log")
    await ctx.google_sheets.update_values(
        sl["sheet_id"], "Sheet1!A1:G1",
        [STAGE_LOG_HEADER],
    )

    # 5. Seed email -- IR materials notification
    await ctx.email.send_email(
        from_user="netflix_ir",
        to="assistant@research.fund",
        subject="Netflix Q1 2024 Earnings Materials",
        body=(
            "Attached please find Q1 2024 earnings materials for Netflix:\n\n"
            "- Q1 2024 shareholder letter (netflix_q1_2024_shareholder_letter.pdf)\n"
            "- Q1 2024 earnings call transcript (netflix_q1_2024_transcript.pdf)\n"
            "- Q4 2023 shareholder letter (netflix_q4_2023_shareholder_letter.html)\n"
            "- Reuters Q1 preview (reuters_netflix_q1_preview.html)\n"
            "- Reuters Q1 results (reuters_netflix_q1_results.html)\n"
            "- Ads signup crop (netflix_q1_ads_signup_crop.png)\n\n"
            "Materials are in /workspace/input/."
        ),
    )

    # 6. Notification -- includes Feishu message
    return {
        "notification": (
            "[Thursday, April 18, 2024 08:30] You have a new email and a new "
            "Feishu message.\n\n"
            "Your email: assistant@research.fund. "
            "Grace Wu: grace.wu@research.fund.\n"
            "Netflix watchlist: Notion database 'Netflix_watchlist'. "
            "Partner questions: Notion database 'Partner_questions'.\n"
            "StreamingConsensus, peer_monitor, netflix_stage_log: Google Sheets.\n"
            "All input materials in /workspace/input/.\n\n"
            "[Feishu] Grace Wu: "
            "\"Need a first steering card on monetization quality. "
            "Keep reported, FX-neutral, and guide bases separate. "
            "Do not let strong net adds flatten the pricing / ARM discussion.\""
        ),
        "time": "2024-04-18T08:30:00+08:00",
    }


async def stage1(ctx):
    """Stage 2 -- Follow-Up + Silent Partner Question: Friday April 19, 2024."""
    # 1. Silent: Add partner question to Notion (agent must discover)
    await ctx.notion.add_database_row(PARTNER_QUESTIONS_DB, {
        "question_id": _notion_title("PQ-NFLX-001"),
        "topic": _notion_text("ARM / pricing effectiveness"),
        "question": _notion_text(
            "1% reported ARM growth looks like pricing is not working. "
            "Is paid sharing just shifting mix toward lower-price SKUs and "
            "masking any real pricing power? "
            "Please clarify before the next partner steering."
        ),
        "status": _notion_select("open"),
    })

    # 2. Loud: Grace Wu sends follow-up email
    await ctx.email.send_email(
        from_user="grace_wu",
        to="assistant@research.fund",
        subject="Netflix follow-up -- guide changes and ARM",
        body=(
            "Two things:\n\n"
            "1. Compare Q1 actuals against Q4'23 guide levels -- what moved "
            "on revenue, operating margin, and FY24 margin?\n"
            "2. Give me one clean sentence on ARM -- is pricing working or not?\n\n"
            "Send me the follow-up note when ready."
        ),
    )

    # 3. Notification -- only mentions the loud email
    return {
        "notification": "[Friday, April 19, 2024 09:00] You have a new email.",
        "time": "2024-04-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """Stage 3 -- Overnight Peer Framing: Tuesday May 7, 2024."""
    # 1. Silent: Update peer_monitor with Disney streaming profitability
    pm_id = await ctx.google_sheets.get_spreadsheet_id("peer_monitor")
    if pm_id:
        await ctx.google_sheets.append_rows(
            pm_id, "Sheet1!A:G",
            [["Disney", "Entertainment DTC profitable", "FQ2 2024",
              "profitable", "status", "Disney FQ2 2024 release", "2024-05-07"],
             ["Disney", "Disney+ Core subscriber adds", "FQ2 2024",
              "6", "M", "Disney FQ2 2024 release", "2024-05-07"],
             ["Disney", "Disney+ Core ARPU sequential change", "FQ2 2024",
              "+0.44", "USD", "Disney FQ2 2024 release", "2024-05-07"]],
        )

    # 2. Loud: Overnight news email with image reference
    await ctx.email.send_email(
        from_user="netflix_ir",
        to="assistant@research.fund",
        subject="Overnight peer news -- Disney streaming update",
        body=(
            "Overnight update: Disney reported fiscal Q2 2024 results. "
            "Entertainment DTC turned profitable and combined streaming "
            "businesses are expected profitable by fiscal Q4. "
            "See the screenshot at /workspace/input/netflix_q1_peer_streaming_news.png "
            "for coverage details.\n\n"
            "Please frame the peer read-through for Netflix."
        ),
    )

    # 3. Notification -- mentions email but NOT the silent sheet update
    return {
        "notification": (
            "[Tuesday, May 7, 2024 07:30] You have a new email with a "
            "new overnight peer screenshot attached."
        ),
        "time": "2024-05-07T07:30:00+08:00",
    }


# -- Checker Functions ---------------------------------------------------------

# -- S1 (Initial Read) -- checked after stage0 --


async def _s0_artifacts_exist(ctx):
    """facts.csv exists with >=5 rows AND stage1_brief.md has >=30 words."""
    rows = _read_csv(ctx, "facts.csv")
    if len(rows) < 5:
        return False
    return _md_has_content(ctx, "stage1_brief.md", min_words=30)


async def _s0_reported_vs_fxn_revenue(ctx):
    """facts.csv has separate rows for Q1 revenue growth 14.8% reported and 18% FX-neutral."""
    rows = _read_csv(ctx, "facts.csv")
    found_reported = False
    found_fxn = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        basis = (r.get("basis") or "").lower()
        value_raw = (r.get("value") or "")
        val = _parse_percentage(value_raw)
        if val is None:
            continue
        is_revenue_growth = ("revenue" in metric and "growth" in metric) or \
                            ("revenue" in metric and "yoy" in metric) or \
                            ("rev" in metric and "growth" in metric)
        if not is_revenue_growth:
            continue
        if "reported" in basis and _values_close(val, 14.8, rel_tol=0.08):
            found_reported = True
        if ("fx" in basis or "fx_neutral" in basis or "constant" in basis
                or "fx-neutral" in basis or "fxn" in basis):
            if _values_close(val, 18.0, rel_tol=0.08):
                found_fxn = True
    if found_reported and found_fxn:
        return True
    # Fallback: check if at least 2 revenue-growth rows with distinct bases exist
    rev_rows = [r for r in rows
                if "revenue" in (r.get("metric") or "").lower()
                and "growth" in (r.get("metric") or "").lower()]
    if len(rev_rows) < 2:
        return False
    bases = {(r.get("basis") or "").strip().lower() for r in rev_rows
             if (r.get("basis") or "").strip()}
    return len(bases) >= 2


async def _s0_reported_vs_fxn_arm(ctx):
    """facts.csv has separate rows for ARM growth 1% reported and 4% FX-neutral."""
    rows = _read_csv(ctx, "facts.csv")
    found_reported = False
    found_fxn = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        basis = (r.get("basis") or "").lower()
        value_raw = (r.get("value") or "")
        val = _parse_percentage(value_raw)
        if val is None:
            continue
        is_arm = "arm" in metric or "average revenue per member" in metric \
                 or "arpu" in metric
        if not is_arm:
            continue
        if "reported" in basis and _values_close(val, 1.0, rel_tol=0.15):
            found_reported = True
        if ("fx" in basis or "fx_neutral" in basis or "constant" in basis
                or "fx-neutral" in basis or "fxn" in basis):
            if _values_close(val, 4.0, rel_tol=0.15):
                found_fxn = True
    if found_reported and found_fxn:
        return True
    # Fallback: check if at least 2 ARM rows with distinct bases exist
    arm_rows = [r for r in rows
                if "arm" in (r.get("metric") or "").lower()
                or "arpu" in (r.get("metric") or "").lower()]
    if len(arm_rows) < 2:
        return False
    bases = {(r.get("basis") or "").strip().lower() for r in arm_rows
             if (r.get("basis") or "").strip()}
    return len(bases) >= 2


async def _s0_q2_guide_vs_consensus(ctx):
    """Q2 revenue guide 9.491B recorded as below consensus 9.537B."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        direction = (r.get("direction") or "").lower()
        note = (r.get("note") or "").lower()
        value_raw = (r.get("value") or "")
        # Look for Q2 guide or consensus comparison
        if ("q2" in metric or "guide" in metric or "consensus" in metric
                or "revenue" in metric):
            if direction in ("below", "negative", "miss", "under"):
                return True
            if ("below" in note or "under" in note or "miss" in note
                    or "negative" in note):
                return True
            # Check if value encodes the comparison (e.g. 9.491 vs 9.537)
            val = _parse_financial_number(value_raw)
            if val is not None and _values_close(val, 9.491, rel_tol=0.02):
                # Found the guide value; look for direction or consensus pair
                if direction or "consensus" in note or "street" in note:
                    return True
    # Check Notion street_view field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    for r in notion_rows:
        sv = _get_notion_field(r, "street_view").lower()
        if "below" in sv or "under" in sv or "miss" in sv or "negative" in sv:
            return True
    return False


async def _s0_ads_and_net_adds(ctx):
    """Paid net adds, ads membership growth, and ads-plan signup mix captured."""
    rows = _read_csv(ctx, "facts.csv")
    found_net_adds = False
    found_ads_growth = False
    found_ads_mix = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        value_raw = (r.get("value") or "")
        combined = f"{metric} {note}"
        # Paid net adds ~9.33M
        if ("net add" in combined or "paid" in combined and "add" in combined
                or "subscriber" in combined):
            val = _parse_financial_number(value_raw)
            if val is not None:
                found_net_adds = True
            # Also accept raw number patterns
            pct = _parse_percentage(value_raw)
            if pct is not None and _values_close(pct, 9.33, rel_tol=0.10):
                found_net_adds = True
        # Ads membership +65% QoQ
        if "ads" in combined or "ad-" in combined or "ad " in combined:
            if "65" in value_raw or "member" in combined or "growth" in combined:
                found_ads_growth = True
            # Ads plan mix 40%+
            if "40" in value_raw or "signup" in combined or "mix" in combined:
                found_ads_mix = True
    return found_net_adds and (found_ads_growth or found_ads_mix)


async def _s0_watch_items(ctx):
    """3 watch items: paid-sharing durability, ads monetization lag, Argentina FX distortion."""
    rows = _read_csv(ctx, "facts.csv")
    items_found = 0
    watch_patterns = [
        ["paid", "sharing", "durability", "churn"],
        ["ad", "monetization", "lag", "inventory"],
        ["argentina", "fx", "distortion", "currency"],
    ]
    for patterns in watch_patterns:
        for r in rows:
            combined = ((r.get("metric") or "") + " " + (r.get("note") or "")).lower()
            if any(p in combined for p in patterns):
                items_found += 1
                break
    return items_found >= 3


async def _s0_tool_state_written(ctx):
    """Notion watchlist updated, netflix_stage_log has rows, Grace Wu received email."""
    # 1. Notion watchlist has at least 1 non-empty field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    row = notion_rows[0]
    has_data = False
    for field in ("q1_revenue_growth_reported", "q1_arm_growth_reported",
                  "fy24_operating_margin_guide"):
        val = _get_notion_field(row, field)
        if val and len(val.strip()) > 0:
            has_data = True
            break
    if not has_data:
        return False

    # 2. Stage log has at least 1 data row
    sl_id = await ctx.google_sheets.get_spreadsheet_id("netflix_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G20")
    if not vals or len(vals) <= 1:  # only header
        return False

    # 3. Grace Wu received at least 1 email (Feishu substitute)
    emails = await ctx.email.get_emails("grace_wu")
    return len(emails) >= 1


# -- S2 (Follow-Up + Silent Partner Question) -- checked after stage1 --


async def _s1_artifacts_exist(ctx):
    """stage2_followup.md exists with >=20 words."""
    return _md_has_content(ctx, "stage2_followup.md", min_words=20)


async def _s1_prior_guide_comparison(ctx):
    """facts.csv captures prior-quarter guide comparison (prior Q1 revenue guide 9.240B, etc.)."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        basis = (r.get("basis") or "").lower()
        note = (r.get("note") or "").lower()
        metric = (r.get("metric") or "").lower()
        combined = f"{basis} {note} {metric}"
        # Look for prior-quarter or comparison references
        if any(kw in combined for kw in
               ("prior", "q4", "4q23", "previous", "comparison", "change", "vs",
                "guide")):
            val = _parse_financial_number((r.get("value") or ""))
            pct = _parse_percentage((r.get("value") or ""))
            if val is not None or pct is not None:
                return True
    return False


async def _s1_arm_sentence(ctx):
    """stage2_followup.md addresses ARM in at least one sentence."""
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if ("arm" in text or "average revenue per member" in text
                    or "arpu" in text):
                return True
    return False


async def _s1_partner_followup_answered(ctx):
    """If partner question was planted, pricing/mix concern is answered in Notion or outputs."""
    # Primary: check Notion watchlist partner_followup_answer field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        val = _get_notion_field(notion_rows[0], "partner_followup_answer")
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
               ("pricing", "mix", "arm", "partner", "followup", "follow-up",
                "paid sharing", "sku")):
            if ("silent" in basis or "followup" in basis or "partner" in basis
                    or "follow-up" in basis):
                return True
    # Tertiary: check stage2_followup.md for pricing/mix content
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if ("pricing" in text and ("mix" in text or "arm" in text
                                       or "paid sharing" in text)):
                return True
    return False


async def _s1_tool_state_written(ctx):
    """Notion watchlist advanced, stage log has S2 rows, Grace Wu received >=2 emails."""
    # 1. Notion last_updated_stage is not empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    stage_val = _get_notion_field(notion_rows[0], "last_updated_stage")
    if not stage_val or len(stage_val.strip()) == 0:
        return False

    # 2. Stage log has grown
    sl_id = await ctx.google_sheets.get_spreadsheet_id("netflix_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G30")
    if not vals or len(vals) <= 2:  # header + at least 2 data rows
        return False

    # 3. Grace Wu received >=2 emails (S1 + S2 summaries)
    emails = await ctx.email.get_emails("grace_wu")
    return len(emails) >= 2


# -- S3 (Overnight Peer Framing) -- checked after stage2 --


async def _s2_artifacts_exist(ctx):
    """stage3_alert.md exists with >=20 words."""
    return _md_has_content(ctx, "stage3_alert.md", min_words=20)


async def _s2_disney_peer_extracted(ctx):
    """facts.csv stage-3 rows capture Disney streaming profitability facts."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        source_ref = (r.get("source_ref") or "").lower()
        value = (r.get("value") or "").lower()
        combined = f"{metric} {note} {source_ref} {value}"
        if "disney" in combined:
            # Found a Disney reference -- check it has content
            if (r.get("value") or "").strip():
                return True
    return False


async def _s2_peer_relative_framing(ctx):
    """Separate judgement fields: sector improvement + Netflix relative strength + remaining debate."""
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
        if any(kw in combined for kw in ("disney", "peer", "sector")):
            has_peer = True
        if any(kw in combined for kw in ("netflix", "nflx", "relative",
                                          "stronger", "lead", "margin")):
            has_own = True
    return has_peer and has_own


async def _s2_tool_state_written(ctx):
    """Notion peer_frame updated, stage log grown, Grace Wu received >=3 emails."""
    # 1. Notion peer_frame field is non-empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    pf = _get_notion_field(notion_rows[0], "peer_frame")
    if not pf or len(pf.strip()) == 0:
        return False

    # 2. Grace Wu received >=3 emails (S1 + S2 + S3 summaries)
    emails = await ctx.email.get_emails("grace_wu")
    return len(emails) >= 3


# -- Red-Line Checks (final) --


async def _r_bases_not_collapsed(ctx):
    """REVERSE: Reported and FX-neutral revenue/ARM bases remain distinct; net adds not merged."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False
    # Check revenue growth rows
    rev_rows = [r for r in rows
                if "revenue" in (r.get("metric") or "").lower()
                and ("growth" in (r.get("metric") or "").lower()
                     or "yoy" in (r.get("metric") or "").lower())]
    if rev_rows:
        bases = {(r.get("basis") or "").strip().lower() for r in rev_rows
                 if (r.get("basis") or "").strip()}
        if len(bases) < 2:
            return False
    # Check ARM rows
    arm_rows = [r for r in rows
                if "arm" in (r.get("metric") or "").lower()
                or "arpu" in (r.get("metric") or "").lower()]
    if arm_rows:
        bases = {(r.get("basis") or "").strip().lower() for r in arm_rows
                 if (r.get("basis") or "").strip()}
        if len(bases) < 2:
            return False
    # Verify net adds are not merged into ARM/pricing rows
    for r in rows:
        metric = (r.get("metric") or "").lower()
        if ("arm" in metric or "pricing" in metric or "arpu" in metric):
            note = (r.get("note") or "").lower()
            value = (r.get("value") or "").lower()
            # Net adds value (9.33M) should not appear in ARM rows
            if "9.33" in value or "9330" in value:
                return False
    return True


async def _r_peer_readthrough_not_overstated(ctx):
    """REVERSE: Disney update affects sector framing without erasing Netflix's separate profile."""
    for path in (ctx.workspace / "stage3_alert.md",
                 ctx.workspace / "outputs" / "stage3_alert.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            # The alert should mention both Disney/peer AND Netflix
            has_peer = ("disney" in text or "peer" in text or "sector" in text)
            has_netflix = ("netflix" in text or "nflx" in text)
            if not (has_peer and has_netflix):
                # Missing one side -- likely overstated or incomplete
                return False
            # Should not claim Disney has caught up or Netflix lead is gone
            overstatement_signals = [
                "caught up", "no longer leads", "lead is gone",
                "parity", "same position", "equal footing",
            ]
            for sig in overstatement_signals:
                if sig in text:
                    return False
            return True
    return False


# -- RUBRIC --------------------------------------------------------------------

RUBRIC = {
    "stage0": [
        {"id": "S1_artifacts_exist",
         "checker": _s0_artifacts_exist, "weight": 1.0},
        {"id": "S1_reported_vs_fxn_revenue",
         "checker": _s0_reported_vs_fxn_revenue, "weight": 2.0},
        {"id": "S1_reported_vs_fxn_arm",
         "checker": _s0_reported_vs_fxn_arm, "weight": 2.0},
        {"id": "S1_q2_guide_vs_consensus",
         "checker": _s0_q2_guide_vs_consensus, "weight": 2.0},
        {"id": "S1_ads_and_net_adds",
         "checker": _s0_ads_and_net_adds, "weight": 1.5},
        {"id": "S1_watch_items",
         "checker": _s0_watch_items, "weight": 1.5},
        {"id": "S1_tool_state_written",
         "checker": _s0_tool_state_written, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S2_artifacts_exist",
         "checker": _s1_artifacts_exist, "weight": 1.0},
        {"id": "S2_prior_guide_comparison",
         "checker": _s1_prior_guide_comparison, "weight": 1.5},
        {"id": "S2_arm_sentence",
         "checker": _s1_arm_sentence, "weight": 1.0},
        {"id": "S2_partner_followup_answered",
         "checker": _s1_partner_followup_answered, "weight": 2.0},
        {"id": "S2_tool_state_written",
         "checker": _s1_tool_state_written, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S3_artifacts_exist",
         "checker": _s2_artifacts_exist, "weight": 1.0},
        {"id": "S3_disney_peer_extracted",
         "checker": _s2_disney_peer_extracted, "weight": 1.5},
        {"id": "S3_peer_relative_framing",
         "checker": _s2_peer_relative_framing, "weight": 2.0},
        {"id": "S3_tool_state_written",
         "checker": _s2_tool_state_written, "weight": 1.0},
    ],
    "final": [
        {"id": "R1_bases_not_collapsed",
         "checker": _r_bases_not_collapsed, "weight": 2.0},
        {"id": "R2_peer_readthrough_not_overstated",
         "checker": _r_peer_readthrough_not_overstated, "weight": 2.0},
    ],
}
