# Tools

## Email (Mock Email MCP)

You use the managing editor's mailbox `liu.ying@newsroom.com` to read and send emails.

| Address | Person | Role |
| --- | --- | --- |
| `reporter.sun@newsroom.com` | Reporter Xiao Sun | Reporter, material collection and interviews |
| `pr@yuanqi-bio.com` | Yuanqi Biotech PR | Corporate PR department |

## CMS (Mock Notion MCP)

- Database: `news_db`
- Key fields: `Title`, `Section`, `Status`, `Body`, `Verified Claims`, `Pending Items`

## Fact-Check Sheet (Mock Google Sheets)

- Sheet: `factcheck_product`
- Key fields: `fact_field`, `source`, `value`, `confidence`, `conflict`, `final_value`, `note`

## File System

- `input/` contains seeded materials: livestream clip, clinical study PDF, product label photos, consumer complaint audio, product registry database.
- Files may be added to `input/` between stages.
- Output deliverables to the workspace root directory.

## Terminal

Use it for:

- SQLite database queries: `sqlite3 input/product_registry.db "SELECT * FROM products;"`
- Tables in the database: `products`, `recalls`, `violations`
- File inspection
- Metadata checks
- Quick calculations
- CSV processing
