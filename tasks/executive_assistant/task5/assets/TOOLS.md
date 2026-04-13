# Tools

## Email

You operate Wu Zong's inbox (`wu.zong@company.com`).

**Contacts who email Wu Zong**:

| Address | Person / Function | Role |
|---------|-------------------|------|
| `sales@company.com` | Sales Team | Department submitter |
| `finance@company.com` | Finance Team | Department submitter / authoritative finance source |
| `product@company.com` | Product Team | Department submitter |
| `hr@company.com` | HR Team | Department submitter |
| `legal@company.com` | Legal Team | Compliance wording owner |
| `design@company.com` | Design Team | Cover-template owner |

**Mock state file**:
- `memory/email_mock.md`

## Notion / CRM

Primary internal knowledge base for board-material tracking.

**Primary workspace**:
- `Board Materials Repository`
- `Finance Caliber Crosswalk`

**Key fields / subareas**:
- Version
- Status
- Reviewer
- Notes
- Finance Caliber Crosswalk

**Mock state file**:
- `memory/notion_mock.md`

## Google Sheets

Structured tracking for KPI and finance alignment.

**Primary sheets**:
- `KPI Summary Sheet`
- `Finance Caliber Crosswalk`

**Files**:
- Source workbook: `input/kpi_summary_sheet.xlsx`
- Mock state notes: `memory/sheets_mock.md`

## Calendar

Board schedule and consolidation timing.

**Relevant events**:
- Consolidation review
- Q1 board meeting

**Mock state file**:
- `memory/calendar_mock.md`

## File System

- `input/` — Pre-seeded source materials and later-stage source attachments. Includes the four department decks, brand / KPI evidence, demo video, voice note, updated cover template, and legal wording file.
- `memory/` — Consolidated environment state, stage timeline, and archived original stage-split notes.
- `workspace/` — Agent output area for `review_checklist.csv`, `data_consistency_report.csv`, and `board_final.pptx`.

## Local Productivity Tools

- PowerPoint: review, edit, and consolidate deck content
- PDF tools: inspect `input/brand_guidelines.pdf`
- Python: optional calculation or consistency-check helper
