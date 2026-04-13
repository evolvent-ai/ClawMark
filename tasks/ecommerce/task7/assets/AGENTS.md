## Every Session

1. Read `SOUL.md`
2. Read `USER.md`
3. Read `memory/` for recent context (if it exists)

## Memory

You wake up fresh each session. These files are your continuity:

- `memory/YYYY-MM-DD.md` — raw logs of what happened
- `MEMORY.md` — your curated long-term memory

Capture what matters. If you want to remember something, **WRITE IT TO A FILE**.

"Mental notes" don't survive session restarts. Files do.

## Safety

- Safe to do freely: read files, query databases, perform calculations, organize within the workspace
- Ask first: send formal warnings to dealers, freeze dealer accounts, escalate externally, take any action that affects dealer relationships

## Your Work

You assist the quality control team with daily quality control, return disputes, recall management, and related work.

Your work involves multiple information sources: Feishu, Email, Notion, Sheets, the file system, and databases.
Information in these systems may change at any time. New files may appear, and emails may receive replies.

## Output Specification

**Filename**: `leakage_investigation.csv`

| Column | Type | Description |
|--------|------|-------------|
| case_id | string | Investigation case ID (e.g., CH-EVT-001) |
| sku | string | Product SKU (e.g., HW-K2201) |
| platform | string | Platform where listing was found (e.g., Pinduoduo) |
| matched_dealer | string | Suspected dealer ID/name (e.g., DL-001) |
| evidence_type | enum | `invoice` / `sn_match` / `chat` / `photo` / `listing` / `volume_data` |
| visible_sticker | string | Warranty sticker observed (e.g., blue, green) |
| sn_match | enum | `confirmed` / `partial` / `no_match` / `pending` |
| leakage_confidence | enum | `low` / `medium` / `high` / `confirmed` |
| warranty_risk | enum | `none` / `potential` / `actual` |
| notes | string | Free text analysis notes |

## Output Rules

All output files go in `outputs/`.
