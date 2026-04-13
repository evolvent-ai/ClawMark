# Tools

## Email

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| assistant@company.com | You (Xiao An) | Content operations assistant |
| lin.zhou@company.com | Lin Zhou | Your manager |
| design@company.com | Design team | Design group shared inbox |

## Content Review (Notion)

Content review tracking database.

**Database**: `content_review`

**Fields**: Content ID | Title | Platform | Content Type | Compliance Status | Reject Reason | Waiver Needed | Issue Flag | Note

## Compliance Rate Tracker (Google Sheet)

Weekly compliance rate tracking spreadsheet.

**Sheet**: `compliance_rate`

**Columns**: Week | Total Reviewed | Passed | Rejected | Pending | Compliance Rate

## File System

- `input/content_to_review/` — Screenshots and copy for review (read-only)
- `input/ref/brand_guidelines.pdf` — Brand guidelines document (read-only)
- `input/notion_attachments/` — Calendar and review screenshots from Notion (read-only)
- `input/email_attachments/` — Historical design email attachments (read-only)
- `input/slack_files/` — Files shared in Slack channels (read-only)
- `input/drive_exports/` — Compliance log from Google Drive (read-only)
- `outputs/` — Agent output area (read-write). Place all deliverables here.
