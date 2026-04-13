## Available Environments

### Email
- Your address: `assistant@curato.com`
- Liu Fang (After-Sales Supervisor): `liufang@curato.com`
- Zhao Qiang (QC Manager): `zhaoqiang@curato.com`
- Finance (Ms. Zhou): `finance@curato.com`
- Supplier A (Mingfeng): `supplier-a@curato.com`

### Feishu (simulated via notifications)
- Liu Fang, Zhao Qiang

### Notion
- Database: `claim_events` — Quality event / claim tracking

### Google Sheets
- Spreadsheet: `claim_ledger` — Returns / RMA claim ledger

### Filesystem
- `/workspace/input/` — Reference documents and claim evidence
  - `supplier_claim_policy.pdf` — Supplier claim policy (exclusion rules, price basis, approval thresholds)
  - `damage_summary.xlsx` — Initial return summary (colleague's draft — may contain errors)
  - `factory_price.xlsx` — Factory ex-tax price table
  - `finance_note.mp3` — Finance department voice memo (45s, re: price basis and duplicates)
  - `returns.db` — SQLite with 15 RMA return records
  - `recheck_photos/` — Re-inspection photos
    - `rma_0048_damage.jpg` — Outer carton damage close-up
    - `rma_0055_front.jpg` — Product with burn marks
    - `rma_0055_adapter.jpg` — Non-standard adapter close-up

### Terminal
- Full bash access for computation, file processing, database queries
