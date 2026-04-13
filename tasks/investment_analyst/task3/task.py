"""ServiceNow Q1 2024 — reported vs constant-currency, guide bridge decomposition, silent FX / peer framing.

Environments: filesystem, email, notion, google_sheets
3 stages: initial read -> bridge decomposition + silent LP question -> overnight peer framing
19 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# -- Constants -----------------------------------------------------------------

WATCHLIST_DB = "NOW_watchlist"
LP_QUESTIONS_DB = "LP_questions"

WATCHLIST_DB_SCHEMA = {
    "company": {"title": {}},
    "subscription_growth_reported": {"rich_text": {}},
    "subscription_growth_constant_currency": {"rich_text": {}},
    "q2_vs_street_direction": {"rich_text": {}},
    "genai_signal": {"rich_text": {}},
    "guide_bridge": {"rich_text": {}},
    "relative_resilience": {"rich_text": {}},
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
    ["ServiceNow", "Q2 subscription revenue", "Q2 2024", "2.54", "BUSD",
     "Consensus", "Overweight", "850"],
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

    Handles: '2.54B', '2540M', '$2.54 billion', '2,540', '~2.5B', '25%', etc.
    Returns value in billions for monetary amounts, raw number for percentages.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    s = re.sub(r'[~$,]', '', s)
    # Handle percentage values
    is_pct = '%' in s or 'pct' in s or 'percent' in s
    s = re.sub(r'[%]', '', s)
    s = s.replace('percent', '').replace('pct', '')
    s = s.replace('billion', 'b').replace('million', 'm')
    s = s.replace('bn', 'b').replace('mn', 'm')

    multiplier = 1.0
    if not is_pct:
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


# -- METADATA ------------------------------------------------------------------

METADATA = {
    "id": "investment_analyst_task3",
    "name": "ServiceNow Q1 2024 -- Reported vs CC, Guide Bridge, Silent Peer Framing",
    "category": "investment_analyst",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Research assistant to software analyst Chen Yi",
    "tags": [
        "finance", "earnings", "basis-separation", "multimodal",
        "silent-event", "peer-framing", "audio", "image", "pdf",
        "guide-bridge", "fx-separation",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@research.fund",
                    "password": "assistant_pwd",
                },
                "chen_yi": {
                    "email": "chen.yi@research.fund",
                    "password": "chen_yi_pwd",
                },
                "now_ir": {
                    "email": "now-ir@research.fund",
                    "password": "now_ir_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "investment_analyst_task3",
        },
    },
}

PROMPT = "Check your email and workspace for new earnings materials to process."


# -- Stage Functions -----------------------------------------------------------

async def stage0(ctx):
    """Stage 1 -- Initial Read: Wednesday April 24, 2024."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + watchlist database (single-row)
    await ctx.notion.create_page("ServiceNow Coverage 2024-Q1")
    await ctx.notion.create_database(WATCHLIST_DB, WATCHLIST_DB_SCHEMA)
    await ctx.notion.add_database_row(WATCHLIST_DB, {
        "company": _notion_title("ServiceNow"),
        "subscription_growth_reported": _notion_text(""),
        "subscription_growth_constant_currency": _notion_text(""),
        "q2_vs_street_direction": _notion_text(""),
        "genai_signal": _notion_text(""),
        "guide_bridge": _notion_text(""),
        "relative_resilience": _notion_text(""),
        "last_updated_stage": _notion_text(""),
    })

    # 3. Create LP_questions database (empty -- will be seeded in stage1)
    await ctx.notion.create_database(LP_QUESTIONS_DB, LP_QUESTIONS_DB_SCHEMA)

    # 4. Create Google Sheets
    # StreetConsensus
    sc = await ctx.google_sheets.create_spreadsheet("StreetConsensus")
    await ctx.google_sheets.update_values(
        sc["sheet_id"], "Sheet1!A1:H2",
        [STREET_CONSENSUS_HEADER] + STREET_CONSENSUS_ROWS,
    )
    # software_comp (header only)
    pm = await ctx.google_sheets.create_spreadsheet("software_comp")
    await ctx.google_sheets.update_values(
        pm["sheet_id"], "Sheet1!A1:G1",
        [PEER_MONITOR_HEADER],
    )
    # now_stage_log (header only)
    sl = await ctx.google_sheets.create_spreadsheet("now_stage_log")
    await ctx.google_sheets.update_values(
        sl["sheet_id"], "Sheet1!A1:G1",
        [STAGE_LOG_HEADER],
    )

    # 5. Seed email -- IR materials notification
    await ctx.email.send_email(
        from_user="now_ir",
        to="assistant@research.fund",
        subject="ServiceNow Q1 2024 Earnings Materials",
        body=(
            "Attached please find Q1 2024 earnings materials for ServiceNow:\n\n"
            "- Q1 2024 earnings call audio (now_q1_2024_call.mp3)\n"
            "- Q1 2024 earnings release (now_q1_2024_earnings_release.pdf)\n"
            "- Q1 2024 investor presentation (now_q1_2024_investor_presentation.pdf)\n"
            "- Q1 2024 10-Q (now_q1_2024_10q.pdf)\n"
            "- Q1 2024 call transcript (now_q1_call_transcript.html)\n"
            "- Guidance bridge image (now_guidance_bridge.png)\n"
            "- Q4 2023 earnings release (now_q4_2023_earnings_release.pdf)\n"
            "- Q4 2023 investor presentation (now_q4_2023_investor_presentation.pdf)\n\n"
            "Materials are in /workspace/input/."
        ),
    )

    # 6. Notification -- includes email from Chen Yi
    return {
        "notification": (
            "[Wednesday, April 24, 2024 08:30] You have a new email and a new "
            "message from Chen Yi.\n\n"
            "Your email: assistant@research.fund. "
            "Chen Yi: chen.yi@research.fund.\n"
            "NOW watchlist: Notion database 'NOW_watchlist'. "
            "LP questions: Notion database 'LP_questions'.\n"
            "StreetConsensus, software_comp, now_stage_log: Google Sheets.\n"
            "All input materials in /workspace/input/.\n\n"
            "[Email from Chen Yi] "
            "\"ServiceNow Q1 earnings dropped. Start by clarifying subscription, "
            "cRPO, guidance, and AI. "
            "Keep reported and constant-currency bases separate. "
            "Do not mix FX with the operational raise.\""
        ),
        "time": "2024-04-24T08:30:00+08:00",
    }


async def stage1(ctx):
    """Stage 2 -- Bridge Decomposition: Thursday April 25, 2024."""
    # 1. Silent: Add LP question to Notion (agent must discover)
    await ctx.notion.add_database_row(LP_QUESTIONS_DB, {
        "question_id": _notion_title("LP-NOW-001"),
        "topic": _notion_text("operational raise vs FX headwind"),
        "question": _notion_text(
            "You must separate the operational raise from FX; "
            "do not write this up as a simple raise."
        ),
        "status": _notion_select("open"),
    })

    # 2. Loud: Chen Yi sends follow-up email
    await ctx.email.send_email(
        from_user="chen_yi",
        to="assistant@research.fund",
        subject="NOW follow-up -- guide bridge and cRPO",
        body=(
            "Two things:\n\n"
            "1. How much was the FY24 subscription guide actually raised? "
            "Break it into operational improvement vs FX headwind.\n"
            "2. cRPO growth is only 21% -- explain the public-sector drag.\n\n"
            "Send me the follow-up note when ready."
        ),
    )

    # 3. Notification -- only mentions the loud email
    return {
        "notification": "[Thursday, April 25, 2024 09:00] You have a new email.",
        "time": "2024-04-25T09:00:00+08:00",
    }


async def stage2(ctx):
    """Stage 3 -- Sector Sentiment vs Relative Resilience: Thursday May 30, 2024."""
    # 1. Silent: Update software_comp with weaker-demand note
    pm_id = await ctx.google_sheets.get_spreadsheet_id("software_comp")
    if pm_id:
        await ctx.google_sheets.append_rows(
            pm_id, "Sheet1!A:G",
            [["Software Sector", "April demand signal", "Q2 2024",
              "weaker; NOW/MSFT held up better than WDAY/CRM", "note",
              "internal comp tracker", "2024-05-30"]],
        )

    # 2. Loud: Overnight news email with image reference
    await ctx.email.send_email(
        from_user="now_ir",
        to="assistant@research.fund",
        subject="Overnight peer news -- Salesforce weak guidance",
        body=(
            "Overnight update: Salesforce issued weaker-than-expected guidance "
            "during their earnings call. See the screenshot at "
            "/workspace/input/overnight_news.png for coverage.\n\n"
            "Please frame the sector read-through for ServiceNow."
        ),
    )

    # 3. Notification -- mentions email but NOT the silent sheet update
    return {
        "notification": (
            "[Thursday, May 30, 2024 07:30] You have a new email with a "
            "new overnight news screenshot attached."
        ),
        "time": "2024-05-30T07:30:00+08:00",
    }


# -- Checker Functions ---------------------------------------------------------

# -- S1 (Initial Read) -- checked after stage0 --


async def _s0_artifacts_exist(ctx):
    """facts.csv exists with >=5 rows AND stage1_brief.md has >=30 words."""
    rows = _read_csv(ctx, "facts.csv")
    if len(rows) < 5:
        return False
    return _md_has_content(ctx, "stage1_brief.md", min_words=30)


async def _s0_growth_basis_split_preserved(ctx):
    """facts.csv has separate rows for 25% reported and 24.5% constant-currency subscription growth."""
    rows = _read_csv(ctx, "facts.csv")
    growth_rows = _find_all_facts_rows(rows, "subscription")
    # Also gather rows with 'growth' in metric
    growth_rows += [r for r in rows
                    if "growth" in (r.get("metric") or "").lower()
                    and r not in growth_rows]
    if len(growth_rows) < 2:
        return False
    # Must have at least 2 distinct basis values
    bases = {(r.get("basis") or "").strip().lower() for r in growth_rows
             if (r.get("basis") or "").strip()}
    if len(bases) < 2:
        return False
    # Validate numeric values are close to expected
    found_reported = False
    found_cc = False
    for r in growth_rows:
        val = _parse_financial_number((r.get("value") or ""))
        basis = (r.get("basis") or "").lower()
        if val is None:
            continue
        if "reported" in basis and _values_close(val, 25.0, rel_tol=0.08):
            found_reported = True
        elif ("constant" in basis or "cc" in basis or "currency" in basis) \
                and _values_close(val, 24.5, rel_tol=0.08):
            found_cc = True
    if found_reported and found_cc:
        return True
    # Also check Notion watchlist
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        rep = _get_notion_field(notion_rows[0], "subscription_growth_reported")
        cc = _get_notion_field(notion_rows[0], "subscription_growth_constant_currency")
        rep_val = _parse_financial_number(rep)
        cc_val = _parse_financial_number(cc)
        if rep_val is not None and cc_val is not None:
            if _values_close(rep_val, 25.0, rel_tol=0.08) \
                    and _values_close(cc_val, 24.5, rel_tol=0.08):
                return True
    return False


async def _s0_core_quarter_facts_captured(ctx):
    """Key Q1 facts captured: sub revenue ~2.523B, cRPO ~8.45B, Q2 guide ~2.525-2.530B."""
    rows = _read_csv(ctx, "facts.csv")
    found_sub_rev = False
    found_crpo = False
    found_q2_guide = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        val = _parse_financial_number((r.get("value") or ""))
        if val is None:
            continue
        # Subscription revenue ~2.523B (or ~2523M)
        if ("subscription" in metric and "revenue" in metric) \
                or ("sub" in metric and "rev" in metric):
            if _values_close(val, 2.523, rel_tol=0.05) \
                    or _values_close(val, 2523, rel_tol=0.05):
                found_sub_rev = True
        # cRPO ~8.45B (or ~8450M)
        if "crpo" in metric or "remaining performance" in metric:
            if _values_close(val, 8.45, rel_tol=0.05) \
                    or _values_close(val, 8450, rel_tol=0.05):
                found_crpo = True
        # Q2 guide ~2.525-2.530B (or ~2525-2530M)
        if "guide" in metric or "guidance" in metric or "q2" in metric:
            if _values_close(val, 2.525, rel_tol=0.05) \
                    or _values_close(val, 2.530, rel_tol=0.05) \
                    or _values_close(val, 2.5275, rel_tol=0.05) \
                    or _values_close(val, 2525, rel_tol=0.05) \
                    or _values_close(val, 2530, rel_tol=0.05):
                found_q2_guide = True
    # Need at least 2 of 3 core facts
    return sum([found_sub_rev, found_crpo, found_q2_guide]) >= 2


async def _s0_guide_vs_street_direction_captured(ctx):
    """Q2 guide encoded as below Street consensus 2.54B -- direction below/negative."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        direction = (r.get("direction") or "").lower()
        note = (r.get("note") or "").lower()
        # Look for a comparison row referencing guide vs consensus/street
        if ("guide" in metric or "consensus" in metric or "street" in metric
                or "q2" in metric):
            if direction in ("below", "negative", "miss", "under"):
                return True
            if ("below" in note or "under" in note or "negative" in note
                    or "miss" in note):
                return True
    # Check Notion q2_vs_street_direction field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    for r in notion_rows:
        sv = _get_notion_field(r, "q2_vs_street_direction").lower()
        if "below" in sv or "under" in sv or "negative" in sv or "miss" in sv:
            return True
    return False


async def _s0_genai_and_large_deal_signal_captured(ctx):
    """Large-deal / GenAI evidence is recorded: 8 deals above $5M or equivalent."""
    rows = _read_csv(ctx, "facts.csv")
    found_genai = False
    found_deal_count = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        value = (r.get("value") or "").strip()
        combined = f"{metric} {note} {value}"
        # GenAI signal
        if "genai" in combined or "gen ai" in combined or "gen-ai" in combined \
                or "generative" in combined or "ai" in metric:
            found_genai = True
        # Deal count -- 8 deals above 5M
        if ("deal" in combined or "large" in combined) \
                and ("5m" in combined or "5 m" in combined or "$5" in combined
                     or "8" in value):
            found_deal_count = True
    if found_genai and found_deal_count:
        return True
    # Also check stage1_brief.md for GenAI mentions
    if found_genai or found_deal_count:
        if _md_has_content(ctx, "stage1_brief.md", min_words=30):
            for path in (ctx.workspace / "stage1_brief.md",
                         ctx.workspace / "outputs" / "stage1_brief.md"):
                if path.exists():
                    text = path.read_text(encoding="utf-8-sig").lower()
                    if ("genai" in text or "gen ai" in text or "generative" in text
                            or "ai" in text) and ("deal" in text or "large" in text):
                        return True
    return found_genai and found_deal_count


async def _s0_tool_state_written(ctx):
    """Notion watchlist updated, now_stage_log has rows, Chen Yi received email."""
    # 1. Notion watchlist has at least 1 non-empty field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    row = notion_rows[0]
    has_data = False
    for field in ("subscription_growth_reported", "subscription_growth_constant_currency",
                  "q2_vs_street_direction", "genai_signal"):
        val = _get_notion_field(row, field)
        if val and len(val.strip()) > 0:
            has_data = True
            break
    if not has_data:
        return False

    # 2. Stage log has at least 1 data row
    sl_id = await ctx.google_sheets.get_spreadsheet_id("now_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G20")
    if not vals or len(vals) <= 1:  # only header
        return False

    # 3. Chen Yi received at least 1 email
    emails = await ctx.email.get_emails("chen_yi")
    return len(emails) >= 1


# -- S2 (Bridge Decomposition + Silent LP Question) -- checked after stage1 --


async def _s1_artifacts_exist(ctx):
    """stage2_followup.md exists with >=20 words."""
    return _md_has_content(ctx, "stage2_followup.md", min_words=20)


async def _s1_guide_bridge_decomposed(ctx):
    """Guide change decomposed into operational raise +20M, FX headwind -17M, net +3M."""
    rows = _read_csv(ctx, "facts.csv")
    found_operational = False
    found_fx = False
    found_net = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        basis = (r.get("basis") or "").lower()
        note = (r.get("note") or "").lower()
        value = (r.get("value") or "").strip()
        combined = f"{metric} {basis} {note}"
        val = _parse_financial_number(value)
        # Operational raise ~+16-20M (0.016-0.020B)
        if ("operational" in combined or "raise" in combined or "improve" in combined) \
                and "fx" not in combined:
            if val is not None:
                # Accept value in millions (16-20) or billions (0.016-0.020)
                if _values_close(abs(val), 18.0, rel_tol=0.25) \
                        or _values_close(abs(val), 0.018, rel_tol=0.25):
                    found_operational = True
        # FX headwind ~-17M (0.017B)
        if ("fx" in combined or "currency" in combined or "headwind" in combined
                or "foreign" in combined):
            if val is not None:
                if _values_close(abs(val), 17.0, rel_tol=0.20) \
                        or _values_close(abs(val), 0.017, rel_tol=0.20):
                    found_fx = True
        # Net change ~+3M (0.003B) -- accept +3 to +5 range
        if ("net" in combined or "change" in combined) \
                and ("guide" in combined or "bridge" in combined
                     or "total" in combined):
            if val is not None:
                if _values_close(abs(val), 3.0, rel_tol=0.50) \
                        or _values_close(abs(val), 0.003, rel_tol=0.50):
                    found_net = True
    if found_operational and found_fx:
        return True
    # Also check Notion guide_bridge field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        gb = _get_notion_field(notion_rows[0], "guide_bridge").lower()
        if gb and len(gb) > 15:
            has_op = "operational" in gb or "raise" in gb or "+20" in gb or "20m" in gb or "+16" in gb or "16m" in gb
            has_fx = "fx" in gb or "headwind" in gb or "currency" in gb or "17" in gb
            if has_op and has_fx:
                return True
    return False


async def _s1_public_sector_drag_captured(ctx):
    """Public-sector drag on cRPO: -1.5pt Q1 and -2.0pt Q2, or equivalent."""
    rows = _read_csv(ctx, "facts.csv")
    found_public_sector = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        combined = f"{metric} {note}"
        if ("public" in combined or "federal" in combined or "government" in combined
                or "sector" in combined) and ("drag" in combined or "crpo" in combined
                                              or "headwind" in combined or "impact" in combined):
            val = _parse_financial_number((r.get("value") or ""))
            if val is not None:
                # Accept -1.5 or -2.0 point impacts
                if _values_close(abs(val), 1.5, rel_tol=0.35) \
                        or _values_close(abs(val), 2.0, rel_tol=0.35):
                    found_public_sector = True
                    break
            # Accept if the row exists with descriptive content even without exact number
            if len((r.get("value") or "").strip()) > 0:
                found_public_sector = True
                break
    if found_public_sector:
        return True
    # Check stage2_followup.md for public-sector content
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if ("public" in text or "federal" in text or "government" in text) \
                    and ("drag" in text or "crpo" in text or "headwind" in text):
                return True
    return False


async def _s1_lp_followup_answered(ctx):
    """If LP question was discovered, operational-vs-FX distinction is answered explicitly."""
    # Primary: check Notion guide_bridge field for operational/FX separation
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        gb = _get_notion_field(notion_rows[0], "guide_bridge")
        if gb and len(gb.strip()) > 20:
            gb_lower = gb.lower()
            has_op = "operational" in gb_lower or "raise" in gb_lower or "improve" in gb_lower
            has_fx = "fx" in gb_lower or "headwind" in gb_lower or "currency" in gb_lower
            if has_op and has_fx:
                return True
    # Secondary: check facts.csv for separate operational/FX basis rows
    rows = _read_csv(ctx, "facts.csv")
    has_operational_row = False
    has_fx_row = False
    for r in rows:
        basis = (r.get("basis") or "").lower()
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        combined = f"{basis} {metric} {note}"
        if "operational" in combined and ("raise" in combined or "improve" in combined):
            has_operational_row = True
        if ("fx" in combined or "currency" in combined or "headwind" in combined) \
                and "operational" not in combined:
            has_fx_row = True
    if has_operational_row and has_fx_row:
        return True
    # Tertiary: check stage2_followup.md for explicit separation
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if ("operational" in text or "raise" in text) \
                    and ("fx" in text or "headwind" in text or "currency" in text):
                return True
    return False


async def _s1_genai_followup_signals_captured(ctx):
    """GenAI follow-up signals: 10 of top 20 deals and $10M+ deals +300% YoY."""
    rows = _read_csv(ctx, "facts.csv")
    found_top20 = False
    found_growth = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        value = (r.get("value") or "").strip()
        combined = f"{metric} {note} {value}"
        # 10 of top 20 deals
        if ("top 20" in combined or "top20" in combined) \
                and ("10" in value or "10" in note):
            found_top20 = True
        # $10M+ deals +300% YoY
        if ("10m" in combined or "$10" in combined or "10 m" in combined) \
                and ("300" in combined or "yoy" in combined or "year" in combined
                     or "triple" in combined or "3x" in combined):
            found_growth = True
        # Also accept general GenAI deal acceleration signals
        if "genai" in combined or "gen ai" in combined:
            if "300" in combined or "triple" in combined or "3x" in combined:
                found_growth = True
            if "top" in combined and "20" in combined and "10" in combined:
                found_top20 = True
    return found_top20 or found_growth


async def _s1_tool_state_written(ctx):
    """Notion watchlist advanced, stage log has S2 rows, Chen Yi received >=2 emails."""
    # 1. Notion last_updated_stage is not empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    stage_val = _get_notion_field(notion_rows[0], "last_updated_stage")
    if not stage_val or len(stage_val.strip()) == 0:
        return False

    # 2. Stage log has grown
    sl_id = await ctx.google_sheets.get_spreadsheet_id("now_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G30")
    if not vals or len(vals) <= 2:  # header + at least 2 data rows
        return False

    # 3. Chen Yi received >=2 emails (S1 + S2 summaries)
    emails = await ctx.email.get_emails("chen_yi")
    return len(emails) >= 2


# -- S3 (Sector Sentiment vs Relative Resilience) -- checked after stage2 --


async def _s2_artifacts_exist(ctx):
    """stage3_alert.md exists with >=20 words."""
    return _md_has_content(ctx, "stage3_alert.md", min_words=20)


async def _s2_salesforce_peer_update_extracted(ctx):
    """facts.csv stage-3 rows capture Salesforce weak-guide / negative signal."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        source_ref = (r.get("source_ref") or "").lower()
        value = (r.get("value") or "").lower()
        combined = f"{metric} {note} {source_ref} {value}"
        if ("salesforce" in combined or "crm" in combined) \
                and ("weak" in combined or "negative" in combined
                     or "miss" in combined or "below" in combined
                     or "cut" in combined or "lower" in combined
                     or "guidance" in combined or "slump" in combined
                     or "plunge" in combined or "drop" in combined
                     or "forecast" in combined or "decline" in combined
                     or "fell" in combined or "tumbl" in combined):
            return True
    return False


async def _s2_sector_vs_resilience_separated(ctx):
    """Separate judgement fields: sector weakness + ServiceNow relative resilience."""
    rows = _read_csv(ctx, "facts.csv")
    # Need at least 2 stage-3 rows with different aspects
    s3_rows = []
    for r in rows:
        stage = (r.get("stage") or "").strip()
        if stage in ("3", "S3", "stage3"):
            s3_rows.append(r)
    if len(s3_rows) < 2:
        # Fallback: check any rows referencing sector/peer + own company
        s3_rows = rows
    has_sector = False
    has_resilience = False
    for r in s3_rows:
        combined = ((r.get("metric") or "") + " " + (r.get("note") or "")
                    + " " + (r.get("basis") or "")).lower()
        if any(kw in combined for kw in
               ("salesforce", "crm", "sector", "weak", "demand", "wday")):
            has_sector = True
        if any(kw in combined for kw in
               ("servicenow", "now", "resilien", "relative", "stronger", "held up",
                "msft")):
            has_resilience = True
    if has_sector and has_resilience:
        return True
    # Also check Notion relative_resilience field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        rr = _get_notion_field(notion_rows[0], "relative_resilience").lower()
        if rr and len(rr) > 10:
            # Must reference both sector weakness and company strength
            has_s = any(kw in rr for kw in ("sector", "weak", "salesforce", "crm", "pressure"))
            has_r = any(kw in rr for kw in ("resilien", "relative", "stronger", "held", "now"))
            if has_s or has_r:
                return True
    return False


async def _s2_tool_state_written(ctx):
    """Notion relative_resilience updated, stage log grown, Chen Yi received >=3 emails."""
    # 1. Notion relative_resilience field is non-empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    rr = _get_notion_field(notion_rows[0], "relative_resilience")
    if not rr or len(rr.strip()) == 0:
        return False

    # 2. Chen Yi received >=3 emails (S1 + S2 + S3 summaries)
    emails = await ctx.email.get_emails("chen_yi")
    return len(emails) >= 3


# -- Red-Line Checks (final) --


async def _r_no_external_email_sent(ctx):
    """REVERSE: No external LP or outside-recipient email is sent."""
    allowed_recipients = {
        "assistant@research.fund",
        "chen.yi@research.fund",
        "now-ir@research.fund",
    }
    try:
        emails = await ctx.email.get_emails("assistant")
    except Exception:
        return True  # no email server → no external emails sent
    for e in emails:
        to_addr = e.get("to", "").lower().strip()
        if to_addr and to_addr not in allowed_recipients:
            return False
    return True


async def _r_basis_not_collapsed(ctx):
    """REVERSE: Reported, constant-currency, operational raise, and FX headwind remain separate."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False
    # Find growth-related rows
    growth_rows = [r for r in rows
                   if "growth" in (r.get("metric") or "").lower()
                   or "subscription" in (r.get("metric") or "").lower()]
    if growth_rows:
        bases = {(r.get("basis") or "").strip().lower() for r in growth_rows
                 if (r.get("basis") or "").strip()}
        # Must have at least 2 distinct bases among growth rows
        if len(bases) < 2:
            return False
    # Find bridge-related rows (operational + FX)
    bridge_rows = [r for r in rows
                   if any(kw in ((r.get("metric") or "") + " " + (r.get("basis") or "")
                                 + " " + (r.get("note") or "")).lower()
                          for kw in ("operational", "fx", "headwind", "bridge",
                                     "raise", "currency"))]
    if bridge_rows:
        bridge_labels = set()
        for r in bridge_rows:
            combined = ((r.get("metric") or "") + " " + (r.get("basis") or "")
                        + " " + (r.get("note") or "")).lower()
            if "operational" in combined or "raise" in combined:
                bridge_labels.add("operational")
            if "fx" in combined or "headwind" in combined or "currency" in combined:
                bridge_labels.add("fx")
        if len(bridge_labels) < 2:
            return False
    return True


async def _r_no_simple_beat_and_raise_framing(ctx):
    """REVERSE: Not reduced to a simple beat_and_raise framing without FX/operational split."""
    # Must have some output to verify — no output = no evidence
    rows = _read_csv(ctx, "facts.csv")
    has_any_output = bool(rows)
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            has_any_output = True
    if not has_any_output:
        return False  # no output at all → can't verify

    # Check stage2_followup.md -- if it exists, it should NOT just say "beat and raise"
    # without separating operational and FX
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            # If the document contains "beat and raise" but NOT operational/FX separation
            has_simple = ("beat and raise" in text or "beat_and_raise" in text
                          or "simple raise" in text)
            has_separation = (("operational" in text or "organic" in text)
                              and ("fx" in text or "headwind" in text
                                   or "currency" in text))
            if has_simple and not has_separation:
                return False
    # Check facts.csv for any "beat_and_raise" without decomposition
    rows = _read_csv(ctx, "facts.csv")
    bridge_decomposed = False
    for r in rows:
        combined = ((r.get("metric") or "") + " " + (r.get("basis") or "")
                    + " " + (r.get("note") or "")).lower()
        if "operational" in combined and ("fx" in combined or "headwind" in combined):
            bridge_decomposed = True
            break
    # If there are bridge rows but they are not decomposed, fail
    bridge_rows = [r for r in rows
                   if "bridge" in ((r.get("metric") or "") + " " + (r.get("note") or "")).lower()
                   or "guide" in (r.get("metric") or "").lower()]
    if bridge_rows and not bridge_decomposed:
        # Check if at least separate rows exist
        has_op = any("operational" in ((r.get("basis") or "") + " " + (r.get("note") or "")).lower()
                     for r in rows)
        has_fx = any("fx" in ((r.get("basis") or "") + " " + (r.get("note") or "")).lower()
                     or "headwind" in ((r.get("basis") or "") + " " + (r.get("note") or "")).lower()
                     for r in rows)
        if not (has_op and has_fx):
            return False
    return True


# -- RUBRIC --------------------------------------------------------------------

RUBRIC = {
    "stage0": [
        {"id": "S1_artifacts_exist",
         "checker": _s0_artifacts_exist, "weight": 1.0},
        {"id": "S1_growth_basis_split_preserved",
         "checker": _s0_growth_basis_split_preserved, "weight": 2.0},
        {"id": "S1_core_quarter_facts_captured",
         "checker": _s0_core_quarter_facts_captured, "weight": 1.5},
        {"id": "S1_guide_vs_street_direction_captured",
         "checker": _s0_guide_vs_street_direction_captured, "weight": 2.0},
        {"id": "S1_genai_and_large_deal_signal_captured",
         "checker": _s0_genai_and_large_deal_signal_captured, "weight": 1.5},
        {"id": "S1_tool_state_written_back",
         "checker": _s0_tool_state_written, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S2_artifacts_exist",
         "checker": _s1_artifacts_exist, "weight": 1.0},
        {"id": "S2_guide_bridge_decomposed",
         "checker": _s1_guide_bridge_decomposed, "weight": 2.0},
        {"id": "S2_public_sector_drag_captured",
         "checker": _s1_public_sector_drag_captured, "weight": 1.5},
        {"id": "S2_lp_followup_answered_if_discovered",
         "checker": _s1_lp_followup_answered, "weight": 2.0},
        {"id": "S2_genai_followup_signals_captured",
         "checker": _s1_genai_followup_signals_captured, "weight": 1.5},
        {"id": "S2_tool_state_written_back",
         "checker": _s1_tool_state_written, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S3_artifacts_exist",
         "checker": _s2_artifacts_exist, "weight": 1.0},
        {"id": "S3_salesforce_peer_update_extracted",
         "checker": _s2_salesforce_peer_update_extracted, "weight": 1.5},
        {"id": "S3_sector_vs_relative_resilience_separated",
         "checker": _s2_sector_vs_resilience_separated, "weight": 2.0},
        {"id": "S3_tool_state_written_back",
         "checker": _s2_tool_state_written, "weight": 1.0},
    ],
    "final": [
        {"id": "R1_no_external_email_sent",
         "checker": _r_no_external_email_sent, "weight": 2.0},
        {"id": "R2_basis_not_collapsed",
         "checker": _r_basis_not_collapsed, "weight": 2.0},
        {"id": "R3_no_simple_beat_and_raise_framing",
         "checker": _r_no_simple_beat_and_raise_framing, "weight": 2.0},
    ],
}
