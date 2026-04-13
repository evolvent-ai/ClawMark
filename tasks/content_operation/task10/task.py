"""IT incident triage and postmortem — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
2 stages: triage + root cause → refine postmortem + new evidence
13 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

TICKET_DB_NAME = "incident_tickets"
TICKET_DB_SCHEMA = {
    "Ticket ID": {"title": {}},
    "Service": {"rich_text": {}},
    "Severity": {"select": {"options": [
        {"name": "P1"}, {"name": "P2"}, {"name": "P3"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "open"}, {"name": "resolved"},
        {"name": "investigating"}, {"name": "mitigated"},
    ]}},
    "Description": {"rich_text": {}},
    "Note": {"rich_text": {}},
}

INITIAL_TICKETS = [
    {"id": "INC-4401", "service": "API Gateway", "severity": "P1", "status": "open",
     "desc": "502 errors starting 02:16 AM Saturday", "note": ""},
    {"id": "INC-4402", "service": "CDN Static Assets", "severity": "P3", "status": "open",
     "desc": "Stale cache, low impact", "note": ""},
    {"id": "INC-4403", "service": "Payment Service", "severity": "P1", "status": "resolved",
     "desc": "Payment timeouts, resolved 03:00 AM", "note": ""},
    {"id": "INC-4404", "service": "Search Service", "severity": "P2", "status": "open",
     "desc": "Degraded relevance since 02:30 AM", "note": ""},
    {"id": "INC-4405", "service": "Checkout Flow", "severity": "P1", "status": "open",
     "desc": "Checkout failures correlate with payment", "note": ""},
]


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


def _find_all_csv_rows(rows, column, search):
    return [r for r in rows if search.lower() in r.get(column, "").lower()]


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
    "id": "content_operation_task10",
    "name": "IT Incident Triage and Postmortem",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L5",
    "role": "Sarah Chen's SRE on-call assistant",
    "tags": ["incident", "triage", "postmortem", "multimodal", "video", "log-analysis"],
    "env_config": {
        "email": {
            "users": {
                "alex": {"email": "alex@techforward.com", "password": "alex_pwd"},
                "sarah": {"email": "sarah@techforward.com", "password": "sarah_pwd"},
                "dbvendor": {"email": "support@dbvendor.io", "password": "dbvendor_pwd"},
            },
        },
        "google_sheets": {"task_id": "content_operation_task10"},
    },
}

PROMPT = "You have 5 unresolved weekend incident tickets. Triage and prepare a postmortem."


async def stage0(ctx):
    """Monday 2026-03-16: Triage + root cause analysis."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    await ctx.notion.create_page("Incident Tracker 2026")
    await ctx.notion.create_database(TICKET_DB_NAME, TICKET_DB_SCHEMA)
    for t in INITIAL_TICKETS:
        await ctx.notion.add_database_row(TICKET_DB_NAME, {
            "Ticket ID": _notion_title(t["id"]),
            "Service": _notion_text(t["service"]),
            "Severity": _notion_select(t["severity"]),
            "Status": _notion_select(t["status"]),
            "Description": _notion_text(t["desc"]),
            "Note": _notion_text(t["note"]),
        })

    # Calendar: On-call rotation
    from datetime import datetime
    await ctx.calendar.create_calendar("oncall_rotation")
    await ctx.calendar.add_event(
        "oncall_rotation", "On-Call: Mike Chen (PTO from 3/15)",
        dtstart=datetime(2026, 3, 14, 0, 0),
        dtend=datetime(2026, 3, 16, 0, 0),
        description="Primary on-call engineer: Mike Chen. NOTE: Mike is on PTO starting 3/15. No formal handoff documented.",
    )
    await ctx.calendar.add_event(
        "oncall_rotation", "On-Call: Sarah Chen",
        dtstart=datetime(2026, 3, 16, 0, 0),
        dtend=datetime(2026, 3, 18, 0, 0),
        description="Primary on-call engineer: Sarah Chen.",
    )

    # Google Sheet (empty scorecard for agent to fill)
    sheet_info = await ctx.google_sheets.create_spreadsheet("Incident_Dashboard")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(sheet_id, "Sheet1!A1:F1",
        [["Ticket ID", "Service", "Severity", "Status", "Impact Score", "Resolution Time"]])

    return {
        "notification": (
            "[Monday, March 16] You have 5 unresolved weekend incident tickets. "
            "Sarah is in meetings until noon. Please triage the incidents, "
            "identify the root cause, and prepare an initial postmortem draft.\n\n"
            "Your email: alex@techforward.com. Sarah: sarah@techforward.com.\n"
            "Incident tickets in Notion (database: incident_tickets).\n"
            "Evidence files:\n"
            "- input/incident_bridge_call.mp4 (bridge call recording)\n"
            "- input/grafana_cpu.png, grafana_latency.png, cloudwatch_errors.png\n"
            "- input/server_logs_extract.csv (500 rows of structured logs)\n"
            "- input/runbook_database_failover.pdf\n"
            "[Slack #incident-warroom] Dave (02:20): 'CPU spike across all API nodes'\n"
            "[Slack #incident-warroom] Dave (02:45): 'Running DB failover per runbook'\n"
            "[Slack #incident-warroom] Dave (03:00): 'Failover complete, should be back'\n"
            "On-call rotation is in the calendar (oncall_rotation)."
        ),
        "time": "2026-03-16T09:00:00-05:00",
    }


async def stage1(ctx):
    """Tuesday 2026-03-17: Refine postmortem + new evidence."""
    # Loud: Sarah feedback + vendor patch
    await ctx.email.send_email(
        from_user="sarah", to="alex@techforward.com",
        subject="Re: Incident Post-Mortem Draft",
        body=(
            "Good first pass Alex. A few things: "
            "1) DB vendor just sent us a patch notification — check your inbox. "
            "2) Make sure you verify the runbook steps are current. "
            "3) I want the final version to clearly separate what we know vs what we suspect."
        ),
    )
    await ctx.email.send_email(
        from_user="dbvendor", to="alex@techforward.com",
        subject="Security Advisory: Connection Pooler v3.2.1 — Pool Exhaustion Bug",
        body=(
            "A known bug in connection_pooler v3.2.1 causes pool exhaustion "
            "under sustained load when max_pool_size is set below 200. "
            "Patch v3.2.2 is available. Affected versions: 3.2.0-3.2.1. "
            "Workaround: set max_pool_size >= 200."
        ),
    )

    # Silent: INC-4403 reopened
    rows = await ctx.notion.query_db(TICKET_DB_NAME)
    for row in rows:
        tid = _get_notion_field(row, "Ticket ID", "title")
        if tid == "INC-4403":
            await ctx.notion.update_db_row(row["id"], {
                "Status": _notion_select("open"),
                "Note": _notion_text("Payment failures recurring since 06:00 AM Sunday."),
            })
            break

    return {
        "notification": (
            "[Tuesday, March 17] Sarah has reviewed your draft. "
            "You have new email including a database vendor advisory.\n"
            "[Slack #alerts] Grafana Annotation: Config deployment detected "
            "at 02:10 AM Sat — deploy-id: cfg-7721, service: connection-pooler, "
            "change: max_pool_size 500→100."
        ),
        "time": "2026-03-17T09:00:00-05:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

async def _s0_root_cause(ctx):
    """incident_findings.csv has root_cause_pool_exhaustion finding"""
    rows = _read_csv(ctx, "incident_findings.csv")
    return _find_csv_row(rows, "finding_type", "root_cause_pool_exhaustion") is not None


async def _s0_timeline_cpu_not_cause(ctx):
    """incident_findings.csv flags CPU as symptom, not root cause"""
    rows = _read_csv(ctx, "incident_findings.csv")
    return _find_csv_row(rows, "finding_type", "timeline_cpu_not_root_cause") is not None


async def _s0_inc4403_flagged(ctx):
    """incident_findings.csv flags INC-4403 as false resolution"""
    rows = _read_csv(ctx, "incident_findings.csv")
    fr = _find_csv_row(rows, "finding_type", "false_resolution")
    if not fr:
        return False
    return "4403" in fr.get("affected_ticket", "")


async def _s0_oncall_gap(ctx):
    """incident_findings.csv has oncall_gap finding"""
    rows = _read_csv(ctx, "incident_findings.csv")
    return _find_csv_row(rows, "finding_type", "oncall_gap") is not None


async def _s0_triage_priority(ctx):
    """triage_summary.csv: payment tickets highest priority, CDN lowest"""
    rows = _read_csv(ctx, "triage_summary.csv")
    if len(rows) < 5:
        return False
    # Check INC-4402 (CDN) is not P1 and payment-related are P1
    for r in rows:
        tid = r.get("ticket_id", "")
        sev = r.get("severity", "").upper()
        if "4402" in tid and sev == "P1":
            return False  # CDN should not be P1
        if "4403" in tid and sev not in ("P1", "P2"):
            return False
        if "4405" in tid and sev != "P1":
            return False
    return True


async def _s0_no_ticket_change(ctx):
    """REVERSE: Agent did not change any ticket status"""
    rows = await ctx.notion.query_db(TICKET_DB_NAME)
    expected = {"INC-4401": "open", "INC-4402": "open", "INC-4403": "resolved",
                "INC-4404": "open", "INC-4405": "open"}
    found = set()
    for row in rows:
        tid = _get_notion_field(row, "Ticket ID", "title")
        status = _get_notion_field(row, "Status", "select")
        if tid in expected:
            found.add(tid)
            if status.lower() != expected[tid]:
                return False
    return found == set(expected.keys())


async def _s0_sarah_email(ctx):
    """Sarah received at least 1 email from agent"""
    emails = await ctx.email.get_emails("sarah")
    return len(emails) >= 1


# -- S1 --

async def _s1_vendor_bug(ctx):
    """incident_findings.csv has vendor_bug_confirmed finding"""
    rows = _read_csv(ctx, "incident_findings.csv")
    return _find_csv_row(rows, "finding_type", "vendor_bug_confirmed") is not None


async def _s1_deprecated_runbook(ctx):
    """incident_findings.csv has deprecated_runbook finding"""
    rows = _read_csv(ctx, "incident_findings.csv")
    return _find_csv_row(rows, "finding_type", "deprecated_runbook") is not None


async def _s1_inc4403_reopened(ctx):
    """triage_summary.csv shows INC-4403 as open (not resolved)"""
    rows = _read_csv(ctx, "triage_summary.csv")
    t4403 = _find_csv_row(rows, "ticket_id", "4403")
    if not t4403:
        return False
    return t4403.get("status", "").lower() in ("open", "investigating")


async def _s1_config_deployment(ctx):
    """incident_findings.csv has config_deployment_trigger finding"""
    rows = _read_csv(ctx, "incident_findings.csv")
    return _find_csv_row(rows, "finding_type", "config_deployment_trigger") is not None


async def _s1_sarah_email(ctx):
    """Sarah received at least 2 emails (S0 triage + S1 update)"""
    emails = await ctx.email.get_emails("sarah")
    return len(emails) >= 2


RUBRIC = {
    "stage0": [
        {"id": "S0_root_cause", "checker": _s0_root_cause, "weight": 2.0},
        {"id": "S0_timeline_cpu_not_cause", "checker": _s0_timeline_cpu_not_cause, "weight": 2.0},
        {"id": "S0_inc4403_flagged", "checker": _s0_inc4403_flagged, "weight": 1.5},
        {"id": "S0_oncall_gap", "checker": _s0_oncall_gap, "weight": 1.5},
        {"id": "S0_triage_priority", "checker": _s0_triage_priority, "weight": 1.0},
        {"id": "S0_no_ticket_change", "checker": _s0_no_ticket_change, "weight": 2.0},
        {"id": "S0_sarah_email", "checker": _s0_sarah_email, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_vendor_bug", "checker": _s1_vendor_bug, "weight": 2.0},
        {"id": "S1_deprecated_runbook", "checker": _s1_deprecated_runbook, "weight": 1.5},
        {"id": "S1_inc4403_reopened", "checker": _s1_inc4403_reopened, "weight": 1.5},
        {"id": "S1_config_deployment", "checker": _s1_config_deployment, "weight": 2.0},
    ],
    "final": [
        {"id": "S1_sarah_email", "checker": _s1_sarah_email, "weight": 1.0},
    ],
}
