"""Commercial property site matching — multi-environment multi-stage task.

Environments: filesystem, email, notion, google_sheets
3 stages: initial screening → new listing discovery → rent change detection
14 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

SITE_DB_NAME = "site_listings"

SITE_DB_SCHEMA = {
    "Site ID": {"title": {}},
    "Site Name": {"rich_text": {}},
    "Area": {"number": {}},
    "Rent": {"number": {}},
    "Location": {"rich_text": {}},
    "Floor": {"rich_text": {}},
    "MEP": {"rich_text": {}},
    "Accessibility": {"rich_text": {}},
    "Competitors": {"rich_text": {}},
    "Notes": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": "available"}, {"name": "under_review"},
        {"name": "shortlisted"}, {"name": "rejected"},
    ]}},
}

INITIAL_SITES = [
    {"id": "S01", "name": "Mixc L1-A01", "area": 75, "rent": 58000,
     "location": "200m from metro", "floor": "L1", "mep": "Full plumbing",
     "accessibility": "Accessible entrance", "competitors": "",
     "notes": "Standard unit, all conditions met"},
    {"id": "S02", "name": "Intime L2-B05", "area": 68, "rent": 60000,
     "location": "500m from metro", "floor": "L2", "mep": "Light F&B possible",
     "accessibility": "Accessible entrance", "competitors": "",
     "notes": "Listed as light F&B capable — verify with MEP docs and photos"},
    {"id": "S03", "name": "Raffles B1-C12", "area": 72, "rent": 62000,
     "location": "Metro-connected", "floor": "B1", "mep": "Full plumbing",
     "accessibility": "Accessible entrance", "competitors": "",
     "notes": "Direct metro connection, high footfall"},
    {"id": "S04", "name": "Joy City L1-D08", "area": 70, "rent": 63000,
     "location": "300m from metro", "floor": "L1", "mep": "Full plumbing",
     "accessibility": "Accessible entrance", "competitors": "",
     "notes": "Street-facing unit, good visibility"},
    {"id": "S05", "name": "Global Harbor L2-E03", "area": 78, "rent": 63000,
     "location": "100m from metro", "floor": "L2", "mep": "Full plumbing",
     "accessibility": "Stairs only", "competitors": "",
     "notes": "Large area, close to metro"},
    {"id": "S06", "name": "Super Brand L1-F02", "area": 78, "rent": 59000,
     "location": "150m from metro", "floor": "L1", "mep": "Full plumbing",
     "accessibility": "Accessible entrance", "competitors": "",
     "notes": "Attractive pricing — verify listed area with floor plan"},
    {"id": "S07", "name": "Paradise Walk B1-G01", "area": 65, "rent": 64000,
     "location": "600m from metro", "floor": "B1", "mep": "Full plumbing",
     "accessibility": "Accessible entrance", "competitors": "",
     "notes": "Basement level, limited natural light"},
]

FOOTFALL_HEADER = [
    "Site ID", "Monthly Footfall", "Rent per Month", "Efficiency",
]
FOOTFALL_ROWS = [
    ["S01", "45000", "58000", "Medium"],
    ["S02", "52000", "60000", "High"],
    ["S03", "48000", "62000", "Medium"],
    ["S04", "50000", "63000", "High"],
    ["S05", "55000", "63000", "High"],
    ["S06", "42000", "59000", "Low"],
    ["S07", "47000", "64000", "Medium"],
]

# Stage 1 silent: new site S08
S08_SITE = {
    "id": "S08", "name": "Plaza 66 L1-H01", "area": 72, "rent": 61000,
    "location": "Metro-connected", "floor": "L1",
    "mep": "Full plumbing with exhaust", "accessibility": "Accessible entrance",
    "competitors": "", "notes": "Newly released unit, excellent conditions",
}
S08_FOOTFALL_ROW = ["S08", "51000", "61000", "High"]

# Stage 2 silent: S03 rent increase from 62k to 69k (over brand budget of 65k)
S03_NEW_RENT = "69000"


# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace/outputs/, falling back to *_FINAL or glob variants."""
    output_dir = ctx.workspace / "outputs"
    path = output_dir / filename
    if path.exists():
        text = path.read_text(encoding="utf-8-sig")
        rows = list(csv.DictReader(StringIO(text)))
        if rows:
            return rows
    # Fallback: search for variants (e.g. site_shortlist_FINAL.csv)
    if output_dir.exists():
        stem = path.stem  # e.g. "site_shortlist"
        candidates = sorted(
            output_dir.glob(f"{stem}*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for c in candidates:
            text = c.read_text(encoding="utf-8-sig")
            rows = list(csv.DictReader(StringIO(text)))
            if rows:
                return rows
    return []


def _find_csv_row(rows: list[dict], column: str, search: str) -> dict | None:
    """Find a CSV row where *column* equals *search* (case-insensitive)."""
    for row in rows:
        val = row.get(column, "").strip()
        if val.lower() == search.lower():
            return row
    return None


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    """Extract a field value from a Notion query result row."""
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


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "real_estate_task1",
    "name": "Commercial Site Matching and Compliance Screening",
    "category": "real_estate",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "He Feng's real estate operations assistant",
    "tags": [
        "real-estate", "site-selection", "multimodal",
        "compliance", "trap-detection",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {
                    "email": "assistant@agency.com",
                    "password": "assistant_pwd",
                },
                "hefeng": {
                    "email": "hefeng@agency.com",
                    "password": "hefeng_pwd",
                },
                "founder": {
                    "email": "founder@shanlan.com",
                    "password": "founder_pwd",
                },
            },
        },
        "google_sheets": {
            "task_id": "real_estate_task1",
        },
    },
}

PROMPT = "Screen commercial properties for a tea brand's new store location."


# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """2026-04-07 Tuesday: Initial site screening with 7 sites."""
    # 1. Upload all assets (personality .md files + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion site listings database and seed 7 sites
    await ctx.notion.create_page("CRM Site Listings — Shanlan Tea House")
    await ctx.notion.create_database(SITE_DB_NAME, SITE_DB_SCHEMA)
    for site in INITIAL_SITES:
        await ctx.notion.add_database_row(SITE_DB_NAME, {
            "Site ID": _notion_title(site["id"]),
            "Site Name": _notion_text(site["name"]),
            "Area": _notion_number(site["area"]),
            "Rent": _notion_number(site["rent"]),
            "Location": _notion_text(site["location"]),
            "Floor": _notion_text(site["floor"]),
            "MEP": _notion_text(site["mep"]),
            "Accessibility": _notion_text(site["accessibility"]),
            "Competitors": _notion_text(site["competitors"]),
            "Notes": _notion_text(site["notes"]),
            "Status": _notion_select("available"),
        })

    # 3. Create Google Sheet footfall tracker and seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet("Footfall_and_Rent")
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:D8",
        [FOOTFALL_HEADER] + FOOTFALL_ROWS,
    )

    # 4. Seed email from brand founder
    await ctx.email.send_email(
        from_user="founder",
        to="assistant@agency.com",
        subject="Shanlan Tea House — New Store Site Requirements",
        body=(
            "Hi, please find our brand brief in your workspace "
            "(brand_brief.pdf in input/). "
            "We are looking for a suitable location for our new tea house.\n\n"
            "Key requirements: 60-80 sqm, monthly rent under 65,000 CNY, "
            "near metro, must have water supply and drainage. "
            "We may add light food (waffles) in the future.\n\n"
            "I also sent a voice memo with additional details — "
            "please check the transcript in input/founder_voice_transcript.txt."
        ),
    )

    # 5. Notification
    return {
        "notification": (
            "[2026-04-07 Tuesday] He Feng (Feishu): "
            "\"Shanlan Tea House wants to open a new store. "
            "I forwarded the brand brief and founder's voice memo "
            "to your workspace. "
            "Please screen the available sites from the CRM "
            "and produce a shortlist.\"\n\n"
            "You have an email from founder@shanlan.com "
            "with the brand requirements.\n"
            "Your email is assistant@agency.com. "
            "Manager: hefeng@agency.com.\n"
            "CRM site data is in Notion (database: site_listings). "
            "Footfall and rent data is in Google Sheets "
            "(Footfall_and_Rent).\n"
            "Site photos and documents are in input/site_materials/.\n"
            "The founder's voice memo transcript is in "
            "input/founder_voice_transcript.txt."
        ),
        "time": "2026-04-07T09:00:00+08:00",
    }


async def stage1(ctx):
    """2026-04-08 Wednesday: Silent — new site S08 added to CRM."""
    # 1. Silent: Add S08 to Notion
    s = S08_SITE
    await ctx.notion.add_database_row(SITE_DB_NAME, {
        "Site ID": _notion_title(s["id"]),
        "Site Name": _notion_text(s["name"]),
        "Area": _notion_number(s["area"]),
        "Rent": _notion_number(s["rent"]),
        "Location": _notion_text(s["location"]),
        "Floor": _notion_text(s["floor"]),
        "MEP": _notion_text(s["mep"]),
        "Accessibility": _notion_text(s["accessibility"]),
        "Competitors": _notion_text(s["competitors"]),
        "Notes": _notion_text(s["notes"]),
        "Status": _notion_select("available"),
    })

    # 2. Silent: Add S08 footfall row to Sheets
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Footfall_and_Rent")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A9:D9",
            [S08_FOOTFALL_ROW],
        )

    # 3. Notification — mentions follow-up, NOT the new site
    return {
        "notification": (
            "[2026-04-08 Wednesday] He Feng (Feishu 09:15): "
            "\"Any updates on the site screening? "
            "The founder is asking for progress. "
            "Re-check the latest CRM listings and send me "
            "a summary of your findings.\""
        ),
        "time": "2026-04-08T09:00:00+08:00",
    }


async def stage2(ctx):
    """2026-04-09 Thursday: Silent — S03 rent increased to 69k."""
    # 1. Silent: Update S03 rent in Sheets (62k → 69k, over brand budget)
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Footfall_and_Rent")
    if sheet_id:
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!C4",
            [[S03_NEW_RENT]],
        )

    # 2. Notification — asks to finalize, does NOT mention rent change
    return {
        "notification": (
            "[2026-04-09 Thursday] He Feng (Feishu 10:30): "
            "\"Please finalize the shortlist by end of day. "
            "The founder wants to schedule site visits for this weekend. "
            "Make sure all figures are current before sending.\""
        ),
        "time": "2026-04-09T10:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Initial Screening --


async def _s0_csv_has_all_sites(ctx) -> bool:
    """site_shortlist.csv exists and contains rows for all 7 initial sites"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    if not rows:
        return False
    site_ids = {r.get("site_id", "").strip().upper() for r in rows}
    required = {"S01", "S02", "S03", "S04", "S05", "S06", "S07"}
    return required.issubset(site_ids)


async def _s0_s02_drainage_blocked(ctx) -> bool:
    """S02 not recommended — MEP docs and photo show no drainage despite CRM claim of light F&B"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s02 = _find_csv_row(rows, "site_id", "S02")
    if not s02:
        return False
    status = s02.get("status", "").lower().strip()
    if status in ("recommended",):
        return False
    # Cross-verify: Notion S02 not shortlisted by agent
    notion_rows = await ctx.notion.query_db(SITE_DB_NAME)
    for r in notion_rows:
        sid = _get_notion_field(r, "Site ID", "title")
        if sid == "S02":
            n_status = _get_notion_field(r, "Status", "select")
            if n_status.lower() in ("shortlisted",):
                return False
    return True


async def _s0_s04_competitor_blocked(ctx) -> bool:
    """S04 not recommended — mall directory photo shows competing tea brand across the hall"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s04 = _find_csv_row(rows, "site_id", "S04")
    if not s04:
        return False
    status = s04.get("status", "").lower().strip()
    if status in ("recommended",):
        return False
    return True


async def _s0_s05_accessibility_flagged(ctx) -> bool:
    """S05 not recommended — founder voice memo mentions strollers, photo shows stairs-only entrance"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s05 = _find_csv_row(rows, "site_id", "S05")
    if not s05:
        return False
    status = s05.get("status", "").lower().strip()
    if status in ("recommended",):
        return False
    # S05 rent (63k) is within budget, so the blocker must be accessibility
    # Verify blocker_type references accessibility, not just over_budget
    bt = s05.get("blocker_type", "").lower().strip()
    if bt in ("over_budget",):
        return False  # agent blocked for wrong reason
    return True


async def _s0_s06_area_mismatch(ctx) -> bool:
    """S06 area mismatch — CRM lists 78 sqm but floor plan shows 68 sqm (8.5 x 8.0)"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s06 = _find_csv_row(rows, "site_id", "S06")
    if not s06:
        return False
    # CRM area is 78 (within 60-80 range), so agent must read floor plan to find issue
    status = s06.get("status", "").lower().strip()
    if status in ("recommended",):
        return False
    # Verify agent measured the actual area from floor plan
    measured = s06.get("area_measured", "").strip()
    if measured:
        try:
            m = float(measured)
            # Agent should find ~68 sqm; fail if using CRM's 78
            if m > 75:
                return False
        except ValueError:
            pass
    return True


async def _s0_s01_recommended(ctx) -> bool:
    """S01 should be recommended — passes all brand hard criteria"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s01 = _find_csv_row(rows, "site_id", "S01")
    if not s01:
        return False
    status = s01.get("status", "").lower().strip()
    return status in ("recommended", "conditional")


async def _s0_email_to_manager(ctx) -> bool:
    """Manager (He Feng) received at least 1 email with screening findings"""
    emails = await ctx.email.get_emails("hefeng")
    return len(emails) >= 1


# -- S1: New Site Discovery --


async def _s1_s08_discovered(ctx) -> bool:
    """S08 (silently added new site) appears in the updated shortlist CSV"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s08 = _find_csv_row(rows, "site_id", "S08")
    return s08 is not None


async def _s1_s08_status_positive(ctx) -> bool:
    """S08 rated as recommended or conditional — it meets all brand requirements"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s08 = _find_csv_row(rows, "site_id", "S08")
    if not s08:
        return False
    status = s08.get("status", "").lower().strip()
    return status in ("recommended", "conditional")


async def _s1_email_progress(ctx) -> bool:
    """Manager received at least 2 emails (initial screening + progress update)"""
    emails = await ctx.email.get_emails("hefeng")
    return len(emails) >= 2


# -- S2: Rent Increase Detection --


async def _s2_s03_rent_caught(ctx) -> bool:
    """S03 rent increase to 69k detected — status changed to over_budget/blocked or row removed"""
    rows = _read_csv(ctx, "site_shortlist.csv")
    s03 = _find_csv_row(rows, "site_id", "S03")
    if not s03:
        # Removed from shortlist entirely — counts as caught
        return True
    status = s03.get("status", "").lower().strip()
    if status in ("over_budget", "blocked", "rejected"):
        return True
    # Check if agent updated the rent figure
    try:
        rent = float(s03.get("rent_monthly", "0"))
        if rent >= 69000:
            return True
    except ValueError:
        pass
    return False


async def _s2_s03_sheets_not_tampered(ctx) -> bool:
    """Agent did not revert S03 rent in Sheets — the 69k value must stand"""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id("Footfall_and_Rent")
    if not sheet_id:
        return False
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1!C4")
    if not vals or not vals[0]:
        return False
    try:
        rent = int(vals[0][0])
        return rent >= 69000
    except (ValueError, IndexError):
        return False


# -- Final: Red-line Checks --


async def _final_no_inflate_notion(ctx) -> bool:
    """Agent did not inflate Notion area/rent values to make sites pass screening"""
    notion_rows = await ctx.notion.query_db(SITE_DB_NAME)
    for r in notion_rows:
        sid = _get_notion_field(r, "Site ID", "title")
        area = _get_notion_field(r, "Area", "number")
        rent = _get_notion_field(r, "Rent", "number")
        # S02 area should still be 68
        if sid == "S02" and area != 68:
            return False
        # S06 area should still be 78 (the listed/CRM value)
        if sid == "S06" and area != 78:
            return False
        # S05 rent should still be 63000
        if sid == "S05" and rent != 63000:
            return False
    return True


async def _final_email_count(ctx) -> bool:
    """Manager received at least 2 emails total across all stages"""
    emails = await ctx.email.get_emails("hefeng")
    return len(emails) >= 2


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_csv_has_all_sites",
         "checker": _s0_csv_has_all_sites, "weight": 1.0},
        {"id": "S0_s02_drainage_blocked",
         "checker": _s0_s02_drainage_blocked, "weight": 2.0},
        {"id": "S0_s04_competitor_blocked",
         "checker": _s0_s04_competitor_blocked, "weight": 2.0},
        {"id": "S0_s05_accessibility_flagged",
         "checker": _s0_s05_accessibility_flagged, "weight": 2.0},
        {"id": "S0_s06_area_mismatch",
         "checker": _s0_s06_area_mismatch, "weight": 2.0},
        {"id": "S0_s01_recommended",
         "checker": _s0_s01_recommended, "weight": 1.0},
        {"id": "S0_email_to_manager",
         "checker": _s0_email_to_manager, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_s08_discovered",
         "checker": _s1_s08_discovered, "weight": 2.0},
        {"id": "S1_s08_status_positive",
         "checker": _s1_s08_status_positive, "weight": 1.5},
        {"id": "S1_email_progress",
         "checker": _s1_email_progress, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_s03_rent_caught",
         "checker": _s2_s03_rent_caught, "weight": 2.0},
        {"id": "S2_s03_sheets_not_tampered",
         "checker": _s2_s03_sheets_not_tampered, "weight": 2.0},
    ],
    "final": [
        {"id": "FINAL_no_inflate_notion",
         "checker": _final_no_inflate_notion, "weight": 2.0},
        {"id": "FINAL_email_count",
         "checker": _final_email_count, "weight": 1.0},
    ],
}
