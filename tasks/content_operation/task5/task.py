"""Multi-channel weekly report generation — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: anomaly detection → weekly report → follow-up corrections
13 core checkers (0 keyword-search, mostly numeric verification)
"""
import csv
from io import StringIO

ANOMALY_DB_NAME = "anomaly_events"
ANOMALY_DB_SCHEMA = {
    "Date": {"title": {}},
    "Platform": {"rich_text": {}},
    "Metric": {"rich_text": {}},
    "Change": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "pending_investigation"}, {"name": "confirmed"},
        {"name": "resolved"},
    ]}},
}

REPORT_DB_NAME = "weekly_reports"
REPORT_DB_SCHEMA = {
    "Report": {"title": {}},
    "Date": {"rich_text": {}},
    "Note": {"rich_text": {}},
}

SHEET_HEADER = ["platform", "metric", "last_week", "this_week", "wow_change", "status"]
SHEET_ROWS = [
    ["Xiaohongshu", "follower_growth", "1230", "", "", ""],
    ["Xiaohongshu", "total_impressions", "45600", "", "", ""],
    ["Xiaohongshu", "total_interactions", "3890", "", "", ""],
    ["Xiaohongshu", "interaction_rate", "8.5%", "", "", ""],
    ["WeChat", "follower_growth", "560", "", "", ""],
    ["WeChat", "total_reads", "23400", "", "", ""],
    ["WeChat", "total_shares", "1120", "", "", ""],
    ["WeChat", "share_rate", "4.8%", "", "", ""],
    ["Douyin", "follower_growth", "2340", "", "", ""],
    ["Douyin", "total_plays", "128000", "", "", ""],
    ["Douyin", "total_likes", "8920", "", "", ""],
    ["Douyin", "completion_rate", "35.2%", "", "", ""],
]

# Ground truth values for verification
GT_WECHAT_SHARE_RATE_V2 = 4.94  # 1155/23400 * 100
GT_DOUYIN_FILTERED_VIEWS = 110000  # sum of 3/16-3/21 rows only
GT_XHS_INTERACTIONS_CORRECTED = 3890


def _notion_title(v): return {"title": [{"text": {"content": v}}]}
def _notion_text(v): return {"rich_text": [{"text": {"content": v}}]}
def _notion_select(v): return {"select": {"name": v}}

def _read_csv(ctx, filename):
    path = ctx.workspace / "outputs" / filename
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
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


METADATA = {
    "id": "content_operation_task5",
    "name": "Multi-Channel Weekly Report Generation",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhou Lin's data assistant",
    "tags": ["report", "data", "anomaly", "multimodal", "numeric",
             "cross-source", "visual-trap", "csv-cleaning"],
    "env_config": {
        "email": {
            "users": {
                "assistant": {"email": "assistant@company.com", "password": "assistant_pwd"},
                "zhoulin": {"email": "zhoulin@company.com", "password": "zhoulin_pwd"},
                "xiaowang": {"email": "xiaowang@company.com", "password": "xiaowang_pwd"},
            },
        },
        "google_sheets": {"task_id": "content_operation_task5"},
    },
}

PROMPT = "A new day has started. Monitor data and check for anomalies."


async def stage0(ctx):
    """Wednesday 2026-03-18: Daily check — discover Douyin anomaly."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # Notion: create data archive page + anomaly DB + report DB
    await ctx.notion.create_page("Data Archive — Week 12")
    await ctx.notion.create_database(ANOMALY_DB_NAME, ANOMALY_DB_SCHEMA)
    await ctx.notion.create_database(REPORT_DB_NAME, REPORT_DB_SCHEMA)

    # Sheet: weekly report template with last_week pre-filled
    sheet_info = await ctx.google_sheets.create_spreadsheet("weekly_report_template")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(sheet_id, "Sheet1!A1:F13",
        [SHEET_HEADER] + SHEET_ROWS)

    # Email: Xiao Wang sends initial WeChat export
    await ctx.email.send_email(
        from_user="xiaowang", to="assistant@company.com",
        subject="WeChat data export (up to Wednesday)",
        body="Attached is this week's WeChat official account data export, up to Wednesday. See input/wechat_export_v1.csv.",
    )

    # Note: douyin_alert.png is already in input/ (part of assets)
    return {
        "notification": (
            "[Wednesday, March 18] A new day has started.\n\n"
            "Your email: assistant@company.com. Zhou Lin: zhoulin@company.com.\n"
            "[Slack #content] Zhou Lin: 'Handle the weekly report automatically "
            "every Friday. Keep doing daily data monitoring. Xiaohongshu data is "
            "on the Notion data archive page. WeChat data was sent by a colleague "
            "via email. I uploaded the Douyin Excel to Slack.'\n"
            "Douyin Excel: input/douyin_report.xlsx.\n"
            "Dashboard screenshot: input/xiaohongshu_dashboard.png.\n"
            "Last week report screenshot: input/last_week_sheet.png."
        ),
        "time": "2026-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """Friday 2026-03-20: Generate weekly report."""
    # Silent: updated WeChat CSV arrives via email
    await ctx.email.send_email(
        from_user="xiaowang", to="assistant@company.com",
        subject="Updated WeChat data (added Thursday and Friday)",
        body="Updated WeChat data with Thursday and Friday added. See input/wechat_export_v2.csv.",
    )

    return {
        "notification": (
            "[Friday, March 20] Zhou Lin reminded you on Slack to produce "
            "the weekly report. Is all the data ready?"
        ),
        "time": "2026-03-20T09:00:00+08:00",
    }


async def stage2(ctx):
    """Saturday 2026-03-21: Multi-channel follow-up."""
    # Silent: corrected XHS screenshot injected into input/
    inject_src = ctx.task_dir / "inject" / "xhs_updated.png"
    if inject_src.exists():
        await ctx.fs.upload_file(inject_src, "/workspace/input/xhs_updated.png")

    return {
        "notification": (
            "[Saturday, March 21] You have new Slack messages and Notion comments.\n\n"
            "[Slack #content] Zhou Lin: 'Help me check which Douyin videos "
            "are dragging down the completion rate.'\n"
            "[Notion] Colleague commented on weekly report: "
            "'The Xiaohongshu interaction numbers don't match what I see.'"
        ),
        "time": "2026-03-21T09:00:00+08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

async def _s0_alert_detected(ctx):
    """Notion Anomaly DB has Douyin completion_rate record"""
    rows = await ctx.notion.query_db(ANOMALY_DB_NAME)
    for r in rows:
        platform = _get_notion_field(r, "Platform", "rich_text").lower()
        metric = _get_notion_field(r, "Metric", "rich_text").lower()
        if "douyin" in platform and "completion" in metric:
            return True
    return False


async def _s1_report_csv_exists(ctx):
    """weekly_report_w12.csv exists with required columns"""
    rows = _read_csv(ctx, "weekly_report_w12.csv")
    if len(rows) < 10:
        return False
    required = {"platform", "metric", "this_week"}
    headers = set(k.lower().strip() for k in rows[0].keys())
    return required.issubset(headers)


async def _s1_xhs_interactions(ctx):
    """Xiaohongshu total_interactions = 4210 or 3890 (both accepted)"""
    rows = _read_csv(ctx, "weekly_report_w12.csv")
    r = _find_csv_row(rows, "metric", "total_interactions")
    if not r or "xiaohongshu" not in r.get("platform", "").lower():
        # Try finding by platform first
        for row in rows:
            if "xiaohongshu" in row.get("platform", "").lower() and \
               "interaction" in row.get("metric", "").lower():
                r = row
                break
    if not r:
        return False
    val = r.get("this_week", "0").replace(",", "")
    try:
        v = float(val)
        return v in (4210, 3890, 4210.0, 3890.0)
    except ValueError:
        return False


async def _s1_wechat_share_rate(ctx):
    """WeChat share_rate ≈ 4.94% (calculated from v2 data)"""
    rows = _read_csv(ctx, "weekly_report_w12.csv")
    for row in rows:
        if "wechat" in row.get("platform", "").lower() and \
           "share" in row.get("metric", "").lower() and "rate" in row.get("metric", "").lower():
            val = row.get("this_week", "0").replace("%", "").replace(",", "")
            try:
                v = float(val)
                return abs(v - GT_WECHAT_SHARE_RATE_V2) < 0.15
            except ValueError:
                return False
    return False


async def _s1_douyin_date_filtered(ctx):
    """Douyin total_plays excludes the 3/14 row (correct = 110000)"""
    rows = _read_csv(ctx, "weekly_report_w12.csv")
    for row in rows:
        if "douyin" in row.get("platform", "").lower() and \
           "play" in row.get("metric", "").lower():
            val = row.get("this_week", "0").replace(",", "")
            try:
                v = float(val)
                # Should be around 110000 (excluding 3/14 row)
                # If 3/14 row included, it would be higher
                return abs(v - GT_DOUYIN_FILTERED_VIEWS) < 5000
            except ValueError:
                return False
    return False


async def _s1_wow_correct(ctx):
    """At least 8/12 wow_change values correctly calculated (tolerance 0.5%)"""
    rows = _read_csv(ctx, "weekly_report_w12.csv")
    if len(rows) < 10:
        return False
    correct = 0
    total = 0
    for r in rows:
        lw = r.get("last_week", "").replace(",", "").replace("%", "")
        tw = r.get("this_week", "").replace(",", "").replace("%", "")
        wow = r.get("wow_change", "").replace(",", "").replace("%", "").replace("+", "")
        try:
            lw_v = float(lw)
            tw_v = float(tw)
            wow_v = float(wow)
            if lw_v > 0:
                expected = (tw_v - lw_v) / lw_v * 100
                total += 1
                if abs(wow_v - expected) < 0.5:
                    correct += 1
        except (ValueError, ZeroDivisionError):
            pass
    return total >= 10 and correct >= total * 0.8


async def _s1_last_week_unchanged(ctx):
    """REVERSE: Sheet last_week column not modified"""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("weekly_report_template")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!C2:C13")
    if not vals:
        return False
    expected = ["1230", "45600", "3890", "8.5%", "560", "23400", "1120", "4.8%",
                "2340", "128000", "8920", "35.2%"]
    for i, row in enumerate(vals):
        if i < len(expected) and row and row[0] != expected[i]:
            return False
    return True


async def _s1_wechat_used_updated(ctx):
    """WeChat data based on 5 days (v2), not 3 days (v1)"""
    rows = _read_csv(ctx, "weekly_report_w12.csv")
    for row in rows:
        if "wechat" in row.get("platform", "").lower() and \
           "total_reads" in row.get("metric", "").lower():
            val = row.get("this_week", "0").replace(",", "")
            try:
                v = float(val)
                # v2 has 5 days: 4500+6200+3800+5100+3800=23400
                # v1 has 3 days: 4500+6200+3800=14500
                return v > 20000  # Must be based on 5-day data
            except ValueError:
                return False
    return False


async def _s2_xhs_updated_checked(ctx):
    """After correction, XHS total_interactions = 3890 (CSV, Notion, or workspace file)"""
    # Check CSV first
    rows = _read_csv(ctx, "weekly_report_w12.csv")
    for row in rows:
        if "xiaohongshu" in row.get("platform", "").lower() and \
           "interaction" in row.get("metric", "").lower():
            val = row.get("this_week", "0").replace(",", "")
            try:
                if float(val) == GT_XHS_INTERACTIONS_CORRECTED:
                    return True
            except ValueError:
                pass
    # Also check Notion report page
    notion_rows = await ctx.notion.query_db(REPORT_DB_NAME)
    for r in notion_rows:
        note = _get_notion_field(r, "Note", "rich_text")
        if "3890" in note or "3,890" in note:
            return True
    # Also check workspace CSV files (not markdown — avoids false positives from discussion)
    if ctx.workspace:
        outputs = ctx.workspace / "outputs"
        if outputs and outputs.exists():
            for f in outputs.iterdir():
                if f.suffix == ".csv":
                    text = f.read_text(encoding="utf-8-sig")
                    if ("3890" in text or "3,890" in text) and \
                       ("xiaohongshu" in text.lower() or "xhs" in text.lower()):
                        return True
    return False


async def _s1_notion_anomaly_relation(ctx):
    """Weekly report page references the Douyin anomaly (via Notion note or workspace file)."""
    # Check if the weekly report page mentions anomaly or Douyin
    rows = await ctx.notion.query_db(REPORT_DB_NAME)
    for r in rows:
        note = _get_notion_field(r, "Note", "rich_text").lower()
        title = _get_notion_field(r, "Report", "title").lower()
        combined = note + " " + title
        # Must mention both Douyin AND anomaly/completion to avoid false positives
        if "douyin" in combined and ("anomaly" in combined or "completion" in combined):
            return True
    # Also check the weekly report CSV (primary deliverable) for anomaly reference
    report = ctx.workspace / "outputs" / "weekly_report_w12.csv"
    if report and report.exists():
        text = report.read_text(encoding="utf-8-sig").lower()
        if "anomaly" in text and "douyin" in text:
            return True
    return False


async def _s2_douyin_lowest_replied(ctx):
    """Agent identified lowest Douyin video (Weekend Vlog / 22.4% completion)."""
    if ctx.workspace:
        outputs = ctx.workspace / "outputs"
        if outputs and outputs.exists():
            for f in outputs.iterdir():
                if f.suffix in (".csv", ".md", ".txt"):
                    text = f.read_text(encoding="utf-8-sig").lower()
                    if "weekend vlog" in text or "22.4" in text or "22.4%" in text:
                        return True
    # Also check emails
    emails = await ctx.email.get_emails("zhoulin")
    for e in emails:
        body = e.get("body", "").lower()
        if "weekend vlog" in body or "22.4" in body:
            return True
    return False


async def _s2_notion_comment_replied(ctx):
    """Agent replied to Notion comment about XHS discrepancy (mentions shares/forwarding)."""
    # Check Notion report page note
    rows = await ctx.notion.query_db(REPORT_DB_NAME)
    for r in rows:
        note = _get_notion_field(r, "Note", "rich_text").lower()
        if ("share" in note or "forwarding" in note) and \
           ("xiaohongshu" in note or "xhs" in note or "interaction" in note):
            return True
    # Check emails to Zhou Lin
    emails = await ctx.email.get_emails("zhoulin")
    for e in emails:
        body = e.get("body", "").lower()
        if ("share" in body or "forwarding" in body) and \
           ("xiaohongshu" in body or "xhs" in body):
            return True
    return False


async def _s1_zhoulin_email(ctx):
    """Zhou Lin received at least 1 email (formal report)"""
    emails = await ctx.email.get_emails("zhoulin")
    return len(emails) >= 1


RUBRIC = {
    "stage0": [
        {"id": "S0_alert_detected", "checker": _s0_alert_detected, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_report_csv_exists", "checker": _s1_report_csv_exists, "weight": 1.0},
        {"id": "S1_xhs_interactions", "checker": _s1_xhs_interactions, "weight": 1.5},
        {"id": "S1_wechat_share_rate", "checker": _s1_wechat_share_rate, "weight": 2.0},
        {"id": "S1_douyin_date_filtered", "checker": _s1_douyin_date_filtered, "weight": 2.0},
        {"id": "S1_wow_correct", "checker": _s1_wow_correct, "weight": 1.5},
        {"id": "S1_last_week_unchanged", "checker": _s1_last_week_unchanged, "weight": 2.0},
        {"id": "S1_wechat_used_updated", "checker": _s1_wechat_used_updated, "weight": 2.0},
        {"id": "S1_notion_anomaly_relation", "checker": _s1_notion_anomaly_relation, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_xhs_updated_checked", "checker": _s2_xhs_updated_checked, "weight": 2.0},
        {"id": "S2_douyin_lowest_replied", "checker": _s2_douyin_lowest_replied, "weight": 1.5},
        {"id": "S2_notion_comment_replied", "checker": _s2_notion_comment_replied, "weight": 1.0},
    ],
    "final": [
        {"id": "S1_zhoulin_email", "checker": _s1_zhoulin_email, "weight": 1.0},
    ],
}
