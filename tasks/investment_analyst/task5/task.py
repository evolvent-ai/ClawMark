"""Squarespace Q1 2024 + Permira — revenue / KPI scope separation, guide bridge, silent IC question.

Environments: filesystem, email, notion, google_sheets
3 stages: initial deal read -> guide bridge + silent IC question -> overnight peer framing
18 core checkers (0 keyword-search)
"""
import csv
import re
from io import StringIO

# -- Constants -----------------------------------------------------------------

DEAL_NOTE_DB = "SQSP_deal_note"
IC_QUESTIONS_DB = "IC_questions"

DEAL_NOTE_DB_SCHEMA = {
    "company": {"title": {}},
    "q1_revenue": {"rich_text": {}},
    "q1_ufcf": {"rich_text": {}},
    "metric_scope_note": {"rich_text": {}},
    "deal_terms": {"rich_text": {}},
    "guide_change_view": {"rich_text": {}},
    "ic_followup_answer": {"rich_text": {}},
    "peer_frame": {"rich_text": {}},
    "last_updated_stage": {"rich_text": {}},
}

IC_QUESTIONS_DB_SCHEMA = {
    "question_id": {"title": {}},
    "topic": {"rich_text": {}},
    "question": {"rich_text": {}},
    "status": {"select": {"options": [
        {"name": "open"}, {"name": "answered"},
    ]}},
}

# Google Sheets seed data
DEAL_BENCHMARK_HEADER = [
    "company", "metric", "period", "low", "high", "unit", "source",
]
DEAL_BENCHMARK_ROWS = [
    ["Squarespace", "Q1 revenue guide", "Q1 2024", "274", "277", "MUSD",
     "Q4 2023 results"],
    ["Squarespace", "Q1 UFCF guide", "Q1 2024", "83", "86", "MUSD",
     "Q4 2023 results"],
    ["Squarespace", "FY24 revenue guide", "FY 2024", "1170", "1190", "MUSD",
     "Q4 2023 results"],
    ["Squarespace", "FY24 Google Domains contribution", "FY 2024", "85", "88",
     "MUSD", "Q4 2023 results"],
    ["Squarespace", "FY24 UFCF guide", "FY 2024", "290", "310", "MUSD",
     "Q4 2023 results"],
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

    Handles: '281.1M', '1.19B', '$281.1 million', '89.3', '~6.9B', etc.
    Returns value in millions for consistency (SQSP figures are M-scale).
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    s = re.sub(r'[~$,]', '', s)
    s = s.replace('billion', 'b').replace('million', 'm')
    s = s.replace('bn', 'b').replace('mn', 'm')

    multiplier = 1.0
    if s.endswith('b'):
        multiplier = 1000.0
        s = s[:-1]
    elif s.endswith('m'):
        multiplier = 1.0
        s = s[:-1]
    elif s.endswith('k'):
        multiplier = 0.001
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
    "id": "investment_analyst_task5",
    "name": "Squarespace Q1 2024 + Permira -- Revenue / KPI Scope Separation & Peer Monitor",
    "category": "investment_analyst",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Associate on tech buyout team supporting David Ren",
    "tags": [
        "finance", "earnings", "metric-scope", "multimodal",
        "silent-event", "peer-framing", "image", "html", "take-private",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@research.fund",
                    "password": "assistant_pwd",
                },
                "david_ren": {
                    "email": "david.ren@research.fund",
                    "password": "david_ren_pwd",
                },
                "sqsp_ir": {
                    "email": "sqsp-ir@research.fund",
                    "password": "sqsp_ir_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "investment_analyst_task5",
        },
    },
}

PROMPT = "Check your email and workspace for new deal materials to process."


# -- Stage Functions -----------------------------------------------------------

async def stage0(ctx):
    """Stage 1 -- Initial Deal Read: Tuesday May 14, 2024."""
    # 1. Upload assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + deal note database (single-row)
    await ctx.notion.create_page("Squarespace Coverage 2024-Q1")
    await ctx.notion.create_database(DEAL_NOTE_DB, DEAL_NOTE_DB_SCHEMA)
    await ctx.notion.add_database_row(DEAL_NOTE_DB, {
        "company": _notion_title("Squarespace"),
        "q1_revenue": _notion_text(""),
        "q1_ufcf": _notion_text(""),
        "metric_scope_note": _notion_text(""),
        "deal_terms": _notion_text(""),
        "guide_change_view": _notion_text(""),
        "ic_followup_answer": _notion_text(""),
        "peer_frame": _notion_text(""),
        "last_updated_stage": _notion_text(""),
    })

    # 3. Create IC_questions database (empty -- will be seeded in stage1)
    await ctx.notion.create_database(IC_QUESTIONS_DB, IC_QUESTIONS_DB_SCHEMA)

    # 4. Create Google Sheets
    # DealBenchmark
    db = await ctx.google_sheets.create_spreadsheet("DealBenchmark")
    await ctx.google_sheets.update_values(
        db["sheet_id"], "Sheet1!A1:G6",
        [DEAL_BENCHMARK_HEADER] + DEAL_BENCHMARK_ROWS,
    )
    # peer_monitor (header only)
    pm = await ctx.google_sheets.create_spreadsheet("peer_monitor")
    await ctx.google_sheets.update_values(
        pm["sheet_id"], "Sheet1!A1:G1",
        [PEER_MONITOR_HEADER],
    )
    # sqsp_stage_log (header only)
    sl = await ctx.google_sheets.create_spreadsheet("sqsp_stage_log")
    await ctx.google_sheets.update_values(
        sl["sheet_id"], "Sheet1!A1:G1",
        [STAGE_LOG_HEADER],
    )

    # 5. Seed email -- IR materials notification
    await ctx.email.send_email(
        from_user="sqsp_ir",
        to="assistant@research.fund",
        subject="Squarespace Q1 2024 Results & Transaction Materials",
        body=(
            "Attached please find Q1 2024 results and transaction materials "
            "for Squarespace:\n\n"
            "- Q1 2024 results (sqsp_q1_2024_results.html)\n"
            "- Q4 2023 results (sqsp_q4_2023_results.html)\n"
            "- Permira transaction announcement (sqsp_permira_transaction.html)\n"
            "- 2023 10-K excerpt (sqsp_2023_10k.html)\n"
            "- Q1 metric scope crop (sqsp_q1_metric_scope_crop.png)\n\n"
            "Materials are in /workspace/input/."
        ),
    )

    # 6. Notification -- includes Feishu message
    return {
        "notification": (
            "[Tuesday, May 14, 2024 08:30] You have a new email and a new "
            "Feishu message.\n\n"
            "Your email: assistant@research.fund. "
            "David Ren: david.ren@research.fund.\n"
            "Squarespace deal note: Notion database 'SQSP_deal_note'. "
            "IC questions: Notion database 'IC_questions'.\n"
            "DealBenchmark, peer_monitor, sqsp_stage_log: Google Sheets.\n"
            "All input materials in /workspace/input/.\n\n"
            "[Feishu] David Ren: "
            "\"Need a first IC read. "
            "Keep revenue, bookings, ARRR, and cash flow separate. "
            "Do not over-read subscription KPIs if the scope is narrower "
            "than the full business.\""
        ),
        "time": "2024-05-14T08:30:00+08:00",
    }


async def stage1(ctx):
    """Stage 2 -- Guide Bridge + Silent IC Question: Wednesday May 15, 2024."""
    # 1. Silent: Add IC question to Notion (agent must discover)
    await ctx.notion.add_database_row(IC_QUESTIONS_DB, {
        "question_id": _notion_title("IC-SQSP-001"),
        "topic": _notion_text("acquisition-assisted growth / KPI scope"),
        "question": _notion_text(
            "Reported revenue growth is 19% y/y, but Google Domains contributed "
            "an estimated $85M-$88M to FY24. Unique subscriptions and ARPUS "
            "explicitly exclude Acquired Domain Assets. Does the team view "
            "the reported growth as acquisition-assisted, and should unique "
            "subscriptions / ARPUS be treated as whole-company proof points? "
            "Please provide a view before the IC call."
        ),
        "status": _notion_select("open"),
    })

    # 2. Loud: David Ren sends follow-up email
    await ctx.email.send_email(
        from_user="david_ren",
        to="assistant@research.fund",
        subject="SQSP follow-up -- guide bridge and revenue quality",
        body=(
            "Two things:\n\n"
            "1. Compare the new FY24 guide versus the prior FY24 guide -- "
            "what moved on revenue and UFCF?\n"
            "2. Give me one clean sentence on revenue quality versus "
            "metric scope.\n\n"
            "Send me the follow-up note when ready."
        ),
    )

    # 3. Notification -- only mentions the loud email
    return {
        "notification": "[Wednesday, May 15, 2024 09:00] You have a new email.",
        "time": "2024-05-15T09:00:00+08:00",
    }


async def stage2(ctx):
    """Stage 3 -- Overnight Peer Framing: Monday May 20, 2024."""
    # 1. Silent: Update peer_monitor with Wix Q1 2024 data
    pm_id = await ctx.google_sheets.get_spreadsheet_id("peer_monitor")
    if pm_id:
        await ctx.google_sheets.append_rows(
            pm_id, "Sheet1!A:G",
            [["Wix", "Q1 2024 bookings", "Q1 2024",
              "457.3", "MUSD", "Wix Q1 2024 results", "2024-05-15"],
             ["Wix", "Q1 2024 revenue", "Q1 2024",
              "419.8", "MUSD", "Wix Q1 2024 results", "2024-05-15"],
             ["Wix", "Q1 2024 FCF margin", "Q1 2024",
              "26", "PCT", "Wix Q1 2024 results", "2024-05-15"],
             ["Wix", "FY24 FCF margin outlook", "FY 2024",
              "~26", "PCT", "Wix Q1 2024 results", "2024-05-15"]],
        )

    # 2. Loud: Overnight news email with image reference
    await ctx.email.send_email(
        from_user="sqsp_ir",
        to="assistant@research.fund",
        subject="Overnight peer news -- Wix Q1 2024 update",
        body=(
            "Overnight update: Wix released Q1 2024 results. "
            "See the screenshot at "
            "/workspace/input/sqsp_stage3_peer_website_builder_news.png "
            "for coverage.\n\n"
            "The full Wix results are also available at "
            "/workspace/input/wix_q1_2024_results.html.\n\n"
            "Please frame the peer read-through for Squarespace."
        ),
    )

    # 3. Notification -- mentions email but NOT the silent sheet update
    return {
        "notification": (
            "[Monday, May 20, 2024 07:30] You have a new email with a "
            "new overnight peer screenshot attached."
        ),
        "time": "2024-05-20T07:30:00+08:00",
    }


# -- Checker Functions ---------------------------------------------------------

# -- S1 (Initial Deal Read) -- checked after stage0 --


async def _s0_artifacts_exist(ctx):
    """facts.csv exists with >=5 rows AND stage1_brief.md has >=30 words."""
    rows = _read_csv(ctx, "facts.csv")
    if len(rows) < 5:
        return False
    return _md_has_content(ctx, "stage1_brief.md", min_words=30)


async def _s0_metric_bases_preserved(ctx):
    """facts.csv has separate rows for revenue, bookings, ARRR, ARPUS, adj EBITDA, UFCF."""
    rows = _read_csv(ctx, "facts.csv")
    required_metrics = {
        "revenue": False,
        "bookings": False,
        "ufcf": False,
    }
    optional_metrics = {
        "arrr": False,
        "arpus": False,
        "ebitda": False,
    }
    for r in rows:
        metric = (r.get("metric") or "").lower()
        for key in required_metrics:
            if key in metric:
                required_metrics[key] = True
        for key in optional_metrics:
            if key in metric:
                optional_metrics[key] = True
        # Handle alternate names
        if "free cash flow" in metric or "free-cash-flow" in metric:
            required_metrics["ufcf"] = True
        if "subscription" in metric and "unique" in metric:
            optional_metrics["arrr"] = False  # don't double-count
        if "annual run" in metric:
            optional_metrics["arrr"] = True

    # All required must be found
    if not all(required_metrics.values()):
        return False
    # At least 2 of 3 optional must be found
    optional_found = sum(1 for v in optional_metrics.values() if v)
    return optional_found >= 2


async def _s0_q1_vs_prior_guide_direction(ctx):
    """Q1 revenue (~281M) above prior Q1 guide (274-277M) and UFCF (~89M) above prior Q1 guide (83-86M)."""
    rows = _read_csv(ctx, "facts.csv")
    found_rev_above = False
    found_ufcf_above = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        direction = (r.get("direction") or "").lower()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        val = _parse_financial_number((r.get("value") or ""))
        combined = f"{metric} {note} {basis}"

        # Check for revenue beat
        if "revenue" in metric:
            if direction in ("above", "positive", "beat"):
                found_rev_above = True
            if any(kw in note for kw in ("above", "beat", "exceed")):
                found_rev_above = True
            if val is not None and _values_close(val, 281.1, rel_tol=0.05):
                # If the value is close to actual and there is guide context
                if any(kw in combined for kw in ("guide", "vs", "comparison")):
                    found_rev_above = True

        # Check for UFCF beat
        if "ufcf" in metric or "free cash flow" in metric or "fcf" in metric:
            if direction in ("above", "positive", "beat"):
                found_ufcf_above = True
            if any(kw in note for kw in ("above", "beat", "exceed")):
                found_ufcf_above = True
            if val is not None and _values_close(val, 89.3, rel_tol=0.05):
                if any(kw in combined for kw in ("guide", "vs", "comparison")):
                    found_ufcf_above = True

    return found_rev_above and found_ufcf_above


async def _s0_metric_scope_note_captured(ctx):
    """Acquired Domain Assets scope exclusion recorded in facts.csv or Notion."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        combined = f"{metric} {note} {basis}"
        if ("acquired domain" in combined or "domain asset" in combined
                or ("scope" in combined and ("exclud" in combined or "caveat" in combined
                    or "subscript" in combined))):
            return True
        if ("arpus" in combined or "unique subscription" in combined):
            if ("exclud" in combined or "not include" in combined
                    or "not account" in combined or "scope" in combined
                    or "caveat" in combined):
                return True
    # Check Notion
    notion_rows = await ctx.notion.query_db(DEAL_NOTE_DB)
    for r in notion_rows:
        msn = _get_notion_field(r, "metric_scope_note").lower()
        if ("acquired domain" in msn or "domain asset" in msn
                or ("scope" in msn and "exclud" in msn)):
            return True
    return False


async def _s0_deal_terms_logged(ctx):
    """$44/share, ~6.9B EV, and premium facts are captured in facts.csv or Notion."""
    rows = _read_csv(ctx, "facts.csv")
    found_price = False
    found_ev = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        value = (r.get("value") or "").strip()
        note = (r.get("note") or "").lower()
        combined = f"{metric} {value} {note}"
        # $44/share
        if "44" in value and ("share" in combined or "price" in combined
                              or "offer" in combined or "deal" in combined):
            found_price = True
        # ~6.9B EV
        val = _parse_financial_number(value)
        if val is not None:
            if _values_close(val, 6900.0, rel_tol=0.08):
                found_ev = True
            if _values_close(val, 6.9, rel_tol=0.08):
                # Might be in billions directly
                found_ev = True

    # Check Notion deal_terms field as fallback
    if not (found_price and found_ev):
        notion_rows = await ctx.notion.query_db(DEAL_NOTE_DB)
        for r in notion_rows:
            dt = _get_notion_field(r, "deal_terms").lower()
            if "44" in dt and ("share" in dt or "price" in dt):
                found_price = True
            if "6.9" in dt or "6900" in dt:
                found_ev = True

    return found_price and found_ev


async def _s0_tool_state_written(ctx):
    """Notion deal note updated, sqsp_stage_log has rows, David Ren received email."""
    # 1. Notion deal note has at least 1 non-empty field
    notion_rows = await ctx.notion.query_db(DEAL_NOTE_DB)
    if not notion_rows:
        return False
    row = notion_rows[0]
    has_data = False
    for field in ("q1_revenue", "q1_ufcf", "deal_terms", "metric_scope_note"):
        val = _get_notion_field(row, field)
        if val and len(val.strip()) > 0:
            has_data = True
            break
    if not has_data:
        return False

    # 2. Stage log has at least 1 data row
    sl_id = await ctx.google_sheets.get_spreadsheet_id("sqsp_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G20")
    if not vals or len(vals) <= 1:  # only header
        return False

    # 3. David Ren received at least 1 email (Feishu substitute)
    emails = await ctx.email.get_emails("david_ren")
    return len(emails) >= 1


# -- S2 (Guide Bridge + Silent IC Question) -- checked after stage1 --


async def _s1_artifacts_exist(ctx):
    """stage2_followup.md exists with >=20 words."""
    return _md_has_content(ctx, "stage2_followup.md", min_words=20)


async def _s1_prior_vs_current_guide_bridge(ctx):
    """facts.csv captures prior and current FY24 guide comparison (revenue and/or UFCF)."""
    rows = _read_csv(ctx, "facts.csv")
    found_guide_comparison = False
    for r in rows:
        basis = (r.get("basis") or "").lower()
        note = (r.get("note") or "").lower()
        metric = (r.get("metric") or "").lower()
        combined = f"{basis} {note} {metric}"
        # Look for guide comparison references
        if any(kw in combined for kw in
               ("prior", "previous", "comparison", "change", "vs", "bridge",
                "q4", "4q23")):
            if any(kw in combined for kw in
                   ("guide", "guidance", "outlook", "fy24", "fy 2024")):
                val = _parse_financial_number((r.get("value") or ""))
                if val is not None or (r.get("value") or "").strip():
                    found_guide_comparison = True
                    break
    return found_guide_comparison


async def _s1_quality_sentence_captured(ctx):
    """stage2_followup.md addresses revenue quality or metric scope in at least one sentence."""
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if (("quality" in text or "scope" in text or "organic" in text
                 or "acquired domain" in text or "google domains" in text)
                    and ("revenue" in text or "growth" in text or "kpi" in text
                         or "metric" in text)):
                return True
    return False


async def _s1_ic_followup_answered(ctx):
    """If IC question was planted, acquisition / KPI-scope concern is answered in Notion or outputs."""
    # Primary: check Notion deal note ic_followup_answer field
    notion_rows = await ctx.notion.query_db(DEAL_NOTE_DB)
    if notion_rows:
        val = _get_notion_field(notion_rows[0], "ic_followup_answer")
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
               ("acquired domain", "domain asset", "acquisition-assist",
                "google domains", "ic", "followup", "follow-up")):
            if "silent" in basis or "followup" in basis or "ic" in basis:
                return True
    # Tertiary: check stage2_followup.md for acquisition / scope content
    for path in (ctx.workspace / "stage2_followup.md",
                 ctx.workspace / "outputs" / "stage2_followup.md"):
        if path.exists():
            text = path.read_text(encoding="utf-8-sig").lower()
            if (("google domains" in text or "acquired domain" in text
                 or "acquisition" in text)
                    and ("scope" in text or "exclud" in text
                         or "arpus" in text or "subscription" in text)):
                return True
    return False


async def _s1_tool_state_written(ctx):
    """Notion deal note advanced, stage log has S2 rows, David Ren received >=2 emails."""
    # 1. Notion last_updated_stage is not empty
    notion_rows = await ctx.notion.query_db(DEAL_NOTE_DB)
    if not notion_rows:
        return False
    stage_val = _get_notion_field(notion_rows[0], "last_updated_stage")
    if not stage_val or len(stage_val.strip()) == 0:
        return False

    # 2. Stage log has grown
    sl_id = await ctx.google_sheets.get_spreadsheet_id("sqsp_stage_log")
    if not sl_id:
        return False
    vals = await ctx.google_sheets.read_values(sl_id, "Sheet1!A1:G30")
    if not vals or len(vals) <= 2:  # header + at least 2 data rows
        return False

    # 3. David Ren received >=2 emails (S1 + S2 summaries)
    emails = await ctx.email.get_emails("david_ren")
    return len(emails) >= 2


# -- S3 (Overnight Peer Framing) -- checked after stage2 --


async def _s2_artifacts_exist(ctx):
    """stage3_alert.md exists with >=20 words."""
    return _md_has_content(ctx, "stage3_alert.md", min_words=20)


async def _s2_wix_peer_extracted(ctx):
    """facts.csv stage-3 rows capture Wix Q1 2024 peer facts (bookings/revenue/FCF)."""
    rows = _read_csv(ctx, "facts.csv")
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        source_ref = (r.get("source_ref") or "").lower()
        value = (r.get("value") or "").lower()
        combined = f"{metric} {note} {source_ref} {value}"
        if "wix" in combined:
            # Found a Wix reference -- check it has content
            if (r.get("value") or "").strip():
                return True
    return False


async def _s2_peer_framing_preserved(ctx):
    """Separate judgement fields: sector health + SQSP attractiveness + KPI-scope caveats."""
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
        if any(kw in combined for kw in ("wix", "peer", "sector", "website-builder",
                                          "website builder", "smb")):
            has_peer = True
        if any(kw in combined for kw in ("sqsp", "squarespace", "scope", "caveat",
                                          "acquired domain", "cash conversion")):
            has_own = True
    return has_peer and has_own


async def _s2_tool_state_written(ctx):
    """Notion peer_frame updated, stage log grown, David Ren received >=3 emails."""
    # 1. Notion peer_frame field is non-empty
    notion_rows = await ctx.notion.query_db(DEAL_NOTE_DB)
    if not notion_rows:
        return False
    pf = _get_notion_field(notion_rows[0], "peer_frame")
    if not pf or len(pf.strip()) == 0:
        return False

    # 2. David Ren received >=3 emails (S1 + S2 + S3 summaries)
    emails = await ctx.email.get_emails("david_ren")
    return len(emails) >= 3


# -- Red-Line Checks (final) --


async def _r_metric_scope_not_ignored(ctx):
    """REVERSE: KPIs excluding Acquired Domain Assets are not treated as whole-company metrics."""
    rows = _read_csv(ctx, "facts.csv")
    # Check that scope caveat is present somewhere
    has_scope_caveat = False
    for r in rows:
        metric = (r.get("metric") or "").lower()
        note = (r.get("note") or "").lower()
        basis = (r.get("basis") or "").lower()
        combined = f"{metric} {note} {basis}"
        if ("acquired domain" in combined or "domain asset" in combined
                or "scope" in combined or "metric_scope" in combined):
            has_scope_caveat = True
            break
    if not has_scope_caveat:
        # Check Notion
        notion_rows = await ctx.notion.query_db(DEAL_NOTE_DB)
        for r in notion_rows:
            msn = _get_notion_field(r, "metric_scope_note").lower()
            if msn and len(msn.strip()) > 5:
                has_scope_caveat = True
                break
    return has_scope_caveat


async def _r_metrics_not_collapsed(ctx):
    """REVERSE: ARRR / ARPUS / bookings / UFCF remain as distinct metrics, not overwritten as revenue."""
    rows = _read_csv(ctx, "facts.csv")
    if not rows:
        return False
    # Collect unique metric names
    metrics = set()
    for r in rows:
        m = (r.get("metric") or "").strip().lower()
        if m:
            metrics.add(m)
    # Must have at least 3 distinct metric families beyond just revenue
    families_found = 0
    family_patterns = [
        ["bookings"],
        ["ufcf", "free cash flow", "unlevered free cash flow", "fcf"],
        ["arrr", "annual run rate", "annual recurring"],
        ["arpus", "average revenue per"],
        ["ebitda"],
    ]
    for patterns in family_patterns:
        for m in metrics:
            if any(p in m for p in patterns):
                families_found += 1
                break
    return families_found >= 3


# -- RUBRIC --------------------------------------------------------------------

RUBRIC = {
    "stage0": [
        {"id": "S1_artifacts_exist",
         "checker": _s0_artifacts_exist, "weight": 1.0},
        {"id": "S1_metric_bases_preserved",
         "checker": _s0_metric_bases_preserved, "weight": 2.0},
        {"id": "S1_q1_vs_prior_guide_direction",
         "checker": _s0_q1_vs_prior_guide_direction, "weight": 2.0},
        {"id": "S1_metric_scope_note_captured",
         "checker": _s0_metric_scope_note_captured, "weight": 1.5},
        {"id": "S1_deal_terms_logged",
         "checker": _s0_deal_terms_logged, "weight": 1.5},
        {"id": "S1_tool_state_written",
         "checker": _s0_tool_state_written, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S2_artifacts_exist",
         "checker": _s1_artifacts_exist, "weight": 1.0},
        {"id": "S2_prior_vs_current_guide_bridge",
         "checker": _s1_prior_vs_current_guide_bridge, "weight": 1.5},
        {"id": "S2_quality_sentence_captured",
         "checker": _s1_quality_sentence_captured, "weight": 1.0},
        {"id": "S2_ic_followup_answered",
         "checker": _s1_ic_followup_answered, "weight": 2.0},
        {"id": "S2_tool_state_written",
         "checker": _s1_tool_state_written, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S3_artifacts_exist",
         "checker": _s2_artifacts_exist, "weight": 1.0},
        {"id": "S3_wix_peer_extracted",
         "checker": _s2_wix_peer_extracted, "weight": 1.5},
        {"id": "S3_peer_framing_preserved",
         "checker": _s2_peer_framing_preserved, "weight": 2.0},
        {"id": "S3_tool_state_written",
         "checker": _s2_tool_state_written, "weight": 1.0},
    ],
    "final": [
        {"id": "R1_metric_scope_not_ignored",
         "checker": _r_metric_scope_not_ignored, "weight": 2.0},
        {"id": "R2_metrics_not_collapsed",
         "checker": _r_metrics_not_collapsed, "weight": 2.0},
    ],
}
