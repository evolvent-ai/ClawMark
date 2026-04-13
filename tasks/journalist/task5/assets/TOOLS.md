# Tools

## Email (Mock Email MCP)

You use the managing editor's mailbox `liu.ying@newsroom.com` to read and send emails.

| Address | Person | Role |
| --- | --- | --- |
| `reporter.chen@newsroom.com` | Reporter Xiao Chen | Reporter who collected the materials |
| `li.pr@xianweixuan.com` | PR Manager Li | Corporate PR contact for Runjian Calorie Group |

## File System

- `input/` contains seeded photos, video, audio, PDFs, database, and stage-injected materials.
- `workspace/` is the writable output area for deliverables.

## Terminal

Use it for:

- SQLite database queries: `sqlite3 input/food_inspection.db "SELECT * FROM inspections WHERE ..."`
- File inspection and metadata checks
- CSV processing

## Database

- File: `input/food_inspection.db` (SQLite)
- Table: `inspections`
- Columns: `store_id`, `store_name`, `district`, `date`, `result`, `detail`

## Calendar (CalDAV)

- Calendar contains publication deadline events.
