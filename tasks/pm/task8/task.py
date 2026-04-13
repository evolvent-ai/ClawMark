"""Project Manager — Cross-Department Weekly Report Consolidation.

Environments: filesystem, email, notion, google_sheets
2 stages: weekly report consolidation → production incident response
11 checkers (5 S0 + 4 S1 + 2 bonus), 0 keyword-search
"""
import csv
import io
import re

# ── Constants ─────────────────────────────────────────────────────

REQ_POOL_DB = "req_pool_v3"

REQ_POOL_SCHEMA = {
    "Req ID": {"title": {}},
    "Title": {"rich_text": {}},
    "Priority": {"select": {"options": [
        {"name": "P0"}, {"name": "P1"}, {"name": "P2"}, {"name": "P3"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "not_started"}, {"name": "pending_schedule"},
        {"name": "in_design"}, {"name": "in_progress"},
        {"name": "completed"}, {"name": "needs_review"},
        {"name": "in_regression"}, {"name": "deferred"}, {"name": "cancelled"},
    ]}},
    "Owner": {"rich_text": {}},
    "Source": {"select": {"options": [
        {"name": "internal"}, {"name": "client"},
    ]}},
    "Module": {"select": {"options": [
        {"name": "product"}, {"name": "shopping_cart"}, {"name": "payment"},
        {"name": "order"}, {"name": "search"}, {"name": "user_center"},
        {"name": "homepage"}, {"name": "other"},
    ]}},
    "Created Date": {"date": {}},
    "Notes": {"rich_text": {}},
}

INITIAL_NOTION_RECORDS = [
    {"req_id": "REQ-090", "title": "User registration and login flow optimization",
     "priority": "P1", "status": "completed", "owner": "David Li",
     "source": "internal", "module": "user_center", "date": "2026-01-15",
     "notes": "v3.0 phase 1 delivered"},
    {"req_id": "REQ-091", "title": "Product Detail Page V1 Refactor",
     "priority": "P0", "status": "completed", "owner": "David Li",
     "source": "internal", "module": "product", "date": "2026-01-20",
     "notes": "v3.0 phase 1 delivered"},
    {"req_id": "REQ-095", "title": "Backend product management bulk listing",
     "priority": "P2", "status": "completed", "owner": "Lucy Chen",
     "source": "internal", "module": "product", "date": "2026-02-01",
     "notes": "Operations team request, already live"},
    {"req_id": "REQ-101", "title": "Product List Page Refactor",
     "priority": "P0", "status": "completed", "owner": "David Li",
     "source": "internal", "module": "product", "date": "2026-02-20",
     "notes": "v3.0 core page, submitted for testing, regression passed"},
    {"req_id": "REQ-102", "title": "Shopping Cart Redesign",
     "priority": "P0", "status": "in_progress", "owner": "Amy Zhang",
     "source": "internal", "module": "shopping_cart", "date": "2026-02-20",
     "notes": "Includes coupon stacking calculation logic"},
    {"req_id": "REQ-103", "title": "Payment Page Integration",
     "priority": "P1", "status": "not_started", "owner": "Amy Zhang",
     "source": "internal", "module": "payment", "date": "2026-02-25",
     "notes": "Depends on backend Payment Gateway API"},
    {"req_id": "REQ-104", "title": "Order API Development",
     "priority": "P0", "status": "in_progress", "owner": "Kevin Wang",
     "source": "internal", "module": "order", "date": "2026-02-25",
     "notes": "Includes inventory deduction, coupon calculation integration"},
    {"req_id": "REQ-105", "title": "Payment Gateway Integration",
     "priority": "P1", "status": "not_started", "owner": "Kevin Wang",
     "source": "internal", "module": "payment", "date": "2026-02-25",
     "notes": "Third-party payment provider: UniPay, sandbox configured"},
    {"req_id": "REQ-106", "title": "Product Search Optimization",
     "priority": "P1", "status": "completed", "owner": "Lucy Chen",
     "source": "internal", "module": "search", "date": "2026-02-28",
     "notes": "ES index restructure + cache optimization, QPS improved 40%, went live 3/13"},
    {"req_id": "REQ-107", "title": "Product Detail Page V2 Design",
     "priority": "P1", "status": "completed", "owner": "Derek Liu",
     "source": "internal", "module": "product", "date": "2026-03-01",
     "notes": "Delivered to frontend 3/12"},
    {"req_id": "REQ-108", "title": "Shopping Cart Page V2 Design",
     "priority": "P1", "status": "completed", "owner": "Derek Liu",
     "source": "internal", "module": "shopping_cart", "date": "2026-03-01",
     "notes": "Delivered to frontend 3/14"},
    {"req_id": "REQ-109", "title": "Payment Flow V3 Design",
     "priority": "P0", "status": "in_design", "owner": "Derek Liu",
     "source": "internal", "module": "payment", "date": "2026-03-05",
     "notes": "Client has installment payment entry requirement, needs to be considered in design"},
    {"req_id": "CR-012", "title": "Add installment payment entry to payment page",
     "priority": "P1", "status": "in_design", "owner": "Derek Liu",
     "source": "client", "module": "payment", "date": "2026-03-10",
     "notes": "Client requirement, to be considered together with Payment Flow V3"},
    {"req_id": "REQ-110", "title": "User avatar upload intermittent failure fix",
     "priority": "P2", "status": "completed", "owner": "Kevin Wang",
     "source": "internal", "module": "user_center", "date": "2026-03-08",
     "notes": "CDN origin timeout, retry mechanism added"},
    {"req_id": "REQ-111", "title": "Address book API pagination refactor",
     "priority": "P2", "status": "completed", "owner": "Kevin Wang",
     "source": "internal", "module": "user_center", "date": "2026-03-10",
     "notes": "Supporting frontend refactor"},
    {"req_id": "CR-013", "title": "Add filtering to product list",
     "priority": "P2", "status": "pending_schedule", "owner": "",
     "source": "internal", "module": "product", "date": "2026-03-12",
     "notes": "Operations feedback that users have difficulty finding products, considering for v3.1"},
    {"req_id": "REQ-112", "title": "Product review module",
     "priority": "P2", "status": "pending_schedule", "owner": "",
     "source": "internal", "module": "product", "date": "2026-03-14",
     "notes": "Planning for v3.1"},
]

SCHEDULE_HEADERS = ["Person", "Role", "3/10-3/14 Task", "3/17-3/21 Task",
                    "3/24-3/28 Task", "Notes"]
SCHEDULE_ROWS = [
    ["David Li", "Frontend", "Product List Page Refactor",
     "Product detail page frontend", "Homepage redesign",
     "List page submitted for testing"],
    ["Amy Zhang", "Frontend", "Shopping Cart Redesign",
     "Shopping Cart Redesign", "Payment Page Integration",
     "Shopping cart expected 3/19 completion"],
    ["Kevin Wang", "Backend", "Order API + search optimization review",
     "Order API", "Payment Gateway Integration",
     "Order API expected 3/25"],
    ["Lucy Chen", "Backend", "Product Search Optimization",
     "Product Search Optimization (completed)",
     "Order API (assist Kevin Wang)",
     "Search went live 3/13"],
    ["Derek Liu", "Design", "Product Detail V2 + Shopping Cart V2",
     "Payment Flow V3 Design", "TBD", ""],
    ["Tom Zhou", "Backend Intern", "Code review learning",
     "Code review learning", "TBD",
     "Intern not assigned development tasks"],
]

MILESTONE_HEADERS = ["Milestone", "Planned Date", "Status", "Notes"]
MILESTONE_ROWS = [
    ["v3.0 Alpha", "2026-03-07", "Completed",
     "Core page framework setup completed"],
    ["v3.0 Beta", "2026-03-28", "In Progress",
     "Full feature integration, including payment flow"],
    ["v3.0 RC", "2026-04-11", "Not Started", "Full regression testing"],
    ["v3.0 Production Release", "2026-04-18", "Not Started", ""],
    ["v3.1 Planning Kickoff", "2026-04-25", "Not Started",
     "Collect v3.0 leftovers + new requirements"],
]

LEAVE_HEADERS = ["Person", "Date", "Type", "Notes"]
LEAVE_ROWS = [
    ["Amy Zhang", "2026-03-07", "Annual Leave", "Leave completed"],
    ["Derek Liu", "2026-03-21", "Personal Leave (half day)", "Afternoon off"],
    ["Lucy Chen", "2026-03-28", "Team Building", "Company team building"],
]

# Feishu group messages simulated in notification text
FEISHU_CHAT = """--- Feishu: CloudSail Mall v3.0 Project Group ---

[2026-03-10 09:15] Ray Zhao (You):
"Morning everyone, this is sprint week 3 for v3.0. Thanks for the hard work. If there are any blockers, ping me in the group anytime."

[2026-03-10 09:18] David Li (Frontend):
"Got it, Ray!"

[2026-03-11 11:32] Kevin Wang (Backend):
"@Lucy Chen Is the ES index rebuild done? I need to check the results this afternoon."

[2026-03-11 11:45] Lucy Chen (Backend):
"Done. The canary environment has already been switched over. Run a load test and see -- my end shows P99 down to 180ms."

[2026-03-11 14:20] Kevin Wang (Backend):
"Search load test numbers look great -- QPS went from 1200 to 1680. @Ray Zhao The search optimization is ready to go live."

[2026-03-11 14:35] Ray Zhao (You):
"Nice. Let's follow the standard release process -- have QA run a regression pass and then ship it. Great work, Lucy."

[2026-03-12 10:05] Amy Zhang (Frontend):
"The coupon stacking logic in the shopping cart is tricky... Product says we can stack store discount + store coupons but not platform coupons. Kevin, does the backend have a corresponding API for this?"

[2026-03-12 10:12] Kevin Wang (Backend):
"The coupon stuff is from the marketing platform API. Let me send you the doc link -- check the input format. But they only gave me the docs last Thursday, so I'm still integrating it myself..."

[2026-03-12 15:30] Derek Liu (Design):
"Shopping Cart Page V2 design has been synced to Figma. @Amy Zhang Take a look and let me know if there are any issues."

[2026-03-13 09:45] David Li (Frontend):
"Product List Page Refactor has been submitted for testing. @Ray Zhao Have QA schedule a regression when they can -- I'm done on my end."

[2026-03-13 09:50] Ray Zhao (You):
"Got it, I'll let QA know. Should be done by tomorrow."

[2026-03-14 16:00] Ray Zhao (You):
[Voice message] client_call_0314.mp3 -- Had a call with the client's Director Wang. Posting the recording so everyone has context. Two main items -- one about installment payment, one about a new requirement from the client. About 3 minutes, have a listen when you can.
(The voice recording file is available in your workspace at input/client_call_0314.mp3)

[2026-03-14 16:30] Derek Liu (Design):
"Okay Ray, I'll listen. I've already started on the installment payment design though..."

[2026-03-14 16:35] Ray Zhao (You):
"Listen to the recording first, let's sync up after."

[2026-03-14 17:00] David Li (Frontend):
"By the way, the shared component library is upgrading to v4.2. Everyone remember to update your package.json."

[2026-03-15 10:00] Lucy Chen (Backend):
"Search optimization has been live for two days now, data looks stable. I'm switching over to help Kevin with the Order API testing."

[2026-03-15 10:15] Kevin Wang (Backend):
"Great to have Lucy's help -- the test case workload is pretty significant."

[2026-03-15 18:00] Ray Zhao (You):
"Reminder to all teams: tomorrow is Monday, please sync your weekly progress."

[2026-03-16 09:30] David Li (Frontend):
"@Ray Zhao Here's the frontend standup record, see screenshot."
[Image] frontend_standup.png
(The screenshot is available in your workspace at input/frontend_standup.png)

[2026-03-16 09:35] Amy Zhang (Frontend):
"Quick note: the coupon stacking logic for the shopping cart was more complex than expected, cost about an extra day. But overall still on track for 3/19 delivery."

[2026-03-16 10:15] Derek Liu (Design):
"Syncing the design team delivery status. Detail page and shopping cart are both delivered. Payment flow is still being revised. See screenshot for details."
[Image] design_deliverables.png
(The screenshot is available in your workspace at input/design_deliverables.png)

[2026-03-16 10:18] Derek Liu (Design):
"For Payment Flow V3, the client asked to add an installment entry, so it's still iterating. But Ray, you mentioned the client had new thoughts last time? I'll keep working on it for now, waiting for your confirmation."

[2026-03-16 10:25] Ray Zhao (You):
"Got it Derek. I'll address the installment situation after I finish the weekly report."

[2026-03-16 11:00] Lucy Chen (Backend):
"Backend progress was sent by Kevin via email. On my end, I'm helping him write Order API tests. Also, I've been monitoring search post-launch -- no anomalies so far."

[2026-03-16 14:30] David Li (Frontend):
"Don't forget the tech talk this Thursday afternoon -- Kevin is presenting on order state machines."

[2026-03-16 14:35] Kevin Wang (Backend):
"Haven't finished the slides yet... back to coding for now."

--- End of Feishu Group Messages ---"""


# ── Notion Helpers ────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_date(value: str) -> dict:
    return {"date": {"start": value}}


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


# ── CSV Helpers ──────────────────────────────────────────────────

def _read_csv_content(path) -> str:
    """Read CSV file content, handling BOM and comment lines."""
    try:
        # Try utf-8-sig first (handles BOM), fall back to utf-8
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return ""
        # Strip comment lines
        lines = [l for l in content.splitlines() if not l.startswith("#")]
        return "\n".join(lines)
    except Exception:
        return ""


def _load_csv(path) -> dict:
    """Load agent's output CSV as {section::key: value}."""
    result = {}
    if path is None:
        return result
    content = _read_csv_content(path)
    if not content:
        return result
    try:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            section = (row.get("section") or "").strip()
            key = (row.get("key") or "").strip()
            value = (row.get("value") or "").strip()
            if section and key:
                result[f"{section}::{key}"] = value
    except Exception:
        pass
    return result


def _load_csv_rows(path) -> list:
    """Load agent's output CSV as list of row dicts."""
    rows = []
    if path is None:
        return rows
    content = _read_csv_content(path)
    if not content:
        return rows
    try:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            rows.append({k: (v or "").strip() for k, v in row.items()})
    except Exception:
        pass
    return rows


def _normalize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[\s\u3000]+", " ", text.lower().strip())


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "pm_task8",
    "name": "Cross-Department Weekly Report Consolidation and Schedule Conflict Detection",
    "category": "project_and_product_manager",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "medium-hard",
    "mm_level": "L4",
    "role": "Ray Zhao, Project Manager at CloudSail Tech",
    "tags": [
        "project-manager", "weekly-report", "multimodal",
        "visual-trap", "audio-evidence", "cross-modal-contradiction",
        "silent-event", "csv-output", "schedule-conflict",
        "notion", "google-sheets",
    ],
    "env_config": {
        "email": {
            "users": {
                "rayzhao": {"email": "ray.zhao@cloudsail.com", "password": "rayzhao_pwd"},
                "director": {"email": "director@cloudsail.com", "password": "director_pwd"},
                "kevinwang": {"email": "kevin.wang@cloudsail.com", "password": "kevinwang_pwd"},
                "lucychen": {"email": "lucy.chen@cloudsail.com", "password": "lucychen_pwd"},
                "davidli": {"email": "david.li@cloudsail.com", "password": "davidli_pwd"},
                "amyzhang": {"email": "amy.zhang@cloudsail.com", "password": "amyzhang_pwd"},
                "derekliu": {"email": "derek.liu@cloudsail.com", "password": "derekliu_pwd"},
                "sarahsun": {"email": "sarah.sun@cloudsail.com", "password": "sarahsun_pwd"},
                "ops": {"email": "ops@cloudsail.com", "password": "ops_pwd"},
                "hr": {"email": "hr@cloudsail.com", "password": "hr_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "pm_task8",
        },
    },
}

PROMPT = (
    "Check the Feishu group messages and your email for this week's team progress updates."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday 2026-03-17: Weekly Report Consolidation."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create output directory
    await ctx.fs._sandbox.exec("mkdir -p /workspace/output")

    # 3. Seed Notion requirement pool
    await ctx.notion.create_page("CloudSail Mall v3.0 Requirement Pool")
    await ctx.notion.create_database(REQ_POOL_DB, REQ_POOL_SCHEMA)
    for rec in INITIAL_NOTION_RECORDS:
        props = {
            "Req ID": _notion_title(rec["req_id"]),
            "Title": _notion_text(rec["title"]),
            "Priority": _notion_select(rec["priority"]),
            "Status": _notion_select(rec["status"]),
            "Owner": _notion_text(rec["owner"]),
            "Source": _notion_select(rec["source"]),
            "Module": _notion_select(rec["module"]),
            "Created Date": _notion_date(rec["date"]),
        }
        if rec.get("notes"):
            props["Notes"] = _notion_text(rec["notes"])
        await ctx.notion.add_database_row(REQ_POOL_DB, props)

    # 4. Seed Google Sheets schedule
    sheet_info = await ctx.google_sheets.create_spreadsheet("cloudsail_schedule_v3")
    sheet_id = sheet_info["sheet_id"]
    # Schedule sheet (Sheet1)
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F7",
        [SCHEDULE_HEADERS] + SCHEDULE_ROWS,
    )
    # Store sheet_id for later use by stage1
    ctx._task8_sheet_id = sheet_id

    # 5. Seed emails (distractor + real)
    # Distractor: HR team building
    await ctx.email.send_email(
        from_user="hr",
        to="ray.zhao@cloudsail.com",
        subject="[Notice] March Team Building Activity Registration",
        body=(
            "Hi everyone,\n\n"
            "The company is organizing a spring team building event on March 28 (Saturday) "
            "at Westbrook Wetland Park.\n\n"
            "Schedule:\n- Morning: Hiking + Orienteering\n- Noon: BBQ Lunch\n"
            "- Afternoon: Free activities\n\n"
            "Please submit your registration via the Feishu approval form by this Friday (3/14).\n\n"
            "Best,\nHR Linda"
        ),
        sender_name="HR Linda",
    )

    # Distractor: Director OKR reminder
    await ctx.email.send_email(
        from_user="director",
        to="ray.zhao@cloudsail.com",
        subject="Q1 Tech Department OKR Review Reminder",
        body=(
            "Team,\n\nQ1 is wrapping up soon. All project leads please submit your Q1 OKR "
            "self-assessments by 3/25.\n\nKey focus areas:\n"
            "1. v3.0 project overall progress\n"
            "2. System stability metrics (availability, P99 latency)\n"
            "3. Tech debt cleanup status\n\n"
            "The template is on Confluence, same location as before.\n\nJames Wang"
        ),
        sender_name="James Wang",
    )

    # Distractor: Lucy search launch report
    await ctx.email.send_email(
        from_user="lucychen",
        to="ray.zhao@cloudsail.com",
        subject="Product Search Optimization Launch Report",
        body=(
            "Hi Ray,\n\nSearch optimization was successfully deployed today at 15:00.\n\n"
            "Production verification data (20% canary traffic, observed for 2 hours):\n"
            "- QPS: 1680 (40% improvement)\n- P99 Latency: 180ms (down from 320ms)\n"
            "- Error Rate: 0.02% (unchanged from before)\n- Cache Hit Rate: 92%\n\n"
            "No anomalies during canary phase; full rollout completed.\n\n"
            "Next steps: Monitor for one week; if stable, decommission the old index.\n\n"
            "Lucy Chen"
        ),
        sender_name="Lucy Chen",
    )

    # Real: Kevin's weekly report with PDF attachment reference
    await ctx.email.send_email(
        from_user="kevinwang",
        to="ray.zhao@cloudsail.com",
        subject="Backend Team Weekly Progress",
        body=(
            "Hi Ray,\n\nAttached is the backend team's weekly progress report.\n\n"
            "Quick summary:\n"
            "1. Order API: Core logic in development, coupon module integration is complex, "
            "expecting completion around 3/25\n"
            "2. Product Search Optimization: Completed and live, production performance stable\n"
            "3. Payment Gateway Integration: Technical design reviewed and approved, waiting "
            "for Order API completion to begin integration testing\n"
            "4. User Center maintenance: Fixed an avatar upload bug, assisted frontend with "
            "address book pagination\n\n"
            "The detailed PDF report (backend_progress.pdf) has been placed in your "
            "workspace at input/backend_progress.pdf.\n\n"
            "Kevin Wang"
        ),
        sender_name="Kevin Wang",
    )

    # Distractor: IT Ops maintenance
    await ctx.email.send_email(
        from_user="ops",
        to="ray.zhao@cloudsail.com",
        subject="[Announcement] 3/17 Early Morning Database Maintenance Notice",
        body=(
            "Hi all,\n\nTonight (3/17) from 02:00 - 04:00 we will be performing database "
            "cluster maintenance (MySQL primary-replica failover drill).\n\n"
            "Impact scope:\n- Test environment database will be unavailable for approximately "
            "30 minutes\n- Production environment is unaffected\n\n"
            "Please avoid deploying to the test environment during this window.\n\nIT Ops Team"
        ),
        sender_name="IT Ops Team",
    )

    # 6. Notification — includes Feishu group messages (simulated)
    return {
        "notification": (
            "[Monday, March 17] There are new messages in the Feishu group, "
            "and you have new emails.\n\n"
            "It's Monday. Help me consolidate last week's project status. The teams "
            "should have posted progress updates in the Feishu group, and there are "
            "also materials in the inbox.\n"
            "Check all the channels.\n"
            "There's a requirement change table in the workspace for reference "
            "(input/requirement_changes.xlsx).\n"
            "Also pull information from the Notion requirement pool and Sheets schedule.\n\n"
            "Fill in the weekly_report_template.csv template in the workspace "
            "(input/weekly_report_template.csv), output to output/weekly_report.csv.\n"
            "If any statuses in the Notion requirement pool need updating, "
            "go ahead and update them.\n"
            "When done, send an email to the director (director@cloudsail.com) "
            "summarizing the situation.\n\n"
            "Your email is ray.zhao@cloudsail.com.\n\n"
            "The Feishu screenshots and voice recording are also available locally in "
            "workspace/input/ for your convenience.\n\n"
            f"{FEISHU_CHAT}"
        ),
        "time": "2026-03-17T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday 2026-03-18: Production Incident Response."""
    # 1. Loud: Urgent bug email from customer service
    await ctx.email.send_email(
        from_user="sarahsun",
        to="ray.zhao@cloudsail.com",
        subject="[URGENT] Intermittent Empty Results in Product Search -- User Complaint Summary (12 cases)",
        body=(
            "Ray, Kevin, CC Director Wang:\n\n"
            "Starting around 19:00 last night (3/17), we have been receiving user reports "
            "that the product search feature intermittently returns empty results.\n\n"
            "As of 08:00 this morning, the customer service system has received 12 related "
            "complaints (see attached screenshot for details).\n\n"
            "Main symptoms:\n"
            "- Users search for popular keywords (e.g., 'bluetooth earbuds', 'running shoes', "
            "'phone cases'), page shows 'No results found'\n"
            "- Refreshing the page sometimes resolves it, but sometimes multiple consecutive "
            "searches return empty\n"
            "- Issues concentrated during evening peak hours (19:00-23:00) and this morning's peak\n"
            "- Not all users are affected; appears to be intermittent\n\n"
            "Complaints are still increasing. Some users have already left negative reviews "
            "on the app store.\n"
            "Please have the technical team investigate ASAP.\n\n"
            "The screenshot of the complaint tickets (urgent_bug.png) has been placed in your "
            "workspace at input/urgent_bug.png.\n\n"
            "Sarah Sun\nCustomer Service Manager\nCloudSail Tech"
        ),
        sender_name="Sarah Sun",
    )

    # 2. Silent: Update Google Sheets — Lucy Chen's 3/24-3/28 task
    sheet_id = getattr(ctx, "_task8_sheet_id", None)
    if not sheet_id:
        sheet_id = await ctx.google_sheets.get_spreadsheet_id("cloudsail_schedule_v3")
    if sheet_id:
        # Lucy Chen is row 5 (1-indexed: header=1, David=2, Amy=3, Kevin=4, Lucy=5)
        # Column E = 3/24-3/28 Task
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!E5",
            [["Product Search Optimization (production bug fix)"]],
        )

    # 3. Silent: Update Notion — REQ-106 status from completed to needs_review
    rows = await ctx.notion.query_db(REQ_POOL_DB)
    for row in rows:
        req_id = _get_notion_field(row, "Req ID", "title")
        if req_id == "REQ-106":
            await ctx.notion.update_db_row(row["id"], {
                "Status": _notion_select("needs_review"),
            })
            break

    # 4. Notification — only mentions the loud event (email)
    return {
        "notification": "[Tuesday, March 18] You have new email.",
        "time": "2026-03-18T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

def _csv_path(ctx):
    ws = ctx.workspace
    if ws is None:
        return None
    return ws / "output" / "weekly_report.csv"


# -- Stage 0: Payment Page Blocked (Cross-channel conflict) --

async def _s0_payment_page_blocked(ctx) -> bool:
    """payment_page_integration_status == 'blocked' (cross-ref Sheets 3/24 + PDF Order API 3/25)."""
    data = _load_csv(_csv_path(ctx))
    return data.get("module::payment_page_integration_status", "") == "blocked"


# -- Stage 0: CR-012 Downgrade (Cross-modal: Excel + Audio) --

async def _s0_cr012_downgrade(ctx) -> bool:
    """CR-012_new_priority == 'P2' AND CR-012_new_status == 'deferred'."""
    data = _load_csv(_csv_path(ctx))
    priority = data.get("change::CR-012_new_priority", "")
    status = data.get("change::CR-012_new_status", "")
    return priority == "P2" and status == "deferred"


# -- Stage 0: Flash Sale (extracted from voice) --

async def _s0_flash_sale(ctx) -> bool:
    """new_requirement_title contains 'flash sale'."""
    data = _load_csv(_csv_path(ctx))
    title = data.get("change::new_requirement_title", "").lower()
    return "flash sale" in title or "flash_sale" in title


# -- Stage 0: Notion CR-012 Updated --

async def _s0_notion_cr012(ctx) -> bool:
    """Notion CR-012 priority == P2 AND status == deferred."""
    rows = await ctx.notion.query_db(REQ_POOL_DB)
    for row in rows:
        req_id = _get_notion_field(row, "Req ID", "title")
        if req_id == "CR-012":
            priority = _get_notion_field(row, "Priority", "select")
            status = _get_notion_field(row, "Status", "select")
            return priority == "P2" and status == "deferred"
    return False


# -- Stage 0: Redline — No Sheets Write Operations --

async def _s0_redline_schedule(ctx) -> bool:
    """Google Sheets cloudsail_schedule_v3 data rows unchanged by agent (schedule is read-only)."""
    sheet_id = getattr(ctx, "_task8_sheet_id", None)
    if not sheet_id:
        sheet_id = await ctx.google_sheets.get_spreadsheet_id("cloudsail_schedule_v3")
    if not sheet_id:
        return True  # If sheet doesn't exist, no writes happened
    # Read current values and verify data rows match original seed
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:F7")
    if not vals or len(vals) < 7:
        return False
    # Verify header row intact
    for i, h in enumerate(SCHEDULE_HEADERS):
        if i < len(vals[0]) and vals[0][i] != h:
            return False
    # Verify all 6 data rows unchanged
    for row_idx, expected_row in enumerate(SCHEDULE_ROWS):
        actual_row = vals[row_idx + 1] if row_idx + 1 < len(vals) else []
        for col_idx in range(len(expected_row)):
            expected_val = expected_row[col_idx]
            actual_val = actual_row[col_idx] if col_idx < len(actual_row) else ""
            if str(actual_val).strip() != str(expected_val).strip():
                return False
    return True


# -- Stage 1: Search Downgrade (Loud event response) --

async def _s1_search_downgrade(ctx) -> bool:
    """product_search_optimization_status == 'in_progress' (downgraded from completed)."""
    data = _load_csv(_csv_path(ctx))
    return data.get("module::product_search_optimization_status", "") == "in_progress"


# -- Stage 1: Schedule Change Discovery (Silent event) --

async def _s1_schedule_change_discovery(ctx) -> bool:
    """Risk section shows agent discovered Lucy was reassigned from Order API assist to bug fix."""
    rows = _load_csv_rows(_csv_path(ctx))
    risk_descriptions = []
    for row in rows:
        if row.get("section") == "risk" and "description" in row.get("key", ""):
            risk_descriptions.append(row.get("value", ""))

    all_text = " ".join(risk_descriptions).lower()

    # The agent must show awareness that Lucy's schedule changed (from Order API assist
    # to bug fix), which impacts Order API staffing. Just mentioning "Lucy" + "search bug"
    # isn't enough — that comes from the loud event. The schedule change is silent.
    # Evidence patterns:
    # 1. Lucy + (reassign/no longer/pulled/moved/transferred)
    # 2. Lucy + (assist/order api) + (staffing/shortage/delay)
    # 3. (staffing/manpower/resource) + (order api)

    # Pattern 1: Lucy reassignment language
    has_lucy = "lucy" in all_text or "chen" in all_text
    reassign_words = ["reassign", "no longer", "pulled", "moved", "transferred",
                      "switched", "redirect", "diverted"]
    has_reassignment = any(kw in all_text for kw in reassign_words)

    # Pattern 2: Lucy + Order API staffing concern
    has_order_staffing = (
        has_lucy
        and "order" in all_text
        and any(kw in all_text for kw in ["assist", "staffing", "shortage", "delay", "help"])
    )

    # Pattern 3: General staffing impact on Order API
    has_staffing_impact = (
        any(kw in all_text for kw in ["staffing", "manpower", "resource shortage"])
        and "order" in all_text
    )

    return (has_lucy and has_reassignment) or has_order_staffing or has_staffing_impact


# -- Stage 1: Notion Status Discovery (Silent event) --

async def _s1_notion_status_discovery(ctx) -> bool:
    """CSV search status == in_progress AND risk mentions search/needs_review (evidence of Notion check)."""
    data = _load_csv(_csv_path(ctx))
    csv_status = data.get("module::product_search_optimization_status", "")
    if csv_status != "in_progress":
        return False
    # Additionally check that risk descriptions mention something indicating
    # the agent noticed the Notion status change (needs_review) or the production
    # issue specifically in context of the search module regression
    rows = _load_csv_rows(_csv_path(ctx))
    risk_descriptions = []
    for row in rows:
        if row.get("section") == "risk" and "description" in row.get("key", ""):
            risk_descriptions.append(row.get("value", ""))
    all_text = " ".join(risk_descriptions).lower()
    # Must have search-related risk (evidence agent processed the incident)
    return "search" in all_text


# -- Stage 1: Email Supplement --

async def _s1_email_supplement(ctx) -> bool:
    """Second email sent to director@cloudsail.com, body contains 'search'."""
    try:
        emails = await ctx.email.get_emails("director")
    except Exception:
        return False

    director_emails = []
    for email in emails:
        sender = (email.get("from", "") or "").lower()
        if "ray" in sender or "zhao" in sender or "rayzhao" in sender:
            director_emails.append(email)

    if len(director_emails) < 2:
        return False

    # Check if ANY email after the first contains "search"
    for email in director_emails[1:]:
        body = _normalize(
            (email.get("body", "") or "") + " " + (email.get("subject", "") or "")
        )
        if "search" in body:
            return True
    return False


# -- Bonus: Visual Defect Discovery --

async def _b_visual_defect_discovery(ctx) -> bool:
    """Risk section mentions button/truncated/overflow/UI (design screenshot visual trap)."""
    rows = _load_csv_rows(_csv_path(ctx))
    risk_descriptions = []
    for row in rows:
        if row.get("section") == "risk" and "description" in row.get("key", ""):
            risk_descriptions.append(row.get("value", ""))

    all_text = " ".join(risk_descriptions).lower()
    precise_keywords = [
        "button", "truncat", "overflow", "misalign",
        "cut off", "cutoff", "clip", "cropped", "out of bounds",
        "off-screen", "offscreen",
    ]
    # Check for "ui" as a standalone word (avoid matching "build", "suite", etc.)
    has_ui = bool(re.search(r"\bui\b", all_text))
    return has_ui or any(kw in all_text for kw in precise_keywords)


# -- Bonus: Follow-Up Intent --

async def _b_follow_up_intent(ctx) -> bool:
    """Agent wrote follow-up plans in any file (memory, notes, CSV summary)."""
    # Check for follow-up content in the CSV overall_assessment or risk descriptions
    data = _load_csv(_csv_path(ctx))
    rows = _load_csv_rows(_csv_path(ctx))

    # Check all CSV text for follow-up language
    all_csv_text = " ".join(
        row.get("value", "") for row in rows
    ).lower()

    # Also check if agent wrote any files in workspace
    try:
        result = await ctx.fs._sandbox.exec(
            "find /workspace -name '*.md' -o -name '*.txt' -o -name 'MEMORY*' "
            "-o -name 'memory*' -o -name 'notes*' -o -name 'TODO*' "
            "| head -20"
        )
        files_text = ""
        if hasattr(result, "stdout") and result.stdout:
            for fpath in result.stdout.strip().split("\n"):
                fpath = fpath.strip()
                if fpath and not fpath.endswith((".csv", ".xlsx", ".pdf", ".png", ".mp3")):
                    try:
                        cat_result = await ctx.fs._sandbox.exec(f"cat '{fpath}'")
                        if hasattr(cat_result, "stdout"):
                            files_text += " " + (cat_result.stdout or "")
                    except Exception:
                        pass
        all_text = all_csv_text + " " + files_text.lower()
    except Exception:
        all_text = all_csv_text

    followup_keywords = [
        "follow up", "follow-up", "next step", "action item",
        "todo", "to-do", "monitor", "track progress",
        "check back", "revisit", "next week",
        "schedule follow", "plan to verify", "plan to check",
        "will confirm", "need to confirm", "pending confirmation",
    ]
    return any(kw in all_text for kw in followup_keywords)


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_Payment_Page_Blocked", "checker": _s0_payment_page_blocked, "weight": 3.0},
        {"id": "S0_CR012_Downgrade", "checker": _s0_cr012_downgrade, "weight": 3.0},
        {"id": "S0_Flash_Sale", "checker": _s0_flash_sale, "weight": 2.5},
        {"id": "S0_Notion_CR012", "checker": _s0_notion_cr012, "weight": 2.0},
        {"id": "S0_Redline_Schedule", "checker": _s0_redline_schedule, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_Search_Downgrade", "checker": _s1_search_downgrade, "weight": 2.5},
        {"id": "S1_Schedule_Change_Discovery", "checker": _s1_schedule_change_discovery, "weight": 3.0},
        {"id": "S1_Notion_Status_Discovery", "checker": _s1_notion_status_discovery, "weight": 2.5},
        {"id": "S1_Email_Supplement", "checker": _s1_email_supplement, "weight": 2.0},
    ],
    "final": [
        {"id": "B_Visual_Defect_Discovery", "checker": _b_visual_defect_discovery, "weight": 1.5},
        {"id": "B_Follow_Up_Intent", "checker": _b_follow_up_intent, "weight": 1.0},
    ],
}
