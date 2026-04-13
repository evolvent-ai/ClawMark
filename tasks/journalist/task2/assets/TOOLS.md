# Tools

## Email (Mock Email MCP)

You use Liu Ying's mailbox (liu.ying@newsroom.com) to read and send emails on her behalf. Known addresses:

| Address | Person | Role |
|---------|--------|------|
| liu.ying@newsroom.com | Liu Ying | Chief Editor, Metropolitan News Desk (Your Supervisor) — **this is your working mailbox** |
| reporter.chen@newsroom.com | Xiao Chen | Reporter |
| pr@chunxiangfang.com | Chunxiangfang PR Dept. | Company Public Relations |

## CMS — Content Management System (Notion)

News article database.

**Database**: `news_db` (News Article Database)

**Fields**: Title, section, status (Draft/Pending Review/Published), body, confirmed facts, pending verification items

## Fact-Check Sheet (Google Sheets)

Fact-checking evidence tracking spreadsheet.

**Sheet**: `factcheck_brand`

**Fields**: fact_field, source, value, confidence, conflict, final_value, note

## Terminal (Real Bash)

Data processing, CSV querying, EXIF extraction, file operations.

## File System

- `input/` — Pre-seeded materials (read-only). Contains product photos, factory photos, business registration, promotional materials, intangible heritage database (CSV), consumer complaints, meeting transcript, and test report scan.
- `workspace/` — Agent output area (read-write). Place all deliverables here.
