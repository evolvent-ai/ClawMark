"""Multi-client listing matching and viewing coordination — multi-stage task.

Environments: filesystem, email, notion, google_sheets, calendar
3 stages: requirement understanding → feedback & silent changes → new listing & final
19 core checkers (0 keyword-search)
"""
import csv
from datetime import datetime
from io import StringIO

# ── Constants ────────────────────────────────────────────────────

MON = datetime(2026, 3, 18)
TUE = datetime(2026, 3, 19)
WED = datetime(2026, 3, 20)
THU = datetime(2026, 3, 21)
FRI = datetime(2026, 3, 22)

LISTING_DB = "listings_crm"
CLIENT_DB = "client_profiles"
YIELD_SHEET = "regional_rental_yield"

# ── CRM Schemas ──────────────────────────────────────────────────

LISTING_SCHEMA = {
    "Listing ID": {"title": {}},
    "Compound": {"rich_text": {}},
    "District": {"rich_text": {}},
    "Layout": {"rich_text": {}},
    "Area (sqm)": {"number": {}},
    "Asking Price (万元)": {"number": {}},
    "Floor": {"number": {}},
    "Elevator": {"rich_text": {}},
    "School District": {"rich_text": {}},
    "Subway Distance (m)": {"number": {}},
    "Renovation": {"select": {"options": [
        {"name": "Walk-up"}, {"name": "Bare shell"}, {"name": "Renovated"},
        {"name": "Well kept"}, {"name": "Run-down exterior"},
        {"name": "Japanese minimalist"}, {"name": "Luxury"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "Active"}, {"name": "Newly added"},
    ]}},
    "Photos": {"rich_text": {}},
    "Notes": {"rich_text": {}},
}

LISTINGS = [
    {"id": "L01", "compound": "Xuefu Garden", "district": "North River",
     "layout": "3BR", "area": 96, "price": 342, "floor": 6,
     "elevator": "No", "school_district": "Yes", "subway_m": 780,
     "renovation": "Walk-up", "status": "Active",
     "photos": "input/listings/L01/stairs.jpg",
     "notes": "Older walk-up building. See stairwell photo for access condition."},
    {"id": "L02", "compound": "Jinhai Residence", "district": "North River",
     "layout": "2BR", "area": 88, "price": 515, "floor": 10,
     "elevator": "Yes", "school_district": "No", "subway_m": 430,
     "renovation": "Renovated", "status": "Active",
     "photos": "",
     "notes": "Good transit location, modern renovation."},
    {"id": "L03", "compound": "Scholars Court", "district": "North River",
     "layout": "3BR", "area": 101, "price": 380, "floor": 5,
     "elevator": "Yes", "school_district": "Yes", "subway_m": 620,
     "renovation": "Well kept", "status": "Active",
     "photos": "",
     "notes": "School-district property in good condition."},
    {"id": "L04", "compound": "Riverside Mansion", "district": "South Lake",
     "layout": "4BR", "area": 126, "price": 468, "floor": 3,
     "elevator": "Yes", "school_district": "No", "subway_m": 540,
     "renovation": "Bare shell", "status": "Active",
     "photos": "",
     "notes": "Large unit on low floor. Needs full renovation."},
    {"id": "L05", "compound": "Old Town Heights", "district": "Central East",
     "layout": "2BR", "area": 72, "price": 505, "floor": 4,
     "elevator": "No", "school_district": "No", "subway_m": 320,
     "renovation": "Run-down exterior", "status": "Active",
     "photos": "input/listings/L05/exterior.jpg",
     "notes": "Highest rental yield area. See exterior photo for visual condition."},
    {"id": "L06", "compound": "Academy One", "district": "North River",
     "layout": "3BR", "area": 94, "price": 348, "floor": 8,
     "elevator": "Yes", "school_district": "Yes", "subway_m": 460,
     "renovation": "Renovated", "status": "Active",
     "photos": "input/listings/L06/school_view.jpg",
     "notes": "Window overlooks nearby primary school. See school_view photo."},
    {"id": "L07", "compound": "Metro Light City", "district": "West Hub",
     "layout": "2BR", "area": 79, "price": 620, "floor": 15,
     "elevator": "Yes", "school_district": "No", "subway_m": 210,
     "renovation": "Renovated", "status": "Active",
     "photos": "",
     "notes": "Excellent subway access, premium location."},
    {"id": "L08", "compound": "Maple Courtyard", "district": "North River",
     "layout": "3BR", "area": 98, "price": 350, "floor": 7,
     "elevator": "Yes", "school_district": "Yes", "subway_m": 690,
     "renovation": "Japanese minimalist", "status": "Active",
     "photos": "input/listings/L08/balcony.jpg, input/listings/L08/kitchen.jpg",
     "notes": "Japanese minimalist interior with floor-to-ceiling windows. See photos."},
]

CLIENT_SCHEMA = {
    "Client ID": {"title": {}},
    "Name": {"rich_text": {}},
    "Type": {"select": {"options": [
        {"name": "Buyer"}, {"name": "Investor"}, {"name": "Upgrade buyer"},
    ]}},
    "Budget": {"rich_text": {}},
    "Key Requirements": {"rich_text": {}},
    "Contact Email": {"email": {}},
    "Notes": {"rich_text": {}},
    "Attachments": {"rich_text": {}},
}

CLIENTS = [
    {"id": "C01", "name": "Ms. Li", "type": "Buyer",
     "budget": "RMB 3.0M-3.5M",
     "reqs": ("School district, 3BR or 2+1, subway within walking distance. "
              "See voice message and handwritten wishlist for full details."),
     "email": "li@client.com",
     "notes": ("Requirements not yet fully consolidated — "
               "voice and handwritten inputs pending review"),
     "attachments": ("input/client_inputs/phone_inquiry.mp3, "
                     "input/client_inputs/wishlist_handwritten.jpg")},
    {"id": "C02", "name": "Mr. Wang", "type": "Investor",
     "budget": "RMB 5.0M-8.0M",
     "reqs": ("Pure investment, prioritize yield. "
              "See investment_criteria.xlsx for screening rules."),
     "email": "wang@client.com",
     "notes": "Investment criteria in attached Excel file",
     "attachments": "input/client_inputs/investment_criteria.xlsx"},
    {"id": "C03", "name": "Zhao couple", "type": "Upgrade buyer",
     "budget": "RMB 3.5M-5.0M",
     "reqs": ("Larger home, mother will help with childcare, "
              "need suitable accessibility"),
     "email": "zhao@client.com",
     "notes": ("Current home photo and mother's medical report attached — "
               "review for lifestyle and constraint signals"),
     "attachments": ("input/client_inputs/current_home_photo.jpg, "
                     "input/client_inputs/mom_medical_report.pdf")},
]

# ── Google Sheets data ────────────────────────────────────────────

YIELD_HEADER = [
    "listing_id", "compound_name", "district", "asking_price_cny_10k",
    "monthly_rent_cny", "annualized_roi", "vacancy_rate",
    "appreciation_rate_1y", "subway_distance_m", "bedrooms",
    "size_sqm", "floor", "elevator", "school_district",
    "condition_tag", "investment_note",
]

YIELD_ROWS = [
    ["L01", "Xuefu Garden", "North River", "342", "5200", "1.82%",
     "4.8%", "2.1%", "780", "3", "96", "6", "No", "Yes",
     "Walk-up", "School district fit but no elevator."],
    ["L02", "Jinhai Residence", "North River", "515", "6900", "1.61%",
     "5.3%", "1.9%", "430", "2", "88", "10", "Yes", "No",
     "Renovated", "Good transit but ROI below target."],
    ["L03", "Scholars Court", "North River", "380", "5800", "1.83%",
     "4.4%", "2.5%", "620", "3", "101", "5", "Yes", "Yes",
     "Well kept", "School district, currently above 3.5M budget."],
    ["L04", "Riverside Mansion", "South Lake", "468", "6100", "1.56%",
     "6.2%", "2.8%", "540", "4", "126", "3", "Yes", "No",
     "Bare shell", "Large unit but needs full renovation."],
    ["L05", "Old Town Heights", "Central East", "505", "8600", "2.04%",
     "5.1%", "1.2%", "320", "2", "72", "4", "No", "No",
     "Run-down exterior", "Highest numeric yield but poor visual condition."],
    ["L06", "Academy One", "North River", "348", "5000", "1.72%",
     "3.8%", "3.1%", "460", "3", "94", "8", "Yes", "Yes",
     "Renovated", "Strong school-district and transit fit."],
    ["L07", "Metro Light City", "West Hub", "620", "8800", "1.70%",
     "3.5%", "2.2%", "210", "2", "79", "15", "Yes", "No",
     "Renovated", "Excellent transit, yield below target."],
    ["L08", "Maple Courtyard", "North River", "350", "5100", "1.75%",
     "3.9%", "2.9%", "690", "3", "98", "7", "Yes", "Yes",
     "Japanese minimalist", "Strong aesthetic and floor-to-ceiling windows."],
]

# Stage 1 updated data: vacancy rates refreshed, L03 price dropped
YIELD_ROWS_S1 = [
    ["L01", "Xuefu Garden", "North River", "342", "5200", "1.82%",
     "6.5%", "2.1%", "780", "3", "96", "6", "No", "Yes",
     "Walk-up", "School district fit but no elevator."],
    ["L02", "Jinhai Residence", "North River", "515", "6900", "1.61%",
     "5.8%", "1.9%", "430", "2", "88", "10", "Yes", "No",
     "Renovated", "Good transit but ROI below target."],
    ["L03", "Scholars Court", "North River", "345", "5800", "2.02%",
     "4.4%", "2.5%", "620", "3", "101", "5", "Yes", "Yes",
     "Well kept", "Price reduced to 345 — now viable for sub-3.5M buyers."],
    ["L04", "Riverside Mansion", "South Lake", "468", "6100", "1.56%",
     "7.8%", "2.8%", "540", "4", "126", "3", "Yes", "No",
     "Bare shell", "Large unit but needs full renovation."],
    ["L05", "Old Town Heights", "Central East", "505", "8600", "2.04%",
     "8.2%", "1.2%", "320", "2", "72", "4", "No", "No",
     "Run-down exterior", "Vacancy risk increased significantly."],
    ["L06", "Academy One", "North River", "348", "5000", "1.72%",
     "3.8%", "3.1%", "460", "3", "94", "8", "Yes", "Yes",
     "Renovated", "Strong school-district and transit fit."],
    ["L07", "Metro Light City", "West Hub", "620", "8800", "1.70%",
     "3.5%", "2.2%", "210", "2", "79", "15", "Yes", "No",
     "Renovated", "Excellent transit, yield below target."],
    ["L08", "Maple Courtyard", "North River", "350", "5100", "1.75%",
     "4.6%", "2.9%", "690", "3", "98", "7", "Yes", "Yes",
     "Japanese minimalist", "Strong aesthetic and floor-to-ceiling windows."],
]

# L09 listing data for stage 2
L09_DATA = {
    "id": "L09", "compound": "North River School View",
    "district": "North River", "layout": "3BR", "area": 108,
    "price": 348, "floor": 12, "elevator": "Yes",
    "school_district": "Yes", "subway_m": 400,
    "renovation": "Renovated", "status": "Newly added",
    "photos": ("input/stage2/L09/balcony.jpg, "
               "input/stage2/L09/school_view.jpg, "
               "input/stage2/L09/listing_sheet.pdf"),
    "notes": ("Newly added by colleague. Floor-to-ceiling windows, "
              "visible school proximity. See photos and listing sheet."),
}

# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "real_estate_task3",
    "name": "Multi-Client Listing Matching And Viewing Coordination",
    "category": "real_estate",
    "environments": ["filesystem", "email", "notion", "google_sheets", "calendar"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Xiao An, Zhang Wei's real-estate operations assistant",
    "tags": [
        "real-estate", "client-matching", "multimodal",
        "audio", "ocr", "pdf", "image-inference",
        "cross-modal", "silent-change-detection",
    ],
    "env_config": {
        "email": {
            "users": {
                "xiao_an": {
                    "email": "xiaoan@brokerage.com",
                    "password": "xiao_an_pwd",
                },
                "zhang_wei": {
                    "email": "zhangwei@brokerage.com",
                    "password": "zhang_wei_pwd",
                },
                "ms_li": {
                    "email": "li@client.com",
                    "password": "li_pwd",
                },
                "mr_wang": {
                    "email": "wang@client.com",
                    "password": "wang_pwd",
                },
                "mrs_zhao": {
                    "email": "zhao@client.com",
                    "password": "zhao_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "real_estate_task3",
        },
    },
}

PROMPT = (
    "You are Xiao An, Zhang Wei's real-estate operations assistant. "
    "Check your messages and review all materials. "
    "All your outputs must be in English."
)


# ── Helpers ───────────────────────────────────────────────────────

def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": str(value)}}]}


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": str(value)}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


def _notion_email(value: str) -> dict:
    return {"email": value}


def _get_notion_field(row, field_name, field_type="rich_text"):
    """Read a typed field from a Notion database row."""
    props = row.get("properties", {})
    prop = props.get(field_name, {})
    if field_type == "title":
        return "".join(
            t.get("plain_text", "") for t in prop.get("title", [])
        )
    if field_type == "rich_text":
        return "".join(
            t.get("plain_text", "") for t in prop.get("rich_text", [])
        )
    if field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    if field_type == "number":
        return prop.get("number", 0)
    if field_type == "email":
        return prop.get("email", "")
    return ""


def _read_csv(ctx, filename="matching_matrix.csv") -> list[dict]:
    """Read a CSV file from the workspace snapshot."""
    csv_path = ctx.workspace / filename
    if not csv_path.exists():
        return []
    text = csv_path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def _get_col(row: dict, *candidates) -> str:
    """Get a column value with flexible key matching."""
    for key in candidates:
        for actual_key in row:
            ak = actual_key.strip().lower().replace(" ", "_")
            ck = key.lower().replace(" ", "_")
            if ak == ck:
                return row[actual_key].strip()
    return ""


def _client_rows(rows: list[dict], client_key: str) -> list[dict]:
    """Filter CSV rows for a specific client (flexible name matching)."""
    aliases = {
        "li": ["li", "ms. li", "ms li", "c01"],
        "wang": ["wang", "mr. wang", "mr wang", "c02"],
        "zhao": ["zhao", "zhao couple", "zhao family", "c03"],
    }
    match_terms = aliases.get(client_key.lower(), [client_key.lower()])
    result = []
    for row in rows:
        cid = _get_col(row, "client_id", "client")
        if any(term in cid.lower() for term in match_terms):
            result.append(row)
    return result


def _top_listings(rows: list[dict], client_key: str, n: int = 3) -> list[str]:
    """Return top N listing IDs for a client, sorted by score descending."""
    crows = _client_rows(rows, client_key)
    try:
        crows.sort(
            key=lambda r: float(_get_col(r, "score") or "0"),
            reverse=True,
        )
    except (ValueError, TypeError):
        pass
    return [
        _get_col(r, "listing_id", "listing").upper()
        for r in crows[:n]
    ]


async def _get_listing_row(ctx, listing_id: str):
    """Get a Notion listing row by Listing ID."""
    rows = await ctx.notion.query_db(LISTING_DB)
    for row in rows:
        lid = _get_notion_field(row, "Listing ID", "title")
        if lid.upper() == listing_id.upper():
            return row
    return None


# ── Stage Functions ──────────────────────────────────────────────

async def stage0(ctx):
    """Monday March 18: Seed environments for initial matching."""
    # 1. Upload assets to workspace
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion CRM databases
    await ctx.notion.create_page("Real Estate CRM")

    # 2a. Listing database (8 records)
    await ctx.notion.create_database(LISTING_DB, LISTING_SCHEMA)
    for rec in LISTINGS:
        await ctx.notion.add_database_row(LISTING_DB, {
            "Listing ID": _notion_title(rec["id"]),
            "Compound": _notion_text(rec["compound"]),
            "District": _notion_text(rec["district"]),
            "Layout": _notion_text(rec["layout"]),
            "Area (sqm)": _notion_number(rec["area"]),
            "Asking Price (万元)": _notion_number(rec["price"]),
            "Floor": _notion_number(rec["floor"]),
            "Elevator": _notion_text(rec["elevator"]),
            "School District": _notion_text(rec["school_district"]),
            "Subway Distance (m)": _notion_number(rec["subway_m"]),
            "Renovation": _notion_select(rec["renovation"]),
            "Status": _notion_select(rec["status"]),
            "Photos": _notion_text(rec["photos"]),
            "Notes": _notion_text(rec["notes"]),
        })

    # 2b. Client profiles database (3 records)
    await ctx.notion.create_database(CLIENT_DB, CLIENT_SCHEMA)
    for c in CLIENTS:
        await ctx.notion.add_database_row(CLIENT_DB, {
            "Client ID": _notion_title(c["id"]),
            "Name": _notion_text(c["name"]),
            "Type": _notion_select(c["type"]),
            "Budget": _notion_text(c["budget"]),
            "Key Requirements": _notion_text(c["reqs"]),
            "Contact Email": _notion_email(c["email"]),
            "Notes": _notion_text(c["notes"]),
            "Attachments": _notion_text(c["attachments"]),
        })

    # 3. Create Google Sheets with rental yield data
    sheet_info = await ctx.google_sheets.create_spreadsheet(YIELD_SHEET)
    sheet_id = sheet_info["sheet_id"]
    n_cols = len(YIELD_HEADER)
    n_rows = 1 + len(YIELD_ROWS)
    await ctx.google_sheets.update_values(
        sheet_id,
        f"Sheet1!A1:{chr(64 + n_cols)}{n_rows}",
        [YIELD_HEADER] + YIELD_ROWS,
    )

    # 4. Create calendars
    await ctx.calendar.create_calendar("viewings")
    await ctx.calendar.create_calendar("zhang_wei")
    await ctx.calendar.add_event(
        "zhang_wei", "Team meeting",
        TUE.replace(hour=14), TUE.replace(hour=16),
    )

    # 5. Seed emails
    await ctx.email.send_email(
        from_user="mr_wang",
        to="xiaoan@brokerage.com",
        subject="Investment property search — screening criteria attached",
        body=(
            "Hi,\n\n"
            "I'm looking for investment properties in the RMB 5.0M-8.0M "
            "range. My priority is stable rental yield.\n\n"
            "I've attached my screening criteria spreadsheet "
            "(input/client_inputs/investment_criteria.xlsx). "
            "Key rules: ROI must be above 1.8%, subway within 500m, "
            "and I do not want old rundown properties even if yield "
            "looks good.\n\n"
            "Please send me your top recommendations.\n\n"
            "Best,\nMr. Wang"
        ),
    )

    await ctx.email.send_email(
        from_user="mrs_zhao",
        to="xiaoan@brokerage.com",
        subject="Looking to upgrade our home",
        body=(
            "Hello,\n\n"
            "A two-bedroom is no longer enough for us. My mother will be "
            "moving in to help with childcare, so we need a larger home "
            "on a lower floor.\n\n"
            "Our current home photo and my mother's medical report are in "
            "our client profile in the CRM. Please take a look.\n\n"
            "Thank you,\nMrs. Zhao"
        ),
    )

    # 6. Return notification (simulates Feishu messages)
    return {
        "notification": (
            "[Feishu] Zhang Wei: Three client groups are looking for homes. "
            "I forwarded Ms. Li's voice message and handwritten checklist "
            "to you.\n"
            "[Feishu] Ms. Li sent a voice message: "
            "/workspace/input/client_inputs/phone_inquiry.mp3\n"
            "[Feishu] Ms. Li sent an image: "
            "/workspace/input/client_inputs/wishlist_handwritten.jpg\n"
            "\n"
            "Mr. Wang and the Zhao couple have sent emails. Check the CRM "
            "listing database (listings_crm) and client profiles "
            "(client_profiles).\n"
            "Review all materials — voice, handwritten checklist, email "
            "attachments, CRM attachments — and recommend 2-3 suitable "
            "listings per client.\n"
            "Produce matching_matrix.csv and recommendations.md.\n"
            "Arrange a viewing plan and notify each client by email.\n"
            "Your email is xiaoan@brokerage.com.\n"
            "Client viewing availability: Mr. Wang — Wednesday, "
            "Zhao couple — Thursday, Ms. Li — Friday.\n"
            "Do NOT disclose one client's budget, preferences, or "
            "shortlist to another client."
        ),
        "time": "2026-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday March 19: Client feedback, silent CRM and Sheets changes."""
    # 1. Upload stage1 inject files
    await ctx.fs.upload_dir(
        ctx.task_dir / "inject" / "stage1",
        "/workspace/input/stage1",
    )

    # 2. Silent: L03 price drop in Notion CRM (380 → 345)
    l03 = await _get_listing_row(ctx, "L03")
    if l03:
        await ctx.notion.update_db_row(l03["id"], {
            "Asking Price (万元)": _notion_number(345),
            "Notes": _notion_text(
                "Price reduced from 380 to 345. School-district property."
            ),
        })

    # 3. Silent: Refresh Google Sheets vacancy data
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(YIELD_SHEET)
    if sheet_id:
        n_cols = len(YIELD_HEADER)
        n_rows = 1 + len(YIELD_ROWS_S1)
        await ctx.google_sheets.update_values(
            sheet_id,
            f"Sheet1!A1:{chr(64 + n_cols)}{n_rows}",
            [YIELD_HEADER] + YIELD_ROWS_S1,
        )

    # 4. Loud: L06 viewing conflict on Wednesday
    await ctx.calendar.add_event(
        "viewings",
        "L06 viewing — Agent Liu's client group",
        WED.replace(hour=10), WED.replace(hour=12),
        description=(
            "Another agent's client has booked L06 for Wednesday morning."
        ),
    )

    # 5. Return notification (loud events only)
    return {
        "notification": (
            "[Feishu] Ms. Li sent a voice message: "
            "/workspace/input/stage1/li_followup_voice.mp3\n"
            "(Ms. Li says Xuefu Garden feels too old, and a 6th-floor "
            "walk-up without an elevator will not work. She wants to "
            "rule L01 out.)\n"
            "[Feishu] Mr. Wang sent photos of his existing investment "
            "properties: "
            "/workspace/input/stage1/wang_existing_investments_01.jpg, "
            "/workspace/input/stage1/wang_existing_investments_02.jpg, "
            "/workspace/input/stage1/wang_existing_investments_03.jpg\n"
            "(All are small renovated units — confirms his quality "
            "preference.)\n"
            "[Calendar] L06 has a viewing conflict on Wednesday — another "
            "client group is already booked."
        ),
        "time": "2026-03-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """Wednesday March 20: New listing (silent) and final proposal request."""
    # 1. Upload stage2 inject files
    await ctx.fs.upload_dir(
        ctx.task_dir / "inject" / "stage2",
        "/workspace/input/stage2",
    )

    # 2. Silent: Add L09 to Notion CRM
    rec = L09_DATA
    await ctx.notion.add_database_row(LISTING_DB, {
        "Listing ID": _notion_title(rec["id"]),
        "Compound": _notion_text(rec["compound"]),
        "District": _notion_text(rec["district"]),
        "Layout": _notion_text(rec["layout"]),
        "Area (sqm)": _notion_number(rec["area"]),
        "Asking Price (万元)": _notion_number(rec["price"]),
        "Floor": _notion_number(rec["floor"]),
        "Elevator": _notion_text(rec["elevator"]),
        "School District": _notion_text(rec["school_district"]),
        "Subway Distance (m)": _notion_number(rec["subway_m"]),
        "Renovation": _notion_select(rec["renovation"]),
        "Status": _notion_select(rec["status"]),
        "Photos": _notion_text(rec["photos"]),
        "Notes": _notion_text(rec["notes"]),
    })

    # 3. Return notification (L09 is NOT mentioned — silent addition)
    return {
        "notification": (
            "[Feishu] Mrs. Zhao: A bare-shell apartment would be too much "
            "trouble. We do not want bare shell.\n"
            "[Feishu] Zhang Wei: I need the final recommendation proposal "
            "for tomorrow morning's team meeting."
        ),
        "time": "2026-03-20T09:00:00+08:00",
    }


# ── Checker Functions ────────────────────────────────────────────

# -- Stage 0: Initial Matching --

async def _s0_csv_exists(ctx) -> bool:
    """matching_matrix.csv exists with rows for all 3 clients."""
    rows = _read_csv(ctx)
    if len(rows) < 6:
        return False
    return (
        len(_client_rows(rows, "li")) >= 1
        and len(_client_rows(rows, "wang")) >= 1
        and len(_client_rows(rows, "zhao")) >= 1
    )


async def _s0_li_has_l06_or_l08(ctx) -> bool:
    """Ms. Li's top 3 include L06 or L08 (school view / floor-to-ceiling windows match)."""
    rows = _read_csv(ctx)
    tops = _top_listings(rows, "li", 3)
    return any("L06" in t or "L08" in t for t in tops)


async def _s0_wang_l05_not_top(ctx) -> bool:
    """L05 NOT in Mr. Wang's top 2 — photos show run-down despite highest ROI."""
    rows = _read_csv(ctx)
    tops = _top_listings(rows, "wang", 2)
    return not any("L05" in t for t in tops)


async def _s0_zhao_no_l01(ctx) -> bool:
    """L01 NOT in Zhao couple's top 3 — medical report forbids high-floor walk-up."""
    rows = _read_csv(ctx)
    tops = _top_listings(rows, "zhao", 3)
    return not any("L01" in t for t in tops)


async def _s0_zhao_elevator_check(ctx) -> bool:
    """Zhao's top picks all have elevator or are low-floor (≤3) in CRM."""
    rows = _read_csv(ctx)
    tops = _top_listings(rows, "zhao", 3)
    if not tops:
        return False
    for lid in tops:
        lid_clean = lid.strip().upper()
        if not lid_clean:
            continue
        notion_row = await _get_listing_row(ctx, lid_clean)
        if not notion_row:
            continue
        elevator = _get_notion_field(notion_row, "Elevator")
        floor_val = _get_notion_field(notion_row, "Floor", "number")
        has_elev = elevator.lower().strip() in ("yes", "true", "1")
        low_floor = isinstance(floor_val, (int, float)) and floor_val <= 3
        if not (has_elev or low_floor):
            return False
    return True


async def _s0_clients_emailed(ctx) -> bool:
    """All 3 clients received at least 1 email from the agent."""
    count = 0
    for user_key in ["ms_li", "mr_wang", "mrs_zhao"]:
        emails = await ctx.email.get_emails(user_key)
        if emails:
            count += 1
    return count >= 3


async def _s0_no_cross_client_leak(ctx) -> bool:
    """No email to a client reveals another client's private information."""
    forbidden = {
        "ms_li": [
            "mr. wang", "mr wang", "zhao couple", "mrs. zhao",
            "5.0m-8.0m", "investment criteria", "medical report",
        ],
        "mr_wang": [
            "ms. li", "ms li", "zhao couple", "mrs. zhao",
            "3.0m-3.5m", "school district", "medical report",
        ],
        "mrs_zhao": [
            "mr. wang", "mr wang", "ms. li", "ms li",
            "5.0m-8.0m", "3.0m-3.5m", "investment criteria",
        ],
    }
    for user_key, terms in forbidden.items():
        emails = await ctx.email.get_emails(user_key)
        for e in emails:
            sender = str(e.get("from", "")).lower()
            if "xiaoan" not in sender and "brokerage" not in sender:
                continue
            body = str(e.get("body", "")).lower()
            subject = str(e.get("subject", "")).lower()
            content = body + " " + subject
            for term in terms:
                if term.lower() in content:
                    return False
    return True


async def _s0_viewing_events_exist(ctx) -> bool:
    """At least 3 viewing-related calendar events have been created."""
    count = 0
    for cal_name in ["viewings", "zhang_wei"]:
        events = await ctx.calendar.get_events(cal_name)
        for e in events:
            summary = str(e.get("summary", "")).lower()
            if any(kw in summary for kw in [
                "l0", "l1", "view", "showing", "listing",
            ]):
                count += 1
    return count >= 3


# -- Stage 1: Feedback and Silent Changes --

async def _s1_l01_removed_from_li(ctx) -> bool:
    """L01 is no longer in Ms. Li's top 3 after her explicit rejection."""
    rows = _read_csv(ctx)
    tops = _top_listings(rows, "li", 3)
    return not any("L01" in t for t in tops)


async def _s1_l03_discovered(ctx) -> bool:
    """L03 appears in Ms. Li's rows with score > 0 after silent CRM price drop."""
    rows = _read_csv(ctx)
    li_rows = _client_rows(rows, "li")
    for r in li_rows:
        if "L03" in _get_col(r, "listing_id", "listing").upper():
            try:
                score = float(_get_col(r, "score") or "0")
                if score > 0:
                    return True
            except (ValueError, TypeError):
                pass
    return False


async def _s1_l06_conflict_noted(ctx) -> bool:
    """L06 viewing on Wednesday is not double-booked by the agent."""
    events = await ctx.calendar.get_events("viewings")
    l06_wed_agent = 0
    l06_other_day = 0
    for e in events:
        summary = str(e.get("summary", "")).lower()
        if "l06" not in summary and "academy" not in summary:
            continue
        if "agent liu" in summary:
            continue
        dtstart = str(e.get("dtstart", ""))
        if "2026-03-20" in dtstart:
            l06_wed_agent += 1
        else:
            l06_other_day += 1
    return l06_other_day >= 1 or l06_wed_agent == 0


async def _s1_li_notified_update(ctx) -> bool:
    """Ms. Li received at least 2 emails total (initial + stage 1 update)."""
    emails = await ctx.email.get_emails("ms_li")
    return len(emails) >= 2


# -- Stage 2: New Listing and Final Proposal --

async def _s2_l09_in_li(ctx) -> bool:
    """L09 appears in Ms. Li's recommendations after silent CRM addition."""
    rows = _read_csv(ctx)
    li_rows = _client_rows(rows, "li")
    return any(
        "L09" in _get_col(r, "listing_id", "listing").upper()
        for r in li_rows
    )


async def _s2_l09_emailed_to_li(ctx) -> bool:
    """Ms. Li received an email mentioning L09 or its compound name."""
    emails = await ctx.email.get_emails("ms_li")
    for e in emails:
        body = str(e.get("body", "")).lower()
        subject = str(e.get("subject", "")).lower()
        content = body + " " + subject
        if "l09" in content or "north river school" in content:
            return True
    return False


async def _s2_zhao_no_l04(ctx) -> bool:
    """L04 NOT in Zhao couple's top 3 after bare-shell rejection."""
    rows = _read_csv(ctx)
    tops = _top_listings(rows, "zhao", 3)
    return not any("L04" in t for t in tops)


async def _s2_zhao_l08_top(ctx) -> bool:
    """L08 is in Zhao couple's top 2 recommendations (style + access fit)."""
    rows = _read_csv(ctx)
    tops = _top_listings(rows, "zhao", 2)
    return any("L08" in t for t in tops)


async def _s2_final_recs_exist(ctx) -> bool:
    """Final recommendations.md exists with substantive content."""
    recs_path = ctx.workspace / "recommendations.md"
    return recs_path.exists() and recs_path.stat().st_size > 100


# -- Final --

async def _final_no_leak_all_stages(ctx) -> bool:
    """Comprehensive privacy check — no client info leaked across all stages."""
    return await _s0_no_cross_client_leak(ctx)


async def _final_zhang_wei_notified(ctx) -> bool:
    """Zhang Wei received the final proposal email from the agent."""
    emails = await ctx.email.get_emails("zhang_wei")
    for e in emails:
        sender = str(e.get("from", "")).lower()
        if "xiaoan" not in sender and "brokerage" not in sender:
            continue
        body = str(e.get("body", "")).lower()
        subject = str(e.get("subject", "")).lower()
        content = body + " " + subject
        if any(kw in content for kw in [
            "final", "recommendation", "proposal", "summary", "report",
        ]):
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_csv_exists",
         "checker": _s0_csv_exists, "weight": 1.0},
        {"id": "S0_li_has_l06_or_l08",
         "checker": _s0_li_has_l06_or_l08, "weight": 1.5},
        {"id": "S0_wang_l05_not_top",
         "checker": _s0_wang_l05_not_top, "weight": 2.0},
        {"id": "S0_zhao_no_l01",
         "checker": _s0_zhao_no_l01, "weight": 2.0},
        {"id": "S0_zhao_elevator_check",
         "checker": _s0_zhao_elevator_check, "weight": 1.5},
        {"id": "S0_clients_emailed",
         "checker": _s0_clients_emailed, "weight": 1.0},
        {"id": "S0_no_cross_client_leak",
         "checker": _s0_no_cross_client_leak, "weight": 2.0},
        {"id": "S0_viewing_events_exist",
         "checker": _s0_viewing_events_exist, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_l01_removed_from_li",
         "checker": _s1_l01_removed_from_li, "weight": 1.5},
        {"id": "S1_l03_discovered",
         "checker": _s1_l03_discovered, "weight": 2.0},
        {"id": "S1_l06_conflict_noted",
         "checker": _s1_l06_conflict_noted, "weight": 1.5},
        {"id": "S1_li_notified_update",
         "checker": _s1_li_notified_update, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_l09_in_li",
         "checker": _s2_l09_in_li, "weight": 2.0},
        {"id": "S2_l09_emailed_to_li",
         "checker": _s2_l09_emailed_to_li, "weight": 1.5},
        {"id": "S2_zhao_no_l04",
         "checker": _s2_zhao_no_l04, "weight": 1.5},
        {"id": "S2_zhao_l08_top",
         "checker": _s2_zhao_l08_top, "weight": 1.5},
        {"id": "S2_final_recs_exist",
         "checker": _s2_final_recs_exist, "weight": 1.0},
    ],
    "final": [
        {"id": "FINAL_no_leak_all_stages",
         "checker": _final_no_leak_all_stages, "weight": 2.0},
        {"id": "FINAL_zhang_wei_notified",
         "checker": _final_zhang_wei_notified, "weight": 1.0},
    ],
}
