# Tools

## Email

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| assistant@university.edu | You | Research assistant |
| lin.fan@university.edu | Lin Fan | Associate Professor (your PI) |
| sci_admin@university.edu | Research Office Zhang | Research administration |
| budget_li@finance.edu | Finance Li | Budget officer |
| student.zhao@university.edu | Zhao | PhD student (team member) |

## Notion

Proposal progress tracking database.

**Database**: `proposal_db`

**Fields**: section / status / owner / notes / last_updated

## Google Sheets

### budget_sheet — Budget Spreadsheet

**Columns**: category / item / unit_price / quantity / subtotal / year1 / year2 / year3 / year4 / total / remarks

### pub_sheet — Publication List

**Columns**: seq / author / title / venue / year / IF / citations / funding_label

## File System

- `input/` — Pre-seeded materials (read-only). Contains proposal drafts, publication PDFs, budget documents, and administrative notices.
- `workspace/` — Agent output area (read-write). Place all deliverables here.
