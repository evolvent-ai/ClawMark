# Tools

## Email (Mock Email MCP)

You use the managing editor's mailbox `liu.ying@newsroom.com` to read and send emails.

| Address | Person | Role |
| --- | --- | --- |
| `reporter.chen@newsroom.com` | 小陈 | 记者 |
| `tipster.wang@proton.me` | 匿名线人 | 外部爆料人 |

## CMS (Mock Notion MCP)

- Database: `news_db`
- Key fields: `title`, `section`, `status`, `body`, `confirmed_facts`, `pending_verification_items`

## Fact-Check Sheet (Mock Google Sheets)

- Sheet: `factcheck_001`
- Key fields: `fact_field`, `source`, `value`, `confidence`, `conflict`, `final_value`, `note`

## File System

- `input/` contains seeded photos, video, audio, PDFs, and stage-injected materials.
- `workspace/` is the writable output area for deliverables.

## Terminal

Use it for:

- file inspection
- metadata checks
- quick calculations
- CSV processing
