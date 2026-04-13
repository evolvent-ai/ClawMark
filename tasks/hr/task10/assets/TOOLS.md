# Tools

## Email (Mock Email MCP)

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| `xiao.lin@starocean.cn` | Xiao Lin (you) | Expense Audit Specialist |
| `liu.finance@starocean.cn` | Manager Liu | Finance Manager |
| `zhang.qiang@starocean.cn` | Zhang Qiang | Sales Team / claimant |
| `li.na@starocean.cn` | Li Na | Marketing Team / claimant |
| `wang.peng@starocean.cn` | Wang Peng | Engineering Team / claimant |
| `cfo@starocean.cn` | CFO | Approval authority for over-limit client entertainment |

## Expense System (Mock Notion MCP)

Travel reimbursement database with claim-level records.

**Database**: march_travel_expenses
**Fields**: claim_id | employee | category | description | amount_claimed | attachments | notes | status

## Spreadsheet (Google Sheets)

- **Travel Policy Limits 2025** — Policy limit reference table
- **March Expense Summary** — Summary table for final approved / rejected amounts

## Calendar (Mock Calendar MCP)

Business trip schedule verification.
**Calendar**: StarOcean Business Travel

## File System

- `input/` — Pre-seeded materials (read-only).
- `workspace/` — Agent output area (read-write).
