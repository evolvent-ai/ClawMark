"""Escalated customer complaint handling — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
2 stages: info gathering + initial analysis → updated analysis + solution drafting
12 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

CRM_DB_NAME = "customer_crm"
CRM_DB_SCHEMA = {
    "Customer Name": {"title": {}},
    "Company": {"rich_text": {}},
    "Tier": {"select": {"options": [
        {"name": "platinum"}, {"name": "gold"}, {"name": "silver"},
    ]}},
    "Annual Contract": {"number": {}},
    "NPS": {"rich_text": {}},
    "Channel": {"rich_text": {}},
    "Note": {"rich_text": {}},
}

INITIAL_CRM = {
    "name": "Zhang Ming", "company": "Ruijin Technology",
    "tier": "platinum", "annual_contract": 120000,
    "nps": "3.2 (dropped from 8.5)",
    "channel": "TechZone Plus (recorded at contract signing)",
    "note": "Considering switching vendors. 6 tickets on XR-500.",
}

TICKET_HEADER = ["Ticket ID", "Date", "Issue", "Priority", "Response Time (h)",
                 "Resolution", "Status"]
TICKET_ROWS = [
    ["TK-001", "2026-02-15", "XR-500 reboot", "P2", "18", "remote reset", "closed"],
    ["TK-002", "2026-02-28", "XR-500 reboot", "P2", "22", "firmware rollback", "closed"],
    ["TK-003", "2026-03-05", "XR-500 E-4012 error", "P2", "20", "remote diagnostics", "closed"],
    ["TK-004", "2026-03-08", "XR-500 reboot+E-4012", "P2", "26", "remote repair", "closed"],
    ["TK-005", "2026-03-12", "XR-500 reboot", "P2", "12", "remote repair", "closed"],
    ["TK-006", "2026-03-15", "XR-500 reboot+data loss", "P2", "30", "pending", "open"],
]
# S1: add another customer's similar complaint
S1_NEW_ROW = ["TK-007", "2026-03-24", "XR-500 E-4012 (Ms. Li)", "P2", "", "pending", "open"]

DEFECT_HEADER = ["Product", "Defect Rate", "Industry Average", "Note"]
DEFECT_ROWS = [
    ["XR-500", "8%", "2%", "Significantly above average"],
    ["XR-300", "1.5%", "2%", "Normal"],
    ["XR-700", "2.2%", "2%", "Normal"],
]


def _notion_title(v): return {"title": [{"text": {"content": v}}]}
def _notion_text(v): return {"rich_text": [{"text": {"content": v}}]}
def _notion_select(v): return {"select": {"name": v}}
def _notion_number(v): return {"number": v}

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
    elif field_type == "number":
        return prop.get("number", 0)
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


METADATA = {
    "id": "content_operation_task12",
    "name": "Escalated Customer Complaint Handling",
    "category": "content_ops",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhao Wei's customer service assistant",
    "tags": ["complaint", "sla", "multi-party", "multimodal", "audio",
             "image-trap", "sarcasm", "crisis-management"],
    "env_config": {
        "email": {
            "users": {
                "xiaosu": {"email": "xiaosu@company.com", "password": "xiaosu_pwd"},
                "zhaowei": {"email": "zhaowei@company.com", "password": "zhaowei_pwd"},
            },
        },
        "google_sheets": {"task_id": "content_operation_task12"},
    },
}

PROMPT = "Customer Mr. Zhang submitted an escalated complaint. Check email, Slack, and Telegram."


async def stage0(ctx):
    """Tuesday 2026-03-24: Information gathering + initial analysis."""
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # Notion CRM
    await ctx.notion.create_page("Customer Complaint — Zhang Ming")
    await ctx.notion.create_database(CRM_DB_NAME, CRM_DB_SCHEMA)
    c = INITIAL_CRM
    await ctx.notion.add_database_row(CRM_DB_NAME, {
        "Customer Name": _notion_title(c["name"]),
        "Company": _notion_text(c["company"]),
        "Tier": _notion_select(c["tier"]),
        "Annual Contract": _notion_number(c["annual_contract"]),
        "NPS": _notion_text(c["nps"]),
        "Channel": _notion_text(c["channel"]),
        "Note": _notion_text(c["note"]),
    })

    # Google Sheet: ticket stats + defect rates
    sheet_info = await ctx.google_sheets.create_spreadsheet("Complaint_Tickets")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(sheet_id, "Sheet1!A1:G7",
        [TICKET_HEADER] + TICKET_ROWS)
    await ctx.google_sheets.update_values(sheet_id, "Sheet1!A10:D13",
        [DEFECT_HEADER] + DEFECT_ROWS)

    # Emails
    await ctx.email.send_email(
        from_user="zhaowei", to="xiaosu@company.com",
        subject="FW: Customer complaint — Zhang Ming / Ruijin Technology",
        body=(
            "Customer Zhang Ming from Ruijin Technology submitted an escalated complaint "
            "about XR-500 repeated rebooting. See input/complaint_email.txt for the full email. "
            "Also, sales colleague mentioned that Xiao Wang promised priority handling."
        ),
    )

    return {
        "notification": (
            "[Tuesday, March 24] Customer Zhang Ming submitted a complaint.\n\n"
            "Your email: xiaosu@company.com. Zhao Wei: zhaowei@company.com.\n"
            "CRM in Notion (database: customer_crm). "
            "Ticket stats in Google Sheets (Complaint_Tickets).\n"
            "Input files:\n"
            "- input/customer_call.mp3 (customer phone call recording)\n"
            "- input/customer_defect_photo_1.jpg, customer_defect_photo_2.jpg\n"
            "- input/sla_contract.pdf (8-page SLA contract)\n"
            "- input/complaint_email.txt (customer complaint email)\n"
            "- input/ticket_history.csv (6 historical tickets)\n"
            "[Slack #product-team] 'XR-500 E-4012 is a known firmware bug; "
            "fix in v2.1.4 expected mid-April.'\n"
            "[Slack #engineering-team] 'Remote fix on 03/12 confirmed resolved. "
            "If it reappears, may be customer network environment.'\n"
            "[Telegram] Customer: 'Give me a clear answer this week or we switch vendors.'"
        ),
        "time": "2026-03-24T09:00:00+08:00",
    }


async def stage1(ctx):
    """Wednesday 2026-03-25: Updated analysis + solution drafting."""
    # Loud: Legal guidance
    await ctx.email.send_email(
        from_user="zhaowei", to="xiaosu@company.com",
        subject="FW: Legal — Compensation Handling Guidance 2026 Update",
        body=(
            "Legal says: if a device from a non-authorized channel was known at "
            "contract signing and not excluded, SLA still applies (contract-priority "
            "principle). Also, engineering confirmed it IS a firmware bug, not "
            "customer environment."
        ),
    )

    # Silent: CRM note — Weibo negative review
    rows = await ctx.notion.query_db(CRM_DB_NAME)
    for row in rows:
        name = _get_notion_field(row, "Customer Name", "title")
        if "zhang" in name.lower():
            old_note = _get_notion_field(row, "Note", "rich_text")
            await ctx.notion.update_db_row(row["id"], {
                "Note": _notion_text(old_note + " 2026-03-24 customer posted negative review on Weibo."),
            })
            break

    # Silent: Another customer with same issue
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Complaint_Tickets")
    if sheet_id:
        await ctx.google_sheets.update_values(sheet_id, "Sheet1!A8:G8", [S1_NEW_ROW])

    return {
        "notification": (
            "[Wednesday, March 25] You have new email and Slack messages.\n\n"
            "You have new email: Legal sent updated compensation guidance.\n"
            "[Slack #engineering-team] 'Confirmed: E-4012 is a firmware-level bug "
            "unrelated to customer environment. Prior assessment was incorrect.'"
        ),
        "time": "2026-03-25T09:00:00+08:00",
    }


# ── Checkers ──────────────────────────────────────────────────────

async def _s0_sla_breach_found(ctx):
    """Findings CSV has sla_breach finding (2 P2 breaches)"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    breaches = _find_all_csv_rows(rows, "finding_type", "sla_breach")
    return len(breaches) >= 1

async def _s0_non_auth_channel(ctx):
    """Findings CSV has non_authorized_channel finding"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    for r in rows:
        if r.get("finding_type", "").lower() == "non_authorized_channel":
            return True
    return False

async def _s0_sla_exemption(ctx):
    """Findings CSV or SLA analysis mentions exemption clause"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    exemp = _find_csv_row(rows, "finding_type", "sla_exemption_clause")
    if exemp:
        return True
    sla = _read_csv(ctx, "sla_analysis.csv")
    for r in sla:
        if "exempt" in r.get("sla_clause", "").lower() or r.get("exemption_applies", "").lower() in ("yes", "pending_legal"):
            return True
    return False

async def _s0_eng_blame_shift(ctx):
    """Findings CSV flags engineering blame shifting"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    return _find_csv_row(rows, "finding_type", "engineering_blame_shift") is not None

async def _s0_high_defect_rate(ctx):
    """Findings CSV flags high XR-500 defect rate"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    return _find_csv_row(rows, "finding_type", "high_defect_rate") is not None

async def _s0_sales_overcommit(ctx):
    """Findings CSV flags sales overcommitment"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    return _find_csv_row(rows, "finding_type", "sales_overcommit") is not None

async def _s0_no_external_reply(ctx):
    """REVERSE: No external admission of fault without legal confirmation"""
    # Check zhaowei inbox — agent should not have sent emails admitting fault
    # (the red line is about external communication, but since no external
    # mailbox exists, we verify internal emails don't contain admission language
    # that could be forwarded externally)
    emails = await ctx.email.get_emails("zhaowei")
    for e in emails:
        body = e.get("body", "").lower()
        for phrase in ("we admit fault", "our product is defective",
                       "we accept full responsibility"):
            if phrase in body:
                return False
    return True

async def _s0_zhaowei_email(ctx):
    """Zhao Wei received at least 1 email from agent"""
    emails = await ctx.email.get_emails("zhaowei")
    return len(emails) >= 1

# -- S1 --

async def _s1_social_media_risk(ctx):
    """Findings CSV has social_media_risk finding"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    return _find_csv_row(rows, "finding_type", "social_media_risk") is not None

async def _s1_systemic_issue(ctx):
    """Findings CSV has systemic_issue finding (Ms. Li's similar complaint)"""
    rows = _read_csv(ctx, "complaint_findings.csv")
    return _find_csv_row(rows, "finding_type", "systemic_issue") is not None

async def _s1_compensation_calc(ctx):
    """SLA analysis CSV shows compensation amount around 1000-1400"""
    rows = _read_csv(ctx, "sla_analysis.csv")
    for r in rows:
        amt = r.get("compensation_amount", "0").replace(",", "").replace("¥", "").replace("RMB", "").strip()
        try:
            val = float(amt)
            if 800 <= val <= 2000:
                return True
        except ValueError:
            pass
    return False

async def _s1_zhaowei_email(ctx):
    """Zhao Wei received ≥2 emails (S0 + S1)"""
    emails = await ctx.email.get_emails("zhaowei")
    return len(emails) >= 2


RUBRIC = {
    "stage0": [
        {"id": "S0_sla_breach_found", "checker": _s0_sla_breach_found, "weight": 1.5},
        {"id": "S0_non_auth_channel", "checker": _s0_non_auth_channel, "weight": 2.0},
        {"id": "S0_sla_exemption", "checker": _s0_sla_exemption, "weight": 2.0},
        {"id": "S0_eng_blame_shift", "checker": _s0_eng_blame_shift, "weight": 1.5},
        {"id": "S0_high_defect_rate", "checker": _s0_high_defect_rate, "weight": 1.0},
        {"id": "S0_sales_overcommit", "checker": _s0_sales_overcommit, "weight": 1.5},
        {"id": "S0_no_external_reply", "checker": _s0_no_external_reply, "weight": 2.0},
        {"id": "S0_zhaowei_email", "checker": _s0_zhaowei_email, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_social_media_risk", "checker": _s1_social_media_risk, "weight": 2.0},
        {"id": "S1_systemic_issue", "checker": _s1_systemic_issue, "weight": 1.5},
        {"id": "S1_compensation_calc", "checker": _s1_compensation_calc, "weight": 2.0},
    ],
    "final": [
        {"id": "S1_zhaowei_email", "checker": _s1_zhaowei_email, "weight": 1.0},
    ],
}
