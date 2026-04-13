"""PayPal Q1 2024 — revenue vs TM$, mix quality, silent LP question.

Environments: filesystem, email, notion, google_sheets
3 stages: initial read → follow-up + silent LP question → overnight peer framing
17 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

WATCHLIST_DB = "PayPal_watchlist"
LP_QUESTIONS_DB = "LP_questions"

WATCHLIST_DB_SCHEMA = {
    "company": {"title": {}},
    "q1_revenue_growth": {"rich_text": {}},
    "q1_tm_dollars": {"rich_text": {}},
    "mix_quality_view": {"rich_text": {}},
    "guide_change_view": {"rich_text": {}},
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
PAYMENTS_CONSENSUS_HEADER = [
    "company", "metric", "period", "value", "unit", "source",
    "position_status", "target_price",
]
PAYMENTS_CONSENSUS_ROWS = [
    ["PayPal", "Q1 revenue growth guide", "Q1 2024",
     "~6.5% spot / 7% FXN", "PCT", "Prior Q4 call",
     "Neutral", "68"],
    ["PayPal", "FY24 non-GAAP EPS view", "FY24",
     "in line with prior year", "qualitative", "Prior Q4 call",
     "Neutral", "68"],
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
    """Normalize financial strings to a comparable float (in billions)."""
    if not raw:
        return None
    s = str(raw).strip().lower()
    s = re.sub(r'[~≈$,]', '', s)
    s = s.replace('billion', 'b').replace('million', 'm')
    s = s.replace('bn', 'b').replace('mn', 'm')
    multiplier = 1.0
    if s.endswith('b'):
        s = s[:-1]
    elif s.endswith('m'):
        multiplier = 0.001
        s = s[:-1]
    elif s.endswith('%'):
        s = s[:-1]
    try:
        return float(s.strip()) * multiplier
    except ValueError:
        return None


def _values_close(actual: float, expected: float, rel_tol: float = 0.08) -> bool:
    if expected == 0:
        return abs(actual) < 0.01
    return abs(actual - expected) / abs(expected) <= rel_tol


def _md_has_content(ctx, filename: str, min_words: int = 30) -> bool:
    for path in (ctx.workspace / filename, ctx.workspace / "outputs" / filename):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").strip()
            if len(text.split()) >= min_words:
                return True
    return False


def _find_all_facts_rows(rows: list[dict], metric: str) -> list[dict]:
    return [r for r in rows if metric.lower() in (r.get("metric") or "").strip().lower()]


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "investment_analyst_task6",
    "name": "PayPal Q1 2024 — Revenue vs TM$, Mix Quality & Peer Monitor",
    "category": "investment_analyst",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L3",
    "role": "Associate consultant to transformation partner Mia Sun",
    "tags": [
        "finance", "payments", "mix-quality", "basis-separation",
        "silent-event", "peer-framing", "methodology-change", "image", "pdf",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@research.fund",
                    "password": "assistant_pwd",
                },
                "mia_sun": {
                    "email": "mia.sun@research.fund",
                    "password": "mia_sun_pwd",
                },
                "pypl_ir": {
                    "email": "pypl-ir@research.fund",
                    "password": "pypl_ir_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "investment_analyst_task6",
        },
    },
}

PROMPT = "Check your email and workspace for new earnings materials to process."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Stage 1 — Initial Read: Tuesday April 30, 2024."""
    # 1. Upload assets
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + watchlist database
    await ctx.notion.create_page("PayPal Margin Quality 2024-Q1")
    await ctx.notion.create_database(WATCHLIST_DB, WATCHLIST_DB_SCHEMA)
    await ctx.notion.add_database_row(WATCHLIST_DB, {
        "company": _notion_title("PayPal"),
        "q1_revenue_growth": _notion_text(""),
        "q1_tm_dollars": _notion_text(""),
        "mix_quality_view": _notion_text(""),
        "guide_change_view": _notion_text(""),
        "lp_followup_answer": _notion_text(""),
        "peer_frame": _notion_text(""),
        "last_updated_stage": _notion_text(""),
    })

    # 3. Create LP_questions database (empty)
    await ctx.notion.create_database(LP_QUESTIONS_DB, LP_QUESTIONS_DB_SCHEMA)

    # 4. Create Google Sheets
    pc = await ctx.google_sheets.create_spreadsheet("PaymentsConsensus")
    await ctx.google_sheets.update_values(
        pc["sheet_id"], "Sheet1!A1:H3",
        [PAYMENTS_CONSENSUS_HEADER] + PAYMENTS_CONSENSUS_ROWS,
    )
    pm = await ctx.google_sheets.create_spreadsheet("peer_monitor")
    await ctx.google_sheets.update_values(
        pm["sheet_id"], "Sheet1!A1:G1",
        [PEER_MONITOR_HEADER],
    )
    sl = await ctx.google_sheets.create_spreadsheet("pypl_stage_log")
    await ctx.google_sheets.update_values(
        sl["sheet_id"], "Sheet1!A1:G1",
        [STAGE_LOG_HEADER],
    )

    # 5. Seed email — materials notification
    await ctx.email.send_email(
        from_user="pypl_ir",
        to="assistant@research.fund",
        subject="PayPal Q1 2024 Earnings Materials",
        body=(
            "Q1 2024 materials for PayPal:\n\n"
            "- Q1 2024 earnings release (pypl_q1_2024_earnings_release.html)\n"
            "- Q1 2024 investor update (pypl_q1_2024_investor_update.pdf)\n"
            "- Q4 2023 investor update (pypl_q4_2023_investor_update.pdf)\n"
            "- Q4 2023 results context (pypl_q4_2023_results.html)\n"
            "- Block Q1 2024 shareholder letter (block_q1_2024_shareholder_letter.pdf)\n"
            "- Reuters market reaction (reuters_paypal_q1_results.html)\n\n"
            "Materials are in /workspace/input/."
        ),
    )

    # 6. Notification
    return {
        "notification": (
            "[Tuesday, April 30, 2024 08:30] You have a new email and a new "
            "Feishu message.\n\n"
            "Your email: assistant@research.fund. "
            "Mia Sun: mia.sun@research.fund.\n"
            "PayPal margin note: Notion database 'PayPal_watchlist'. "
            "LP questions: Notion database 'LP_questions'.\n"
            "PaymentsConsensus, peer_monitor, pypl_stage_log: Google Sheets.\n"
            "All input materials in /workspace/input/.\n\n"
            "[Feishu] Mia Sun: "
            "\"Need a first steering card on margin quality. "
            "Keep TPV, revenue, TM$, and new-vs-old non-GAAP bases separate. "
            "Do not let a volume-led beat become a simplistic margin-success "
            "story.\""
        ),
        "time": "2024-04-30T08:30:00+08:00",
    }


async def stage1(ctx):
    """Stage 2 — Follow-Up + Silent LP Question: Wednesday May 1, 2024."""
    # 1. Silent: Add LP question to Notion
    await ctx.notion.add_database_row(LP_QUESTIONS_DB, {
        "question_id": _notion_title("LP-PYPL-001"),
        "topic": _notion_text("margin expansion quality"),
        "question": _notion_text(
            "Is the margin expansion really structural, or did Q1 mostly "
            "benefit from interest income on customer balances, lower losses, "
            "and deferred marketing spend? Also, please do not lose the "
            "old-vs-new non-GAAP methodology basis change in the narrative."
        ),
        "status": _notion_select("open"),
    })

    # 2. Loud: Mia Sun sends follow-up email
    await ctx.email.send_email(
        from_user="mia_sun",
        to="assistant@research.fund",
        subject="PayPal follow-up — guide change and TM$",
        body=(
            "Two things:\n\n"
            "1. Compare the current guide and non-GAAP methodology versus "
            "the prior-quarter setup — what moved?\n"
            "2. Give me one clean sentence on transaction-margin quality.\n\n"
            "Send the follow-up note when ready."
        ),
    )

    # 3. Notification — only mentions the loud email
    return {
        "notification": "[Wednesday, May 1, 2024 09:00] You have a new email.",
        "time": "2024-05-01T09:00:00+08:00",
    }


async def stage2(ctx):
    """Stage 3 — Overnight Peer Framing: Thursday May 2, 2024."""
    # 1. Silent: Update peer_monitor with Block outlook
    pm_id = await ctx.google_sheets.get_spreadsheet_id("peer_monitor")
    if pm_id:
        await ctx.google_sheets.append_rows(
            pm_id, "Sheet1!A:G",
            [["Block", "2024 gross profit outlook", "FY24",
              "8.78B vs prior 8.65B", "BUSD", "Block Q1 2024 letter",
              "2024-05-01"]],
        )
        await ctx.google_sheets.append_rows(
            pm_id, "Sheet1!A:G",
            [["Block", "2024 adjusted OI outlook", "FY24",
              "1.30B vs prior 1.15B", "BUSD", "Block Q1 2024 letter",
              "2024-05-01"]],
        )

    # 2. Loud: Overnight news email
    await ctx.email.send_email(
        from_user="pypl_ir",
        to="assistant@research.fund",
        subject="Overnight peer news — Block updated outlook",
        body=(
            "Overnight update: Block raised its 2024 outlook in the Q1 "
            "shareholder letter. See the screenshot at "
            "/workspace/input/pypl_stage3_overnight_payments_peer.png.\n\n"
            "Please frame the peer read-through for PayPal."
        ),
    )

    # 3. Notification
    return {
        "notification": (
            "[Thursday, May 2, 2024 07:30] You have a new email with a "
            "new overnight peer screenshot attached."
        ),
        "time": "2024-05-02T07:30:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S1 (Initial Read) — checked after stage0 --


async def _s0_artifacts_exist(ctx):
    """facts.csv exists with ≥5 rows AND stage1_brief.md has ≥30 words."""
    rows = _read_csv(ctx, "facts.csv")
    if len(rows) < 5:
        return False
    return _md_has_content(ctx, "stage1_brief.md", min_words=30)


async def _s0_spot_vs_fxn_growth(ctx):
    """facts.csv has separate rows for revenue growth 9% spot and 10% FX-neutral."""
    rows = _read_csv(ctx, "facts.csv")
    revenue_rows = _find_all_facts_rows(rows, "revenue")
    if len(revenue_rows) < 2:
        revenue_rows = [r for r in rows
                        if "growth" in (r.get("metric") or "").lower()
                        and "revenue" in (r.get("metric") or "").lower()]
    bases = set()
    for r in revenue_rows:
        b = (r.get("basis") or "").strip().lower()
        if b:
            bases.add(b)
    # Need at least 2 distinct bases (spot/reported + fx_neutral/constant_currency)
    if len(bases) < 2:
        return False
    # Verify numeric values are reasonable
    found_spot = False
    found_fxn = False
    for r in revenue_rows:
        val = _parse_financial_number((r.get("value") or ""))
        basis = (r.get("basis") or "").lower()
        if val is None:
            continue
        if any(kw in basis for kw in ("spot", "reported")) and _values_close(val, 9.0, 0.15):
            found_spot = True
        if any(kw in basis for kw in ("fx", "neutral", "constant")) and _values_close(val, 10.0, 0.15):
            found_fxn = True
    return found_spot and found_fxn


async def _s0_tpv_vs_tm_dollars(ctx):
    """TPV and TM$ captured as separate rows, not collapsed."""
    rows = _read_csv(ctx, "facts.csv")
    has_tpv = False
    has_tm = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        if "tpv" in metric or "total payment volume" in metric:
            has_tpv = True
        if "tm$" in metric or "tm " in metric or "transaction margin" in metric:
            has_tm = True
    return has_tpv and has_tm


async def _s0_actual_vs_prior_guide(ctx):
    """Actual Q1 revenue growth recorded as above prior guide."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        direction = (r.get("direction") or "").lower()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        combined = f"{metric} {note} {basis}"
        if ("guide" in combined or "consensus" in combined
                or "prior" in combined):
            if direction in ("above", "positive", "beat", "ahead"):
                return True
            if any(kw in note for kw in ("above", "beat", "ahead", "exceeded")):
                return True
    # Check Notion
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    for r in notion_rows:
        rev = _get_notion_field(r, "q1_revenue_growth").lower()
        if "above" in rev or "beat" in rev or "exceeded" in rev:
            return True
    return False


async def _s0_mix_watch_items(ctx):
    """4 watch items: PSP dilution, branded/PSP structure, interest/loss tailwind, H2 deferred spend."""
    rows = _read_csv(ctx, "facts.csv")
    items_found = 0
    watch_patterns = [
        ["psp", "mix", "dilution", "braintree", "unbranded"],
        ["branded", "checkout"],
        ["interest", "balance", "loss", "lower loss"],
        ["defer", "h2", "marketing", "investment"],
    ]
    for patterns in watch_patterns:
        for r in rows:
            combined = ((r.get("metric") or "") + " " + (r.get("note") or "")).lower()
            if any(p in combined for p in patterns):
                items_found += 1
                break
    return items_found >= 3


async def _s0_tool_state_written(ctx):
    """Notion updated, pypl_stage_log has rows, Mia Sun received email."""
    # 1. Notion has data
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    has_data = False
    for field in ("q1_revenue_growth", "q1_tm_dollars", "mix_quality_view"):
        val = _get_notion_field(notion_rows[0], field)
        if val and len(val.strip()) > 0:
            has_data = True
            break
    if not has_data:
        return False

    # 2. Stage log has data
    sl_id = await ctx.google_sheets.get_spreadsheet_id("pypl_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G20")
    if not vals or len(vals) <= 1:
        return False

    # 3. Mia Sun received email
    emails = await ctx.email.get_emails("mia_sun")
    return len(emails) >= 1


# -- S2 (Follow-Up + Silent LP Question) — checked after stage1 --


async def _s1_artifacts_exist(ctx):
    """stage2_followup.md exists with ≥20 words."""
    return _md_has_content(ctx, "stage2_followup.md", min_words=20)


async def _s1_methodology_bridge(ctx):
    """Old vs new non-GAAP method EPS comparisons logged in facts.csv."""
    rows = _read_csv(ctx, "facts.csv")
    has_methodology = False
    has_eps_data = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        combined = f"{metric} {note} {basis}"
        if any(kw in combined for kw in ("method", "gaap", "sbc", "stock-based")):
            has_methodology = True
        if "eps" in combined or "earnings per share" in combined:
            val = _parse_financial_number((r.get("value") or ""))
            if val is not None:
                has_eps_data = True
    return has_methodology and has_eps_data


async def _s1_guide_change(ctx):
    """Prior FY24 view vs current FY24 view explicitly logged."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        combined = f"{metric} {note} {basis}"
        if any(kw in combined for kw in ("prior", "fy24", "guidance", "guide")):
            if any(kw in combined for kw in
                   ("change", "vs", "versus", "compared", "current", "update")):
                return True
    # Check Notion guide_change_view
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    for r in notion_rows:
        gcv = _get_notion_field(r, "guide_change_view")
        if gcv and len(gcv.strip()) > 10:
            return True
    return False


async def _s1_lp_followup_answered(ctx):
    """If LP question planted, structural-vs-timing concern answered."""
    # Primary: Notion lp_followup_answer field
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if notion_rows:
        val = _get_notion_field(notion_rows[0], "lp_followup_answer")
        if val and len(val.strip()) > 20:
            return True
    # Secondary: facts.csv with silent_followup basis
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        basis = (r.get("basis") or "").lower()
        note = (r.get("note") or "").lower()
        combined = f"{basis} {note}"
        if any(kw in combined for kw in
               ("structural", "timing", "tailwind", "lp", "followup")):
            if "silent" in basis or "followup" in basis or "lp" in basis:
                return True
    # Tertiary: stage2_followup.md content
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if ("structural" in text or "timing" in text) and "margin" in text:
                return True
    return False


async def _s1_tool_state_written(ctx):
    """Notion advanced, stage log grown, Mia Sun received ≥2 emails."""
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    stage_val = _get_notion_field(notion_rows[0], "last_updated_stage")
    if not stage_val or len(stage_val.strip()) == 0:
        return False
    sl_id = await ctx.google_sheets.get_spreadsheet_id("pypl_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G30")
    if not vals or len(vals) <= 2:
        return False
    emails = await ctx.email.get_emails("mia_sun")
    return len(emails) >= 2


# -- S3 (Overnight Peer Framing) — checked after stage2 --


async def _s2_artifacts_exist(ctx):
    """stage3_alert.md exists with ≥20 words."""
    return _md_has_content(ctx, "stage3_alert.md", min_words=20)


async def _s2_block_peer_extracted(ctx):
    """facts.csv captures Block's updated outlook facts."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        source_ref = (r.get("source_ref") or "").lower()
        combined = f"{metric} {note} {source_ref}"
        if "block" in combined or "sq" in combined:
            if (r.get("value") or "").strip():
                return True
    return False


async def _s2_peer_framing_preserved(ctx):
    """Separate aspects: sector resilience + PayPal credibility + mix-quality debate."""
    rows = _read_csv(ctx, "facts.csv")
    s3_rows = []
    for r in rows:
        stage = (r.get("stage") or "").strip()
        if stage in ("3", "S3", "stage3"):
            s3_rows.append(r)
    if len(s3_rows) < 2:
        return False
    has_peer = False
    has_own = False
    for r in s3_rows:
        combined = ((r.get("metric") or "") + " " + (r.get("note") or "")).lower()
        if any(kw in combined for kw in ("block", "peer", "sector")):
            has_peer = True
        if any(kw in combined for kw in ("paypal", "pypl", "mix", "tm$", "credib")):
            has_own = True
    return has_peer and has_own


async def _s2_tool_state_written(ctx):
    """Notion peer_frame updated, Mia Sun received ≥3 emails."""
    notion_rows = await ctx.notion.query_db(WATCHLIST_DB)
    if not notion_rows:
        return False
    pf = _get_notion_field(notion_rows[0], "peer_frame")
    if not pf or len(pf.strip()) == 0:
        return False
    emails = await ctx.email.get_emails("mia_sun")
    return len(emails) >= 3


# -- Red-Line Checks (final) --


async def _r_methodology_not_hidden(ctx):
    """REVERSE: Non-GAAP methodology change is not silently ignored."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False
    for r in rows:
        combined = ((r.get("metric") or "") + " " + (r.get("note") or "")
                    + " " + (r.get("basis") or "")).lower()
        if any(kw in combined for kw in
               ("method", "non-gaap", "sbc", "stock-based", "old method",
                "new method", "prior method")):
            return True
    # Check stage2_followup.md
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if "method" in text and ("gaap" in text or "sbc" in text):
                return True
    return False


async def _r_volume_and_margin_not_collapsed(ctx):
    """REVERSE: TPV, revenue, and TM$ remain as distinct metric entries."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False
    metrics_found = set()
    for r in rows:
        metric = (r.get("metric") or "").lower()
        if "tpv" in metric or "total payment volume" in metric:
            metrics_found.add("tpv")
        if ("revenue" in metric and "tpv" not in metric
                and "tm" not in metric):
            metrics_found.add("revenue")
        if "tm$" in metric or "tm " in metric or "transaction margin" in metric:
            metrics_found.add("tm")
    return len(metrics_found) >= 3


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S1_artifacts_exist",
         "checker": _s0_artifacts_exist, "weight": 1.0},
        {"id": "S1_spot_vs_fxn_growth",
         "checker": _s0_spot_vs_fxn_growth, "weight": 2.0},
        {"id": "S1_tpv_vs_tm_dollars",
         "checker": _s0_tpv_vs_tm_dollars, "weight": 2.0},
        {"id": "S1_actual_vs_prior_guide",
         "checker": _s0_actual_vs_prior_guide, "weight": 1.5},
        {"id": "S1_mix_watch_items",
         "checker": _s0_mix_watch_items, "weight": 1.5},
        {"id": "S1_tool_state_written",
         "checker": _s0_tool_state_written, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S2_artifacts_exist",
         "checker": _s1_artifacts_exist, "weight": 1.0},
        {"id": "S2_methodology_bridge",
         "checker": _s1_methodology_bridge, "weight": 2.0},
        {"id": "S2_guide_change",
         "checker": _s1_guide_change, "weight": 1.5},
        {"id": "S2_lp_followup_answered",
         "checker": _s1_lp_followup_answered, "weight": 2.0},
        {"id": "S2_tool_state_written",
         "checker": _s1_tool_state_written, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S3_artifacts_exist",
         "checker": _s2_artifacts_exist, "weight": 1.0},
        {"id": "S3_block_peer_extracted",
         "checker": _s2_block_peer_extracted, "weight": 1.5},
        {"id": "S3_peer_framing_preserved",
         "checker": _s2_peer_framing_preserved, "weight": 2.0},
        {"id": "S3_tool_state_written",
         "checker": _s2_tool_state_written, "weight": 1.0},
    ],
    "final": [
        {"id": "R1_methodology_not_hidden",
         "checker": _r_methodology_not_hidden, "weight": 2.0},
        {"id": "R2_volume_and_margin_not_collapsed",
         "checker": _r_volume_and_margin_not_collapsed, "weight": 2.0},
    ],
}
