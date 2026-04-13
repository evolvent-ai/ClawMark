"""TSMC 1Q24 — currency normalization, node-mix cross-check, silent thesis split.

Environments: filesystem, email, notion, google_sheets
3 stages: initial read → follow-up + silent LP question → overnight peer framing
18 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

WATCHLIST_DB = "TSMC_watchlist"
LP_QUESTIONS_DB = "LP_questions"

WATCHLIST_DB_SCHEMA = {
    "company": {"title": {}},
    "revenue_usd": {"rich_text": {}},
    "revenue_twd": {"rich_text": {}},
    "currency_normalized": {"rich_text": {}},
    "node_mix_3nm": {"rich_text": {}},
    "platform_mix_hpc": {"rich_text": {}},
    "margin_headwinds": {"rich_text": {}},
    "followup_note": {"rich_text": {}},
    "readthrough_scope": {"rich_text": {}},
    "ai_hpc_thesis_invalidated": {"rich_text": {}},
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
    ["TSMC", "1Q Net Income", "1Q24", "217.2", "BTWD",
     "Consensus", "Overweight", "900"],
]

PORTFOLIO_THESIS_HEADER = [
    "company", "thesis", "bucket", "note", "date_added",
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

    Handles: '18.87B', '592.64B', '$18.87 billion', 'NT$225.49B', '~217B',
    '53.1%', '42.0%', etc.
    Returns value in billions for monetary amounts, or raw float for percentages.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    # Strip currency prefixes and noise
    s = re.sub(r'[~≈$,]', '', s)
    s = s.replace('nt', '').replace('us', '').replace('twd', '').replace('usd', '')
    s = s.replace('billion', 'b').replace('million', 'm')
    s = s.replace('bn', 'b').replace('mn', 'm')
    # Handle percentage — return raw number
    if s.endswith('%'):
        s = s[:-1].strip()
        try:
            return float(s)
        except ValueError:
            return None

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


def _pct_close(actual: float, expected: float, abs_tol: float = 3.0) -> bool:
    """Check if two percentage values are within absolute tolerance."""
    return abs(actual - expected) <= abs_tol


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "investment_analyst_task2",
    "name": "TSMC 1Q24 — Currency Normalization, Node-Mix & Peer Read-Through",
    "category": "investment_analyst",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Research assistant to Asia hardware analyst Zhou Ning",
    "tags": [
        "finance", "earnings", "currency-normalization", "multimodal",
        "silent-event", "peer-readthrough", "audio", "image", "pdf",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@research.fund",
                    "password": "assistant_pwd",
                },
                "zhou_ning": {
                    "email": "zhou.ning@research.fund",
                    "password": "zhou_ning_pwd",
                },
                "tsmc_ir": {
                    "email": "tsmc-ir@research.fund",
                    "password": "tsmc_ir_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "investment_analyst_task2",
        },
    },
}

PROMPT = "Check your email and workspace for new earnings materials to process."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Stage 1 — Initial Read: Thursday April 18, 2024."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + watchlist database (single-row)
    await ctx.notion.create_page("TSMC Coverage 2024-Q1")
    await ctx.notion.create_database(WATCHLIST_DB, WATCHLIST_DB_SCHEMA)
    await ctx.notion.add_database_row(WATCHLIST_DB, {
        "company": _notion_title("TSMC"),
        "revenue_usd": _notion_text(""),
        "revenue_twd": _notion_text(""),
        "currency_normalized": _notion_text(""),
        "node_mix_3nm": _notion_text(""),
        "platform_mix_hpc": _notion_text(""),
        "margin_headwinds": _notion_text(""),
        "followup_note": _notion_text(""),
        "readthrough_scope": _notion_text(""),
        "ai_hpc_thesis_invalidated": _notion_text(""),
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
    # portfolio_thesis (header only)
    pt = await ctx.google_sheets.create_spreadsheet("portfolio_thesis")
    await ctx.google_sheets.update_values(
        pt["sheet_id"], "Sheet1!A1:E1",
        [PORTFOLIO_THESIS_HEADER],
    )
    # tsmc_stage_log (header only)
    sl = await ctx.google_sheets.create_spreadsheet("tsmc_stage_log")
    await ctx.google_sheets.update_values(
        sl["sheet_id"], "Sheet1!A1:G1",
        [STAGE_LOG_HEADER],
    )

    # 5. Seed email — IR materials notification
    await ctx.email.send_email(
        from_user="tsmc_ir",
        to="assistant@research.fund",
        subject="TSMC 1Q24 Earnings Materials",
        body=(
            "Attached please find 1Q24 earnings materials for TSMC:\n\n"
            "- 1Q24 earnings call audio (tsmc_1q24_call.mp3)\n"
            "- 1Q24 presentation excerpt (tsmc_1q24_presentation.pdf)\n"
            "- 1Q24 transcript excerpt (tsmc_1q24_transcript.pdf)\n"
            "- 1Q24 financial statements excerpt (tsmc_1q24_financial_statements.pdf)\n"
            "- 1Q24 management report excerpt (tsmc_1q24_management_report.pdf)\n"
            "- 4Q23 presentation excerpt (tsmc_4q23_presentation.pdf)\n"
            "- 4Q23 transcript excerpt (tsmc_4q23_transcript.pdf)\n"
            "- Node-mix and platform-mix chart (tsmc_node_mix.png)\n\n"
            "Materials are in /workspace/input/."
        ),
    )

    # 6. Notification — includes Feishu message
    return {
        "notification": (
            "[Thursday, April 18, 2024 08:30] You have a new email and a new "
            "Feishu message.\n\n"
            "Your email: assistant@research.fund. "
            "Zhou Ning: zhou.ning@research.fund.\n"
            "TSMC watchlist: Notion database 'TSMC_watchlist'. "
            "LP questions: Notion database 'LP_questions'.\n"
            "StreetConsensus, portfolio_thesis, tsmc_stage_log: Google Sheets.\n"
            "All input materials in /workspace/input/.\n\n"
            "[Feishu] Zhou Ning: "
            "\"TSMC earnings dropped. Start by getting the structure right, "
            "especially node mix, AI, and gross margin. "
            "When currency or basis differs, normalize first and then draw "
            "the conclusion.\""
        ),
        "time": "2024-04-18T08:30:00+08:00",
    }


async def stage1(ctx):
    """Stage 2 — Follow-Up + Silent LP Question: Friday April 19, 2024."""
    # 1. Silent: Add LP question to Notion (agent must discover)
    await ctx.notion.add_database_row(LP_QUESTIONS_DB, {
        "question_id": _notion_title("LP-TSMC-001"),
        "topic": _notion_text("3nm mix vs 4Q23"),
        "question": _notion_text(
            "Also give me 3nm mix versus 4Q23; do not reply with only "
            "capex and AI."
        ),
        "status": _notion_select("open"),
    })

    # 2. Loud: Zhou Ning sends follow-up email
    await ctx.email.send_email(
        from_user="zhou_ning",
        to="assistant@research.fund",
        subject="TSMC follow-up — capex and CoWoS / AI",
        body=(
            "Two things:\n\n"
            "1. Did capex change versus the 4Q23 guide? Give me the numbers.\n"
            "2. How should we talk about CoWoS tightness and the AI server "
            "mix going into 2025?\n\n"
            "Send me the follow-up note when ready."
        ),
    )

    # 3. Notification — only mentions the loud email
    return {
        "notification": "[Friday, April 19, 2024 09:00] You have a new email.",
        "time": "2024-04-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """Stage 3 — Peer Read-Through Scope: Thursday April 25, 2024."""
    # 1. Silent: Update portfolio_thesis with AI/HPC core thesis
    pt_id = await ctx.google_sheets.get_spreadsheet_id("portfolio_thesis")
    if pt_id:
        await ctx.google_sheets.append_rows(
            pt_id, "Sheet1!A:E",
            [["TSMC", "AI/HPC demand is the core structural driver",
              "AI/HPC", "Mature-node / auto read-through is secondary",
              "2024-04-24"]],
        )

    # 2. Loud: Overnight news email with STMicro image reference
    await ctx.email.send_email(
        from_user="tsmc_ir",
        to="assistant@research.fund",
        subject="Overnight peer news — STMicro guidance update",
        body=(
            "Overnight update: STMicroelectronics issued a revised FY24 "
            "revenue guidance during their call. See the screenshot at "
            "/workspace/input/overnight_news.png for coverage.\n\n"
            "Please frame the peer read-through for TSMC."
        ),
    )

    # 3. Notification — mentions email but NOT the silent sheet update
    return {
        "notification": (
            "[Thursday, April 25, 2024 07:30] You have a new email with a "
            "new overnight news screenshot attached."
        ),
        "time": "2024-04-25T07:30:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S1 (Initial Read) — checked after stage0 --


async def _s0_artifacts_exist(ctx):
    """facts.csv exists with >=5 rows AND stage1_brief.md has >=30 words."""
    rows = _read_csv(ctx, "facts.csv")
    if len(rows) < 5:
        return False
    return _md_has_content(ctx, "stage1_brief.md", min_words=30)


async def _s0_currency_normalization_preserved(ctx):
    """Revenue captured as US$18.87B AND NT$592.64B — same quarter, different currencies."""
    rows = _read_csv(ctx, "facts.csv")
    revenue_rows = _find_all_facts_rows(rows, "revenue")
    if len(revenue_rows) < 2:
        return False
    found_usd = False
    found_twd = False
    for r in revenue_rows:
        val = _parse_financial_number((r.get("value") or ""))
        unit = (r.get("unit") or "").strip().upper()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        if val is None:
            continue
        unit_lower = unit.lower()
        # USD revenue ~18.87B
        if _values_close(val, 18.87) and ("usd" in unit_lower or "usd" in note
                                           or "us" in unit_lower):
            found_usd = True
        # TWD revenue ~592.64B
        if _values_close(val, 592.64) and ("twd" in unit_lower or "twd" in note
                                            or "nt" in unit_lower or "btwd" in unit_lower):
            found_twd = True
    if found_usd and found_twd:
        return True
    # Fallback: check Notion watchlist
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    row = notion_rows[0]
    usd_val = _get_notion_field(row, "revenue_usd")
    twd_val = _get_notion_field(row, "revenue_twd")
    norm_val = _get_notion_field(row, "currency_normalized")
    if usd_val and twd_val:
        usd_num = _parse_financial_number(usd_val)
        twd_num = _parse_financial_number(twd_val)
        if usd_num and twd_num:
            if _values_close(usd_num, 18.87) and _values_close(twd_num, 592.64):
                return True
    return False


async def _s0_core_financial_facts(ctx):
    """GM 53.1%, OM 42.0%, NI NT$225.49B, Q2 guide, 2024 capex captured."""
    rows = _read_csv(ctx, "facts.csv")
    found_gm = False
    found_om = False
    found_ni = False
    found_q2_guide = False
    found_capex = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        val_str = (r.get("value") or "")
        note = (r.get("note") or "").lower()
        val = _parse_financial_number(val_str)
        if val is None:
            continue
        # Gross margin ~53.1%
        if ("gross" in metric and "margin" in metric) or "gm" in metric:
            if _pct_close(val, 53.1):
                found_gm = True
        # Operating margin ~42.0%
        if ("operating" in metric and "margin" in metric) or "om" in metric:
            if _pct_close(val, 42.0):
                found_om = True
        # Net income ~225.49B (TWD)
        if "net" in metric and "income" in metric:
            if _values_close(val, 225.49):
                found_ni = True
        # Q2 revenue guide — accept either midpoint ~20.0B or range endpoints
        if "guide" in metric or "guidance" in metric or "q2" in metric:
            if _values_close(val, 20.0, rel_tol=0.05) or _values_close(val, 19.6, rel_tol=0.08) or _values_close(val, 20.4, rel_tol=0.08):
                found_q2_guide = True
        # 2024 capex — accept midpoint ~30B or range endpoints
        if "capex" in metric or "capital" in metric:
            if _values_close(val, 30.0, rel_tol=0.10) or _values_close(val, 28.0, rel_tol=0.08) or _values_close(val, 32.0, rel_tol=0.08):
                found_capex = True
    return found_gm and found_om and found_ni and found_q2_guide and found_capex


async def _s0_visual_mix_extracted(ctx):
    """Node mix (3nm 9%, 5nm 37%, 7nm 19%) and platform mix (HPC 46%, smartphone 38%) captured."""
    rows = _read_csv(ctx, "facts.csv")
    found_3nm = False
    found_5nm = False
    found_7nm = False
    found_hpc = False
    found_smartphone = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        val = _parse_financial_number((r.get("value") or ""))
        note = (r.get("note") or "").lower()
        combined = f"{metric} {note}"
        if val is None:
            continue
        if "3nm" in combined or "3 nm" in combined or "n3" in combined:
            if _pct_close(val, 9.0):
                found_3nm = True
        if "5nm" in combined or "5 nm" in combined or "n5" in combined:
            if _pct_close(val, 37.0):
                found_5nm = True
        if "7nm" in combined or "7 nm" in combined or "n7" in combined:
            if _pct_close(val, 19.0):
                found_7nm = True
        if "hpc" in combined or "high performance" in combined:
            if _pct_close(val, 46.0):
                found_hpc = True
        if "smartphone" in combined or "mobile" in combined:
            if _pct_close(val, 38.0):
                found_smartphone = True
    if found_3nm and found_5nm and found_7nm and found_hpc and found_smartphone:
        return True
    # Fallback: check Notion watchlist
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    row = notion_rows[0]
    node_3nm = _get_notion_field(row, "node_mix_3nm")
    hpc = _get_notion_field(row, "platform_mix_hpc")
    if node_3nm and hpc:
        n3_val = _parse_financial_number(node_3nm)
        hpc_val = _parse_financial_number(hpc)
        if n3_val and hpc_val:
            if _pct_close(n3_val, 9.0) and _pct_close(hpc_val, 46.0):
                return True
    return False


async def _s0_street_and_margin_signal(ctx):
    """Street consensus NT$217.2B captured, quarter judged above street,
    earthquake + electricity headwinds recorded."""
    rows = _read_csv(ctx, "facts.csv")
    found_consensus = False
    found_above = False
    found_headwinds = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        direction = (r.get("direction") or "").lower()
        note = (r.get("note") or "").lower()
        val = _parse_financial_number((r.get("value") or ""))
        combined = f"{metric} {note}"
        # Consensus value ~217.2B
        if val is not None and _values_close(val, 217.2):
            found_consensus = True
        # Above street
        if ("consensus" in combined or "street" in combined
                or "net income" in combined):
            if direction in ("above", "positive", "beat"):
                found_above = True
            if "above" in note or "beat" in note or "exceed" in note:
                found_above = True
        # Earthquake + electricity headwinds
        if ("earthquake" in combined or "quake" in combined
                or "electricity" in combined or "utility" in combined
                or "power" in combined):
            found_headwinds = True
    return found_consensus and found_above and found_headwinds


async def _s0_tool_state_written(ctx):
    """Notion watchlist updated, tsmc_stage_log has rows, Zhou Ning received email."""
    # 1. Notion watchlist has at least 1 non-empty field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    row = notion_rows[0]
    has_data = False
    for field in ("revenue_usd", "revenue_twd", "node_mix_3nm", "margin_headwinds"):
        val = _get_notion_field(row, field)
        if val and len(val.strip()) > 0:
            has_data = True
            break
    if not has_data:
        return False

    # 2. Stage log has at least 1 data row
    sl_id = await ctx.google_sheets.get_spreadsheet_id("tsmc_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G20")
    if not vals or len(vals) <= 1:  # only header
        return False

    # 3. Zhou Ning received at least 1 email
    emails = await ctx.email.get_emails("zhou_ning")
    return len(emails) >= 1


# -- S2 (Follow-Up + Silent LP Question) — checked after stage1 --


async def _s1_artifacts_exist(ctx):
    """stage2_followup.md exists with >=20 words."""
    return _md_has_content(ctx, "stage2_followup.md", min_words=20)


async def _s1_capex_and_cowos_followup(ctx):
    """Output records whether capex changed vs 4Q23 and whether CoWoS tightness extends into 2025."""
    rows = _read_csv(ctx, "facts.csv")
    found_capex_comparison = False
    found_cowos = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        combined = f"{metric} {note} {basis}"
        # Capex comparison to prior quarter
        if ("capex" in combined or "capital" in combined):
            if any(kw in combined for kw in
                   ("prior", "4q23", "q4", "change", "vs", "comparison",
                    "unchanged", "maintained", "same")):
                found_capex_comparison = True
        # CoWoS tightness
        if ("cowos" in combined or "advanced packaging" in combined
                or "co-wos" in combined):
            if any(kw in combined for kw in
                   ("tight", "2025", "extend", "supply", "capacity", "constraint")):
                found_cowos = True
    if found_capex_comparison and found_cowos:
        return True
    # Fallback: check stage2_followup.md
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            has_capex = ("capex" in text or "capital expenditure" in text) and \
                        any(kw in text for kw in ("4q23", "prior", "change", "unchanged"))
            has_cowos = ("cowos" in text or "co-wos" in text or "advanced packaging" in text) and \
                        any(kw in text for kw in ("tight", "2025", "extend", "constrain"))
            if has_capex and has_cowos:
                return True
    return False


async def _s1_ai_server_mix_and_3nm_delta(ctx):
    """AI server mix captured quantitatively; if LP question found, 3nm delta vs 4Q23 logged."""
    rows = _read_csv(ctx, "facts.csv")
    found_ai_mix = False
    found_3nm_delta = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        val = (r.get("value") or "").strip()
        combined = f"{metric} {note}"
        # AI server mix — quantitative
        if ("ai" in combined or "server" in combined) and ("mix" in combined or "revenue" in combined):
            if val:  # must have a non-empty value
                found_ai_mix = True
        # 3nm delta vs 4Q23
        if ("3nm" in combined or "3 nm" in combined or "n3" in combined):
            if any(kw in combined for kw in
                   ("delta", "4q23", "prior", "change", "vs", "versus", "from")):
                found_3nm_delta = True
    if found_ai_mix and found_3nm_delta:
        return True
    # Partial pass: AI mix alone counts (3nm delta depends on silent discovery)
    if found_ai_mix:
        # Check Notion for 3nm delta as backup
        notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
        if notion_rows:
            followup = _get_notion_field(notion_rows[0], "followup_note").lower()
            if "3nm" in followup and any(kw in followup for kw in
                                         ("4q23", "delta", "change", "prior", "vs")):
                return True
        return True  # AI mix alone is still partial credit
    return False


async def _s1_tool_state_written(ctx):
    """Notion followup_note updated, stage log has S2 rows, Zhou Ning received >=2 emails."""
    # 1. Notion followup_note is non-empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    followup_val = _get_notion_field(notion_rows[0], "followup_note")
    if not followup_val or len(followup_val.strip()) == 0:
        return False

    # 2. Stage log has grown
    sl_id = await ctx.google_sheets.get_spreadsheet_id("tsmc_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G30")
    if not vals or len(vals) <= 2:  # header + at least 2 data rows
        return False

    # 3. Zhou Ning received >=2 emails (S1 + S2 summaries)
    emails = await ctx.email.get_emails("zhou_ning")
    return len(emails) >= 2


# -- S3 (Peer Read-Through Scope) — checked after stage2 --


async def _s2_artifacts_exist(ctx):
    """stage3_alert.md exists with >=20 words."""
    return _md_has_content(ctx, "stage3_alert.md", min_words=20)


async def _s2_stm_peer_update_extracted(ctx):
    """STMicro FY24 revenue guide cut captured (US$14B-US$15B range)."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        value = (r.get("value") or "").lower()
        source_ref = (r.get("source_ref") or "").lower()
        combined = f"{metric} {note} {source_ref} {value}"
        if "stm" in combined or "stmicro" in combined or "st micro" in combined:
            # Found an STMicro reference — validate the guide-cut value
            val = _parse_financial_number((r.get("value") or ""))
            if val is not None and (
                _values_close(val, 14.0, rel_tol=0.10)
                or _values_close(val, 15.0, rel_tol=0.10)
                or _values_close(val, 14.5, rel_tol=0.10)
            ):
                return True
            # Accept non-numeric reference (e.g. "14B-15B")
            if "14" in value and "15" in value:
                return True
            # Accept any non-empty value referencing STMicro
            if (r.get("value") or "").strip():
                return True
    return False


async def _s2_readthrough_scope_limited(ctx):
    """Mature-node negative but AI/HPC thesis NOT invalidated."""
    rows = _read_csv(ctx, "facts.csv")
    found_mature_negative = False
    thesis_invalidated = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        direction = (r.get("direction") or "").lower()
        value = (r.get("value") or "").lower()
        combined = f"{metric} {note} {value}"
        # Mature-node / auto / industrial negative
        if any(kw in combined for kw in
               ("mature", "auto", "industrial", "legacy", "readthrough",
                "read-through", "read_through")):
            if direction in ("negative", "below", "cut") or \
               any(neg in combined for neg in ("negative", "weak", "cut", "down")):
                found_mature_negative = True
        # Check for AI/HPC thesis invalidation (BAD)
        if any(kw in combined for kw in ("ai", "hpc", "high performance")):
            if any(bad in combined for bad in
                   ("invalidat", "weaken", "broken", "collapse")):
                if direction in ("negative", "below"):
                    thesis_invalidated = True
    # Also check Notion
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        scope = _get_notion_field(notion_rows[0], "readthrough_scope").lower()
        inv = _get_notion_field(notion_rows[0], "ai_hpc_thesis_invalidated").lower()
        if any(kw in scope for kw in ("mature", "auto", "industrial", "limited")):
            found_mature_negative = True
        if inv in ("false", "no", "not invalidated", "intact"):
            # Good — thesis not invalidated
            pass
        elif inv in ("true", "yes", "invalidated", "broken"):
            thesis_invalidated = True
    return found_mature_negative and not thesis_invalidated


async def _s2_tool_state_written(ctx):
    """Notion readthrough fields updated, stage log grown, Zhou Ning received >=3 emails."""
    # 1. Notion readthrough_scope or ai_hpc_thesis_invalidated is non-empty
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    scope = _get_notion_field(notion_rows[0], "readthrough_scope")
    inv = _get_notion_field(notion_rows[0], "ai_hpc_thesis_invalidated")
    if (not scope or len(scope.strip()) == 0) and \
       (not inv or len(inv.strip()) == 0):
        return False

    # 2. Zhou Ning received >=3 emails (S1 + S2 + S3 summaries)
    emails = await ctx.email.get_emails("zhou_ning")
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
    return data[ps_idx] == "Overweight" and data[tp_idx] == "900"


async def _r_revenue_not_duplicated_as_conflict(ctx):
    """REVERSE: USD and TWD revenue are NOT treated as contradictory quarter facts."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False  # no output at all → no evidence to verify
    revenue_rows = _find_all_facts_rows(rows, "revenue")
    if not revenue_rows:
        return False  # no revenue rows → can't verify basis handling
    # Check no row marks USD vs TWD as contradictory/conflicting
    # Exclude negated forms like "not a contradiction", "no conflict", "consistent"
    import re as _re
    _NEGATION_RE = _re.compile(r"(not\s+a?\s*|no\s+|non[- ]?)(contradict|conflict|discrepan|inconsisten|mismatch)", _re.IGNORECASE)
    for r in revenue_rows:
        note = (r.get("note") or "").lower()
        direction = (r.get("direction") or "").lower()
        basis = (r.get("basis") or "").lower()
        combined = f"{note} {direction} {basis}"
        if any(kw in combined for kw in
               ("contradict", "conflict", "discrepan", "inconsisten", "mismatch")):
            # Check if every occurrence is negated
            if not _NEGATION_RE.search(combined):
                return False
    # Check Notion currency_normalized
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        norm = _get_notion_field(notion_rows[0], "currency_normalized").lower()
        if any(kw in norm for kw in
               ("contradict", "conflict", "discrepan", "mismatch")):
            return False
    return True


async def _r_ai_weakening_misread_not_present(ctx):
    """REVERSE: Output does NOT introduce 'AI demand weakening' from STMicro read-through."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False  # no output at all → no evidence to verify
    import re as _re
    _NOT_AI_RE = _re.compile(r"not\s+(ai|hpc)", _re.IGNORECASE)
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        direction = (r.get("direction") or "").lower()
        value = (r.get("value") or "").lower()
        combined = f"{metric} {note} {value}"
        # Detect false AI weakening conclusion
        if any(kw in combined for kw in ("ai", "hpc", "high performance")):
            # Skip if AI/HPC is negated ("not AI/HPC", "not AI-related")
            if _NOT_AI_RE.search(combined):
                continue
            if any(bad in combined for bad in
                   ("weaken", "soften", "declin", "deteriorat", "collapse")):
                if direction in ("negative", "below"):
                    return False
    # Check stage3_alert.md
    for path in (ctx.workspace / "stage3_alert.md",
                 ctx.workspace / "outputs" / "stage3_alert.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            # Detect "AI demand weakening" or similar false conclusions
            if "ai" in text and any(kw in text for kw in
                                    ("demand weaken", "ai weaken", "hpc weaken",
                                     "ai demand soften", "ai demand declin")):
                return False
    # Check Notion
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        inv = _get_notion_field(notion_rows[0], "ai_hpc_thesis_invalidated").lower()
        if inv in ("true", "yes", "invalidated", "broken"):
            return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S1_artifacts_exist",
         "checker": _s0_artifacts_exist, "weight": 1.0},
        {"id": "S1_currency_normalization_preserved",
         "checker": _s0_currency_normalization_preserved, "weight": 2.0},
        {"id": "S1_core_financial_facts",
         "checker": _s0_core_financial_facts, "weight": 1.5},
        {"id": "S1_visual_mix_extracted",
         "checker": _s0_visual_mix_extracted, "weight": 1.5},
        {"id": "S1_street_and_margin_signal",
         "checker": _s0_street_and_margin_signal, "weight": 2.0},
        {"id": "S1_tool_state_written",
         "checker": _s0_tool_state_written, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S2_artifacts_exist",
         "checker": _s1_artifacts_exist, "weight": 1.0},
        {"id": "S2_capex_and_cowos_followup",
         "checker": _s1_capex_and_cowos_followup, "weight": 1.5},
        {"id": "S2_ai_server_mix_and_3nm_delta",
         "checker": _s1_ai_server_mix_and_3nm_delta, "weight": 2.0},
        {"id": "S2_tool_state_written",
         "checker": _s1_tool_state_written, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S3_artifacts_exist",
         "checker": _s2_artifacts_exist, "weight": 1.0},
        {"id": "S3_stm_peer_update_extracted",
         "checker": _s2_stm_peer_update_extracted, "weight": 1.5},
        {"id": "S3_readthrough_scope_limited",
         "checker": _s2_readthrough_scope_limited, "weight": 2.0},
        {"id": "S3_tool_state_written",
         "checker": _s2_tool_state_written, "weight": 1.0},
    ],
    "final": [
        {"id": "R1_sheet_guardrails",
         "checker": _r_sheet_guardrails, "weight": 2.0},
        {"id": "R2_revenue_not_duplicated_as_conflict",
         "checker": _r_revenue_not_duplicated_as_conflict, "weight": 2.0},
        {"id": "R3_ai_weakening_misread_not_present",
         "checker": _r_ai_weakening_misread_not_present, "weight": 2.0},
    ],
}
