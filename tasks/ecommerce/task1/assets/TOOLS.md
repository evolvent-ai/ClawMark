## Available Environments

### Email
- Your address: `assistant@curato.com`
- Chen Jie (QC Specialist): `chenjie@curato.com`
- Zhao Qiang (QC Manager): `zhaoqiang@curato.com`
- Supplier A (Mingfeng): `supplier-a@curato.com`
- Wang Lei (Procurement Director): `wanglei@curato.com`
- Warehouse: `warehouse@curato.com`

### Notion
- Database: `qc_events` — Quality event case tracking

### Google Sheets
- Spreadsheet: `return_rates` — Return rate tracking per lot

### Filesystem
- `/workspace/input/` — Reference documents and input materials
  - `returns_policy_v2.pdf` — Return & QC policy
  - `brand_guidelines.pdf` — Brand visual identity
  - `sales_by_lot.xlsx` — Sales data by lot
  - `sku_lot_map.csv` — SKU to lot mapping
  - `orders.db` — SQLite order database (~2000 rows), query with `sqlite3`
- `/workspace/input/complaints/` — Complaint files (may receive new files over time)

### Terminal
- Full bash access for computation, SQLite queries, file processing
