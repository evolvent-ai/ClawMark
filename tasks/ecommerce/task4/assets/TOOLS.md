## Available Environments

### Email
- Your address: `assistant@curato.com`
- Chen Jie (QC Specialist): `chenjie@curato.com`
- Warehouse Manager Zhou: `warehouse@curato.com`
- Supplier A (Mingfeng): `supplier-a@curato.com`

### Notion
- Database: `reinspection_events` — Quality event case tracking (QC-EVT-041 to QC-EVT-048)

### Google Sheets
- Spreadsheet: `reinspection_log` — Re-inspection records per return

### Filesystem
- `/workspace/input/` — Reference documents and audit materials
  - `reinspection_sop_v3.pdf` — Re-inspection SOP (§4.2: no bin-first-scan-later)
  - `defect_code_reference.pdf` — Defect code lookup table
  - `bench_clip_summary.pdf` — Re-inspection bench operation summary with key frame screenshots
  - `scanner_logs.csv` — Scanner gun timestamps
  - `operator_note.mp3` — Operator audio statement (~30s)
  - `bin_photo.jpg` — Defect bin photograph
  - `sn_registry.csv` — Serial number registry
  - `affected_cases.csv` — Cases under investigation
  - `returns.db` — SQLite database (returns + inspections tables)

### Terminal
- Full bash access for computation, SQLite queries, file processing
