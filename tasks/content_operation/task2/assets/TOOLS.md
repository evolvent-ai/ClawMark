# Tools

## Email

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| assistant@company.com | You (Xiao An) | Creator collaboration assistant |
| zhou.lin@company.com | Zhou Lin | Your manager |
| finance@company.com | Finance team | Finance shared inbox |
| collab@company.com | Collab team | Creator collaboration shared inbox |

## Creator Pipeline (Notion)

Creator CRM and pipeline tracking database.

**Database**: `creator_pipeline`

**Fields**: Creator ID | Creator Name | Platform | Audience | Asking Price | Status | Schedule | Risk Flag | Note

## Budget Tracker (Google Sheet)

Creator collaboration budget tracking spreadsheet.

**Sheet**: `Creator_Collab_Q1`

**Columns**: Campaign | Approved Budget | Committed Budget | Frozen Budget | Actual Spend | Reserve Note

## File System

- `input/creator_pitches/` — Pitch decks and audience screenshots (read-only)
- `input/ref/kol_brand_brief.pdf` — Brand collaboration policy (read-only)
- `input/notion_attachments/` — Pipeline screenshots from Notion (read-only)
- `input/slack_files/` — Files shared in Slack channels (read-only)
- `input/docusign_exports/` — Contract templates (read-only)
- `outputs/` — Agent output area (read-write). Place all deliverables here.
