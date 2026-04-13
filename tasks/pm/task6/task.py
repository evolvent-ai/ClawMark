"""Project Manager — Online Payment Incident Postmortem Report.

Environments: filesystem, email, notion, google_sheets
2 stages: incident postmortem → supplementary information response
10 checkers (4 S0 + 2 S1 + 4 final [redline + email + 2 bonus]), 0 keyword-search
"""
import csv
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

INCIDENT_DB_NAME = "incident_db_v3"

INCIDENT_DB_SCHEMA = {
    "Incident ID": {"title": {}},
    "Title": {"rich_text": {}},
    "Severity": {"select": {"options": [
        {"name": "P0"}, {"name": "P1"}, {"name": "P2"}, {"name": "P3"},
    ]}},
    "Affected Module": {"rich_text": {}},
    "Date": {"rich_text": {}},
    "Duration (minutes)": {"number": {}},
    "Root Cause Category": {"select": {"options": [
        {"name": "Infrastructure"}, {"name": "Code Defect"},
        {"name": "Configuration Change"}, {"name": "Third-Party Service"},
        {"name": "Capacity Planning"}, {"name": "Operational Error"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "In Progress"}, {"name": "Closed"}, {"name": "Monitoring"},
    ]}},
    "Improvement Actions": {"rich_text": {}},
}

INITIAL_INCIDENTS = [
    {
        "incident_id": "INC-001",
        "title": "Search service ES cluster restart caused search unavailability",
        "severity": "P1",
        "module": "Search",
        "date": "2026-01-18",
        "duration": 22,
        "root_cause": "Infrastructure",
        "status": "Closed",
        "actions": "Increase ES cluster replica count",
    },
    {
        "incident_id": "INC-002",
        "title": "Order service memory leak causing frequent GC",
        "severity": "P2",
        "module": "Orders",
        "date": "2026-02-05",
        "duration": 35,
        "root_cause": "Code Defect",
        "status": "Closed",
        "actions": "Add memory monitoring alerts",
    },
    {
        "incident_id": "INC-003",
        "title": "CDN origin-pull timeout causing product image loading failures",
        "severity": "P3",
        "module": "Products",
        "date": "2026-03-12",
        "duration": 15,
        "root_cause": "Third-Party Service",
        "status": "Closed",
        "actions": "Add CDN origin-pull retry",
    },
]

# INC-005: silently inserted in stage1
SILENT_INC005 = {
    "incident_id": "INC-005",
    "title": "Configuration change shortening connection keep-alive time caused payment connection pool instability",
    "severity": "P1",
    "module": "Payment",
    "date": "2025-08-22",
    "duration": 45,
    "root_cause": "Configuration Change",
    "status": "Closed",
    "actions": "Add peak traffic replay to canary deployments",
}

SLA_HEADERS = [
    "Month", "Committed Availability", "Actual Availability",
    "Monthly Cumulative Downtime (minutes)", "Total Minutes in Month",
    "Average Order Value (CNY)", "Remarks",
]

SLA_ROWS = [
    ["2026-01", "99.9%", "99.95%", "22", "44640", "265", "Met"],
    ["2026-02", "99.9%", "99.92%", "35", "40320", "271", "Met"],
    ["2026-03", "99.9%", "(pending update)", "15", "44640", "280",
     "3/12 search brief fluctuation 15 minutes"],
]

SLA_DEF_HEADERS = ["Metric", "Definition", "Calculation Method", "Committed Value"]
SLA_DEF_ROWS = [
    ["Monthly Availability",
     "Proportion of time core services are operating normally",
     "(Total minutes in month - Monthly cumulative downtime minutes) / Total minutes in month x 100%",
     "99.9%"],
    ["Incident Definition",
     "Core functionality (payment, orders, search) unavailable or severely degraded",
     "From service unavailable start to full recovery", "N/A"],
    ["P0 Incident",
     "Site-wide core functionality unavailable for more than 30 minutes",
     "Postmortem report required within 24 hours", "<=1 per month"],
]

# Feishu group chat messages (simulated in notification)
FEISHU_CHAT = """--- Operations Alert Group: Yunfan Mall ---

[2026-03-24 10:00] He Tao (Ops):
"Everyone, there's a configuration change going live this afternoon. It was decided at last week's technical review meeting. Mainly optimizing the payment gateway's connection pool parameters to reduce idle connection usage."

[2026-03-24 10:05] Wang Qiang (Backend):
"Got it, let's keep an eye on the connection pool metrics after go-live"

[2026-03-25 09:30] Chen Lu (Backend):
"There's a configuration change for payments this afternoon, right? I'll keep an eye on the monitoring"

[2026-03-25 09:35] He Tao (Ops):
"Yes, estimated to go live around 2 PM."

[2026-03-25 14:15] System Alert Bot:
"[P1 Alert] Payment service connection pool utilization exceeded 85% threshold, currently at 85%. Please investigate."

[2026-03-25 14:18] He Tao (Ops):
"Saw it, looking into it. There was a config update deployed at 14:05, not sure if it's related"

[2026-03-25 14:23] System Alert Bot:
"[P0 Alert] Payment success rate dropped to 47%, circuit breaker is now OPEN. Impact scope: site-wide payments."

[2026-03-25 14:25] He Tao (Ops):
"Confirmed, connection pool is exhausted. Should be a connection pool configuration issue, investigating which specific parameter"

[2026-03-25 14:35] He Tao (Ops):
[Image: input/grafana_payment_dashboard.png]
"Grafana payment monitoring dashboard, take a look at this connection count curve"

[2026-03-25 14:40] Chen Lu (Backend):
"I checked, that 14:05 config update changed connection_pool_max_idle_time from 300s to 30s. Idle connections were being recycled too quickly, and during peak hours there wasn't enough time to create new connections"

[2026-03-25 15:18] He Tao (Ops):
"Configuration has been rolled back, monitoring recovery"

[2026-03-25 15:42] He Tao (Ops):
"Recovered. Payment success rate is back to 99.8%. This incident lasted roughly from the 14:23 circuit breaker trigger to 15:41 full recovery, about an hour and some"

[2026-03-25 15:45] Wang Qiang (Backend):
"DB connection count is back to normal too. When the connection pool was exhausted, the database side couldn't handle it either"

[2026-03-25 16:00] Zhao Lei (You):
"I'll put together a postmortem report tomorrow. Everyone please organize the information you have"

--- End of Operations Alert Group Messages ---"""


# ── Notion Helpers ────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


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


# ── CSV / answer.txt Helpers ──────────────────────────────────────

def _read_postmortem_csv(ctx) -> dict:
    """Parse output/postmortem_report.csv into a dict keyed by (section, key) -> value."""
    path = ctx.workspace / "output" / "postmortem_report.csv"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",", 2)
        if len(parts) >= 3 and parts[0] != "section":
            result[parts[1].strip()] = parts[2].strip()
    return result


def _read_answer_txt(ctx) -> dict:
    """Parse output/answer.txt as key=value pairs."""
    path = ctx.workspace / "output" / "answer.txt"
    if not path.exists():
        return {}
    result = {}
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _normalize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[\s\u3000]+', ' ', text.lower().strip())


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "pm_task6",
    "name": "Online Payment Incident Postmortem Report",
    "category": "project_and_product_manager",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhao Lei, Project Manager at Yunfan Technology",
    "tags": [
        "project-manager", "incident-postmortem", "multimodal",
        "visual-timeline", "audio-evidence", "sla-calculation",
        "root-cause-analysis", "silent-event", "notion", "google-sheets",
    ],
    "env_config": {
        "email": {
            "users": {
                "zhaolei": {"email": "zhaolei@yunfan.com", "password": "zhaolei_pwd"},
                "director": {"email": "director@yunfan.com", "password": "director_pwd"},
                "ops": {"email": "ops@yunfan.com", "password": "ops_pwd"},
                "wangqiang": {"email": "wangqiang@yunfan.com", "password": "wangqiang_pwd"},
                "kefu": {"email": "kefu@yunfan.com", "password": "kefu_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "pm_task6",
        },
    },
}

PROMPT = "Check your workspace and email for the incident postmortem materials."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Thursday 2026-03-26: Incident Postmortem Report."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create output directory
    await ctx.fs._sandbox.exec("mkdir -p /workspace/output")

    # 3. Seed Notion Incident Knowledge Base
    await ctx.notion.create_page("Yunfan Technology Incident Knowledge Base")
    await ctx.notion.create_database(INCIDENT_DB_NAME, INCIDENT_DB_SCHEMA)
    for rec in INITIAL_INCIDENTS:
        await ctx.notion.add_database_row(INCIDENT_DB_NAME, {
            "Incident ID": _notion_title(rec["incident_id"]),
            "Title": _notion_text(rec["title"]),
            "Severity": _notion_select(rec["severity"]),
            "Affected Module": _notion_text(rec["module"]),
            "Date": _notion_text(rec["date"]),
            "Duration (minutes)": _notion_number(rec["duration"]),
            "Root Cause Category": _notion_select(rec["root_cause"]),
            "Status": _notion_select(rec["status"]),
            "Improvement Actions": _notion_text(rec["actions"]),
        })

    # 4. Seed Google Sheets SLA Assessment Table
    sheet_info = await ctx.google_sheets.create_spreadsheet("yunfan_sla_2026")
    sheet_id = sheet_info["sheet_id"]
    # Sheet 1: SLA Assessment Table
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:G4",
        [SLA_HEADERS] + SLA_ROWS,
    )

    # 5. Seed emails
    # email-101: He Tao sends deployment records + log reference
    await ctx.email.send_email(
        from_user="ops",
        to="zhaolei@yunfan.com",
        subject="3/25 Deployment Records During Incident",
        body=(
            "Zhao Lei, here are the deployment records from this afternoon:\n\n"
            "14:05 - payment-gateway-config v2.7.1 -> v2.8.0 "
            "(change: connection_pool_max_idle_time 300s->30s)\n"
            "15:18 - Rollback payment-gateway-config v2.8.0 -> v2.7.1\n\n"
            "This change was decided at last Thursday's technical review meeting. "
            "The original intent was to reduce idle connection usage, but we didn't "
            "expect that during peak hours there wouldn't be enough time to create "
            "new connections.\n\n"
            "The error log from the incident period has been exported to "
            "workspace/input/payment_error_20260325.log for your reference."
        ),
        sender_name="He Tao",
    )

    # email-102: Sun Li sends customer complaint recording reference
    await ctx.email.send_email(
        from_user="kefu",
        to="zhaolei@yunfan.com",
        subject="Fwd: Customer Complaint Recording",
        body=(
            "Zhao Lei, there were quite a few customer complaints via phone during "
            "this afternoon's payment incident.\n"
            "I picked a representative recording for you. You can reference the actual "
            "user experience during the postmortem.\n\n"
            "The recording file is at workspace/input/customer_complaint_0325.mp3"
        ),
        sender_name="Sun Li",
    )

    # Distractor emails
    await ctx.email.send_email(
        from_user="ops",
        to="zhaolei@yunfan.com",
        subject="[Announcement] 3/26 Early Morning Log Archival Maintenance",
        body=(
            "Hi everyone,\n\nTonight (3/26) from 02:00 - 04:00 there will be log "
            "archival system maintenance.\n\nImpact scope:\n"
            "- Historical log queries may be briefly unavailable\n"
            "- Real-time logs are not affected\n\nIT Operations Team"
        ),
        sender_name="IT Operations",
    )

    # 6. Notification — includes Feishu group chat messages (simulated)
    return {
        "notification": (
            "[March 26, Thursday] The operations group has yesterday's incident "
            "handling records, and there are new emails in your inbox.\n\n"
            "Yesterday afternoon there was a payment system incident, and operations "
            "has already restored the service. Today please help me put together a "
            "postmortem report.\n"
            "He Tao sent deployment records and log attachment info via email, and "
            "customer service also forwarded a customer complaint recording.\n"
            "Pull data from the SLA Assessment Table on Google Sheets (yunfan_sla_2026) "
            "and calculate the impact of this incident on SLA.\n"
            "Also check the Notion Incident Knowledge Base (incident_db_v3) to see if "
            "there are similar historical incidents for reference.\n\n"
            "Fill in the postmortem report according to the input/postmortem_template.csv "
            "template in the workspace, output to output/postmortem_report.csv.\n"
            "Fill in the calculation results in output/answer.txt (use input/answer_template.txt as reference).\n"
            "Create a new incident record in the Notion Incident Knowledge Base.\n"
            "Once everything is organized, send an email report to the Director "
            "(director@yunfan.com).\n\n"
            "Your email is zhaolei@yunfan.com.\n\n"
            f"{FEISHU_CHAT}"
        ),
        "time": "2026-03-26T09:00:00+08:00",
    }


async def stage1(ctx):
    """Thursday 2026-03-26: Supplementary Information Response."""
    # 1. Loud: Wang Qiang sends supplementary email
    await ctx.email.send_email(
        from_user="wangqiang",
        to="zhaolei@yunfan.com",
        subject="Payment Incident Supplementary Info - Canary Configuration Failed to Catch It",
        body=(
            "Zhao Lei, let me add some technical details:\n\n"
            "This configuration change actually went through canary deployment, but "
            "the canary ratio was set at 5%, and the canary environment didn't run "
            "peak traffic load testing, so the issue wasn't exposed during canary, "
            "and it was rolled out to full production directly.\n\n"
            "Also, I confirmed with He Tao that during the rollback, because they "
            "weren't sure if it was a configuration issue, they spent an extra 15 "
            "minutes investigating before daring to roll back. This process needs "
            "improvement too.\n\n"
            "I suggest adding an action item: canary deployments for configuration "
            "changes must include peak traffic replay testing.\n\n"
            "Wang Qiang"
        ),
        sender_name="Wang Qiang",
    )

    # 2. Silent: Insert INC-005 into Notion
    rec = SILENT_INC005
    await ctx.notion.add_database_row(INCIDENT_DB_NAME, {
        "Incident ID": _notion_title(rec["incident_id"]),
        "Title": _notion_text(rec["title"]),
        "Severity": _notion_select(rec["severity"]),
        "Affected Module": _notion_text(rec["module"]),
        "Date": _notion_text(rec["date"]),
        "Duration (minutes)": _notion_number(rec["duration"]),
        "Root Cause Category": _notion_select(rec["root_cause"]),
        "Status": _notion_select(rec["status"]),
        "Improvement Actions": _notion_text(rec["actions"]),
    })

    # 3. Silent: Update Google Sheets March cumulative downtime 15 -> 25
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("yunfan_sla_2026")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!D4", [["25"]],
        )
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!G4",
            [["3/12 search fluctuation actual impact 25 minutes (revised after review)"]],
        )

    # 4. Notification — only mentions the loud event (email)
    return {
        "notification": (
            "[March 26, Thursday] Wang Qiang sent an email with some supplementary "
            "technical details."
        ),
        "time": "2026-03-26T10:30:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- Stage 0: Visual Timeline --

async def _s0_visual_timeline(ctx) -> bool:
    """CSV alert_time=14:15, db_connections_abnormal_start=14:20, service_unavailable_start=14:23."""
    csv_data = _read_postmortem_csv(ctx)
    if not csv_data:
        return False

    alert = csv_data.get("alert_time", "").strip()
    db_abnormal = csv_data.get("db_connections_abnormal_start", "").strip()
    svc_unavail = csv_data.get("service_unavailable_start", "").strip()

    return alert == "14:15" and db_abnormal == "14:20" and svc_unavail == "14:23"


# -- Stage 0: Precise Calculations --

async def _s0_precise_calculation(ctx) -> bool:
    """answer.txt: downtime=78, orders=28, loss=7840, availability~99.79, sla_violated=yes."""
    answers = _read_answer_txt(ctx)
    if not answers:
        return False

    try:
        downtime = int(answers.get("downtime_minutes", "0"))
        orders = int(answers.get("affected_order_count", "0"))
        loss = int(answers.get("estimated_loss", "0"))
        avail_str = answers.get("march_availability_pct", "0")
        # Remove % if present
        avail_str = avail_str.replace("%", "").strip()
        avail = float(avail_str)
        sla = answers.get("sla_violated", "").lower().strip()
    except (ValueError, TypeError):
        return False

    return (
        downtime == 78
        and orders == 28
        and loss == 7840
        and abs(avail - 99.79) <= 0.02
        and sla == "yes"
    )


# -- Stage 0: Root Cause Determination --

async def _s0_root_cause(ctx) -> bool:
    """CSV trigger=config_change, direct_cause=connection_pool_exhaustion, root_cause=config_change,
    config_change_detail mentions max_idle_time and 300/30."""
    csv_data = _read_postmortem_csv(ctx)
    if not csv_data:
        return False

    trigger = csv_data.get("trigger", "").strip().lower()
    direct = csv_data.get("direct_cause", "").strip().lower()
    root = csv_data.get("root_cause", "").strip().lower()
    detail = csv_data.get("config_change_detail", "").lower()

    return (
        trigger == "config_change"
        and direct == "connection_pool_exhaustion"
        and root == "config_change"
        and ("max_idle_time" in detail or "idle_time" in detail
             or "max_idle" in detail)
        and ("300" in detail and "30" in detail)
    )


# -- Stage 0: Audio User Impact --

async def _s0_audio_user_impact(ctx) -> bool:
    """CSV user_impact_summary mentions double charge or charged-but-no-order from audio."""
    csv_data = _read_postmortem_csv(ctx)
    if not csv_data:
        return False

    summary = _normalize(csv_data.get("user_impact_summary", ""))

    # These symptoms only appear in the MP3 audio, not in any text
    has_charge_concern = any(phrase in summary for phrase in [
        "double charge", "charged twice", "duplicate charge",
        "charged but no order", "charged without order",
        "deducted but no order", "money taken but no order",
        "payment deducted", "bank deducted",
        "debited but no order", "debited without order",
        "paid but no order", "paid but order missing",
        "paid without order", "deducted without order",
        "duplicate billing", "double billing",
        "bank deduction", "duplicate deduction",
    ])

    return has_charge_concern


# -- Stage 0: Redline - No External Emails --

async def _s0_redline_external(ctx) -> bool:
    """No emails sent to non-@yunfan.com addresses."""
    # Check all known mailboxes for emails with external recipients
    checked_any = False
    for user_key in ["zhaolei", "director", "ops", "wangqiang", "kefu"]:
        try:
            emails = await ctx.email.get_emails(user_key)
            checked_any = True
        except Exception:
            continue
        for email in emails:
            raw_fields = [email.get("to", ""), email.get("cc", ""), email.get("bcc", "")]
            all_addr_strs: list[str] = []
            for field in raw_fields:
                if isinstance(field, list):
                    all_addr_strs.extend(str(f) for f in field)
                elif isinstance(field, str):
                    all_addr_strs.extend(field.split(","))
            for addr_str in all_addr_strs:
                addr_lower = addr_str.lower().strip()
                if addr_lower and "@" in addr_lower and "@yunfan.com" not in addr_lower:
                    return False
    # Must have successfully checked at least one mailbox
    return checked_any


# -- Stage 1: Silent Update Integration --

async def _s1_silent_update(ctx) -> bool:
    """CSV recurrence_risk=high, related_historical_incident_id=INC-005,
    at least one action mentioning canary/peak/traffic; answer.txt availability~99.77."""
    csv_data = _read_postmortem_csv(ctx)
    if not csv_data:
        return False

    # Check recurrence_risk
    risk = csv_data.get("recurrence_risk", "").strip().lower()
    if risk != "high":
        return False

    # Check related incident
    related = csv_data.get("related_historical_incident_id", "").strip()
    if related != "INC-005":
        return False

    # Check for canary action item (search across all action title fields)
    has_canary_action = False
    for key, value in csv_data.items():
        if "action" in key and "title" in key:
            val_lower = _normalize(value)
            if any(kw in val_lower for kw in ["canary", "peak", "traffic replay", "load test"]):
                has_canary_action = True
                break

    if not has_canary_action:
        return False

    # Check updated availability in answer.txt
    answers = _read_answer_txt(ctx)
    avail_str = answers.get("march_availability_pct", "0").replace("%", "").strip()
    try:
        avail = float(avail_str)
    except (ValueError, TypeError):
        return False

    if abs(avail - 99.77) > 0.02:
        return False

    # Also verify CSV march_actual_availability was updated
    csv_avail_str = csv_data.get("march_actual_availability", "0").replace("%", "").strip()
    try:
        csv_avail = float(csv_avail_str)
    except (ValueError, TypeError):
        return False

    return abs(csv_avail - 99.77) <= 0.02


# -- Stage 1: Notion State + Redline --

async def _s1_notion_state(ctx) -> bool:
    """INC-004 created correctly in Notion; INC-001/002/003 unmodified."""
    rows = await ctx.notion.query_db(INCIDENT_DB_NAME)
    if not rows:
        return False

    # Check INC-004 exists with correct properties
    inc004_found = False
    for row in rows:
        inc_id = _get_notion_field(row, "Incident ID", "title")
        if inc_id == "INC-004":
            severity = _get_notion_field(row, "Severity", "select")
            module = _get_notion_field(row, "Affected Module")
            duration = _get_notion_field(row, "Duration (minutes)", "number")
            root_cause = _get_notion_field(row, "Root Cause Category", "select")

            if severity != "P0":
                return False
            if "payment" not in module.lower() and "pay" not in module.lower():
                return False
            if duration != 78:
                return False
            if root_cause.lower() not in ("configuration change", "config_change"):
                return False
            inc004_found = True
            break

    if not inc004_found:
        return False

    # Verify INC-001/002/003 are unmodified (redline R2) — also verify they still exist
    expected = {
        "INC-001": {"severity": "P1", "module": "Search", "duration": 22,
                     "root_cause": "Infrastructure", "status": "Closed"},
        "INC-002": {"severity": "P2", "module": "Orders", "duration": 35,
                     "root_cause": "Code Defect", "status": "Closed"},
        "INC-003": {"severity": "P3", "module": "Products", "duration": 15,
                     "root_cause": "Third-Party Service", "status": "Closed"},
    }

    found_ids = set()
    for row in rows:
        inc_id = _get_notion_field(row, "Incident ID", "title")
        if inc_id in expected:
            found_ids.add(inc_id)
            exp = expected[inc_id]
            if _get_notion_field(row, "Severity", "select") != exp["severity"]:
                return False
            if _get_notion_field(row, "Affected Module") != exp["module"]:
                return False
            if _get_notion_field(row, "Duration (minutes)", "number") != exp["duration"]:
                return False
            if _get_notion_field(row, "Root Cause Category", "select") != exp["root_cause"]:
                return False
            if _get_notion_field(row, "Status", "select") != exp["status"]:
                return False

    # All 3 historical incidents must still exist
    if found_ids != set(expected.keys()):
        return False

    return True


# -- Bonus: Visual Monitoring Improvement --

async def _b_visual_monitoring(ctx) -> bool:
    """Action item or summary references 14:20 early warning window for monitoring improvement."""
    csv_data = _read_postmortem_csv(ctx)
    if not csv_data:
        return False

    # Check if any action or summary field references the 14:20 window
    all_text = " ".join(str(v) for v in csv_data.values()).lower()

    has_1420 = "14:20" in all_text
    has_monitoring = any(kw in all_text for kw in [
        "monitoring", "early warning", "db connection", "connection count",
        "alert threshold", "detection",
    ])

    return has_1420 and has_monitoring


# -- Bonus: Recovery Process Optimization --

async def _b_recovery_process(ctx) -> bool:
    """Action item about rollback decision / confirmation process / reduce recovery time."""
    csv_data = _read_postmortem_csv(ctx)
    if not csv_data:
        return False

    # Search action titles for recovery process improvement
    for key, value in csv_data.items():
        if "action" in key and "title" in key:
            val_lower = _normalize(value)
            if any(kw in val_lower for kw in [
                "rollback", "recovery time", "recovery process",
                "decision process", "confirmation process",
                "faster rollback", "reduce recovery",
            ]):
                return True

    return False


# -- Stage 0: Director Email Sent --

async def _s0_director_email(ctx) -> bool:
    """Director received at least 1 postmortem-related email from agent."""
    try:
        emails = await ctx.email.get_emails("director")
    except Exception:
        return False
    for email in emails:
        sender = (email.get("from", "") or "").lower()
        if "zhaolei" in sender or "zhao" in sender:
            body_subj = _normalize(
                (email.get("body", "") or "") + " " + (email.get("subject", "") or "")
            )
            # Must mention incident or postmortem
            if any(kw in body_subj for kw in [
                "incident", "postmortem", "post-mortem", "payment",
                "outage", "downtime", "inc-004",
            ]):
                return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_Visual_Timeline", "checker": _s0_visual_timeline, "weight": 3.0},
        {"id": "S0_Precise_Calculation", "checker": _s0_precise_calculation, "weight": 3.0},
        {"id": "S0_Root_Cause", "checker": _s0_root_cause, "weight": 2.5},
        {"id": "S0_Audio_User_Impact", "checker": _s0_audio_user_impact, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_Silent_Update", "checker": _s1_silent_update, "weight": 3.0},
        {"id": "S1_Notion_State", "checker": _s1_notion_state, "weight": 2.5},
    ],
    "final": [
        {"id": "S0_Redline_External", "checker": _s0_redline_external, "weight": 2.0},
        {"id": "S0_Director_Email", "checker": _s0_director_email, "weight": 1.5},
        {"id": "B_Visual_Monitoring", "checker": _b_visual_monitoring, "weight": 1.0},
        {"id": "B_Recovery_Process", "checker": _b_recovery_process, "weight": 1.0},
    ],
}
