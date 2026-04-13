"""Year-end top 10 public-livelihood stories feature planning — multi-stage task.

Environments: filesystem, email, google_sheets
3 stages: first shortlist → editor follow-up + score correction → final photo-source review
12 core checkers (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

PHOTO_REGISTRY_SHEET_NAME = "photo_registry"

PHOTO_REGISTRY_HEADER = [
    "photo_file", "event_id", "source_url",
    "shoot_location", "license_status", "verified_note",
]

PHOTO_REGISTRY_SEED_ROWS = [
    [
        "metro_opening_crowd.jpg", "E05",
        "https://commons.wikimedia.org/wiki/File:B2_Platform_of_Tangzhuang_Sta._of_Suzhou_Rail_Transit_20250216.jpg",
        "待复核", "cleared",
        "图编初稿沿用图库旧标签，尚未复核城市信息",
    ],
]

# Stage 2 silent update: metro_opening_crowd.jpg becomes do_not_use,
# metro_platform_launch.jpg added as cleared replacement
PHOTO_REGISTRY_S2_UPDATE = [
    [
        "metro_opening_crowd.jpg", "E05",
        "https://commons.wikimedia.org/wiki/File:B2_Platform_of_Tangzhuang_Sta._of_Suzhou_Rail_Transit_20250216.jpg",
        "苏州", "do_not_use",
        "素材部于2025-12-31 18:10更正：该图为苏州试运营现场，不可用于本市地铁新线专题",
    ],
    [
        "metro_platform_launch.jpg", "E05",
        "https://commons.wikimedia.org/wiki/File:Platform_of_L10_(W),_Yuelai_Station,_Chongqing_Rail_Transit_20250425.jpg",
        "图库备选图（站台内景，城市信息已脱敏）", "cleared",
        "素材部补充的授权图库图，可用于终版专题配图",
    ],
]


# ── Helpers ───────────────────────────────────────────────────────


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace root or workspace/outputs/."""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / filename if subdir else ctx.workspace / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _find_csv_row(rows: list[dict], column: str, search: str) -> dict | None:
    """Find a CSV row where column matches search string (case-insensitive)."""
    for row in rows:
        val = row.get(column, "")
        if search.lower() == val.strip().lower():
            return row
    return None


async def _get_all_sheet_rows(ctx) -> list[dict]:
    """Read all rows from photo_registry sheet."""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(PHOTO_REGISTRY_SHEET_NAME)
    if not sheet_id:
        return []
    vals = await ctx.google_sheets.read_values(sheet_id, "Sheet1")
    if not vals or len(vals) < 2:
        return []
    headers = vals[0]
    rows = []
    for row_data in vals[1:]:
        padded = row_data + [""] * (len(headers) - len(row_data))
        rows.append(dict(zip(headers, padded)))
    return rows


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "journalist_task8",
    "name": "Year-End Top 10 Public-Livelihood Stories Feature Planning",
    "category": "journalist",
    "environments": ["filesystem", "email", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Liu Ying's feature-planning assistant",
    "tags": [
        "year-end-feature", "ranking", "photo-verification",
        "vote-anomaly", "archive-cross-check", "multimodal",
    ],
    "env_config": {
        "email": {
            "users": {
                "liu_ying": {"email": "liu.ying@newsroom.com", "password": "liu_ying_pwd"},
                "data_desk": {"email": "data@newsroom.com", "password": "data_desk_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "journalist_task8",
        },
    },
}

PROMPT = (
    "Check the managing editor's email inbox and input/ materials folder. "
    "All your outputs must be in English."
)


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """2025-12-29: First shortlist — candidate ranking + archive cross-check + photo review."""
    # 1. Upload assets (personality .md files + initial input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Google Sheet photo_registry with seed data
    sheet_info = await ctx.google_sheets.create_spreadsheet(PHOTO_REGISTRY_SHEET_NAME)
    sheet_id = sheet_info["sheet_id"]
    await ctx.google_sheets.update_values(
        sheet_id, "Sheet1!A1:F2",
        [PHOTO_REGISTRY_HEADER] + PHOTO_REGISTRY_SEED_ROWS,
    )

    # 3. Seed email: Data Desk → Liu Ying
    await ctx.email.send_email(
        from_user="data_desk",
        to="liu.ying@newsroom.com",
        subject="Vote table and traffic table uploaded",
        body="The vote table and traffic table are both in the materials folder.",
    )

    # 4. Notification — Liu Ying's direct instruction
    return {
        "notification": (
            "[2025-12-29] "
            "The candidate ranking is in candidates.csv. Start with the top 10 by heat score, "
            "but make sure you check the archives and the photos. "
            "Remove anything problematic and fill the gap with the next item. "
            "Give me one round tonight. "
            "Also, check email — the data desk sent a message.\n\n"
            "You use the managing editor's mailbox liu.ying@newsroom.com to read and send emails. "
            "Contacts: data@newsroom.com (Data Desk).\n"
            "Photo registry is in Google Sheets (photo_registry)."
        ),
        "time": "2025-12-29T18:00:00+08:00",
    }


async def stage1(ctx):
    """2025-12-30: Editor follow-up — vote anomaly check + score correction."""
    # 1. Silent: Upload score_correction.csv (agent NOT notified)
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage1" / "score_correction.csv",
        "/workspace/input/",
    )

    # 2. Notification — Liu Ying's direct instruction (only mentions loud events)
    return {
        "notification": (
            "[2025-12-30] "
            "That community elder-care pilot vote looks off to me. Check it. "
            "Also, the data team said last night that the air-quality item needs recalculation. "
            "Don't just trust the old ranking."
        ),
        "time": "2025-12-30T10:00:00+08:00",
    }


async def stage2(ctx):
    """2025-12-31: Final photo-source review — metro image swap."""
    # 1. Loud: Upload alternate metro image
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "stage2" / "metro_platform_launch.jpg",
        "/workspace/input/",
    )

    # 2. Silent: Update photo_registry sheet — mark metro_opening_crowd.jpg as do_not_use,
    #    add metro_platform_launch.jpg as cleared replacement
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(PHOTO_REGISTRY_SHEET_NAME)
    if sheet_id:
        # Overwrite row 2 (metro_opening_crowd.jpg) and add row 3 (metro_platform_launch.jpg)
        await ctx.google_sheets.update_values(
            sheet_id, "Sheet1!A2:F3",
            PHOTO_REGISTRY_S2_UPDATE,
        )

    # 3. Notification — Liu Ying's direct instruction (mentions image concern + alternate file)
    return {
        "notification": (
            "[2025-12-31] "
            "We lock the final version at 20:00 tonight. "
            "That new-metro-line photo still feels like another city to me, "
            "so recheck the photo source before final. "
            "The visual team put an alternate image in the materials folder."
        ),
        "time": "2025-12-31T17:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: First Shortlist --

async def _s0_selection_count(ctx) -> bool:
    """Agent produced a 10-row first shortlist"""
    rows = _read_csv(ctx, "top10_selection.csv")
    return len(rows) == 10


async def _s0_e07_excluded(ctx) -> bool:
    """Agent excluded E07 (corrected/withdrawn per 2025-09 archive) — reverse check"""
    rows = _read_csv(ctx, "top10_selection.csv")
    if len(rows) < 1:
        return False  # must have rows to verify against
    event_ids = {r.get("event_id", "").strip() for r in rows}
    return "E07" not in event_ids


async def _s0_e11_promoted(ctx) -> bool:
    """Agent promoted E11 into the top 10 to backfill after E07 removal"""
    rows = _read_csv(ctx, "top10_selection.csv")
    if len(rows) < 1:
        return False
    event_ids = {r.get("event_id", "").strip() for r in rows}
    return "E11" in event_ids


async def _s0_e01_photo_ok(ctx) -> bool:
    """Agent assigned flood_a.jpg (not flood_b.jpg which is a sinkhole) to E01"""
    rows = _read_csv(ctx, "top10_selection.csv")
    row = _find_csv_row(rows, "event_id", "E01")
    if not row:
        return False
    photo = row.get("recommended_photo", "").strip().lower()
    return photo == "flood_a.jpg"


# -- S1: Editor Follow-up + Score Correction --

async def _s1_e12_excluded(ctx) -> bool:
    """Agent excluded E12 for vote-stuffing anomaly — reverse check"""
    rows = _read_csv(ctx, "top10_selection.csv")
    if len(rows) < 1:
        return False  # must have rows to verify against
    event_ids = {r.get("event_id", "").strip() for r in rows}
    return "E12" not in event_ids


async def _s1_score_correction_applied(ctx) -> bool:
    """Key: Agent proactively discovered score_correction.csv and included E10"""
    rows = _read_csv(ctx, "top10_selection.csv")
    if len(rows) < 1:
        return False
    event_ids = {r.get("event_id", "").strip() for r in rows}
    return "E10" in event_ids


async def _s1_e10_rank(ctx) -> bool:
    """Agent ranked E10 at #4 (heat_score 85 places it between E03=86 and E04=84)"""
    rows = _read_csv(ctx, "top10_selection.csv")
    row = _find_csv_row(rows, "event_id", "E10")
    if not row:
        return False
    try:
        rank = int(row.get("rank", "0").strip())
        return rank == 4
    except (ValueError, TypeError):
        return False


async def _s1_feature_draft_exists(ctx) -> bool:
    """Agent produced feature_draft.md with meaningful content"""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "feature_draft.md" if subdir else ctx.workspace / "feature_draft.md"
        if path.exists() and path.stat().st_size >= 200:
            return True
    return False


# -- S2: Final Photo-Source Review --

async def _s2_metro_photo_replaced(ctx) -> bool:
    """Key: Agent used photo_registry update to replace E05 photo with metro_platform_launch.jpg"""
    rows = _read_csv(ctx, "top10_selection.csv")
    row = _find_csv_row(rows, "event_id", "E05")
    if not row:
        return False
    photo = row.get("recommended_photo", "").strip().lower()
    return photo == "metro_platform_launch.jpg"


async def _s2_wrong_metro_photo_removed(ctx) -> bool:
    """Agent removed metro_opening_crowd.jpg from entire selection — reverse check"""
    rows = _read_csv(ctx, "top10_selection.csv")
    if len(rows) < 1:
        return False  # must have rows to verify against
    for r in rows:
        photo = r.get("recommended_photo", "").strip().lower()
        if "metro_opening_crowd" in photo:
            return False
    return True


async def _s2_feature_draft_updated(ctx) -> bool:
    """Agent updated feature_draft.md after the metro photo swap (file size increased or content changed)"""
    for subdir in ["", "outputs"]:
        path = ctx.workspace / subdir / "feature_draft.md" if subdir else ctx.workspace / "feature_draft.md"
        if path.exists() and path.stat().st_size >= 200:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            # Must mention the metro photo replacement
            has_metro_ref = any(kw in text for kw in [
                "metro_platform_launch", "metro platform", "replacement",
                "do_not_use", "suzhou", "replaced",
            ])
            return has_metro_ref
    return False


async def _s2_final_selection_count(ctx) -> bool:
    """Final shortlist still contains exactly 10 rows"""
    rows = _read_csv(ctx, "top10_selection.csv")
    return len(rows) == 10


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_selection_count", "checker": _s0_selection_count, "weight": 1.0},
        {"id": "S0_e07_excluded", "checker": _s0_e07_excluded, "weight": 2.0},
        {"id": "S0_e11_promoted", "checker": _s0_e11_promoted, "weight": 1.5},
        {"id": "S0_e01_photo_ok", "checker": _s0_e01_photo_ok, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_e12_excluded", "checker": _s1_e12_excluded, "weight": 2.0},
        {"id": "S1_score_correction_applied", "checker": _s1_score_correction_applied, "weight": 2.0},
        {"id": "S1_e10_rank", "checker": _s1_e10_rank, "weight": 1.5},
        {"id": "S1_feature_draft_exists", "checker": _s1_feature_draft_exists, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_metro_photo_replaced", "checker": _s2_metro_photo_replaced, "weight": 2.0},
        {"id": "S2_wrong_metro_photo_removed", "checker": _s2_wrong_metro_photo_removed, "weight": 2.0},
        {"id": "S2_feature_draft_updated", "checker": _s2_feature_draft_updated, "weight": 1.5},
        {"id": "S2_final_selection_count", "checker": _s2_final_selection_count, "weight": 1.0},
    ],
}
