# Tools

## Email

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| assistant@company.com | You (Xiao An) | Content operations assistant |
| zhao.yue@company.com | Zhao Yue | Your manager |
| design@company.com | Design team | Design group shared inbox |

## Content Calendar (Notion)

Content scheduling and request tracking database.

**Database**: `content_calendar`

**Fields**: Request ID | Date | Platform | Type | Status | Note | Budget | Issue Flag

## Budget Tracker (Google Sheet)

Campaign budget tracking spreadsheet.

**Sheet**: `Q1_Content_Budget`

**Columns**: Campaign | Owner | Approved Budget | Committed Budget | Actual Spend | Reserve Note

## File System

- `input/design_requests/` — New design request screenshots (read-only)
- `input/ref/brand_guidelines.pdf` — Brand guidelines document (read-only)
- `input/email_attachments/` — Historical and delivery email attachments (read-only)
- `input/notion_attachments/` — Calendar and brief screenshots from Notion (read-only)
- `input/slack_files/` — Files shared in Slack channels (read-only)
- `outputs/` — Agent output area (read-write). Place all deliverables here.
