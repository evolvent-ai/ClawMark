# Work Standards

## Handover Audit Output

### `output/handover_audit.xlsx`
Fill in the `handover_audit_template.xlsx` template and save to `output/handover_audit.xlsx`.

**Sheet 1: "Module Audit"**

| Column | Type | Description |
|--------|------|-------------|
| `module_id` | text | Pre-filled (SP-001 through SP-006), do not modify |
| `module_name` | text | Pre-filled, do not modify |
| `notion_status` | enum | Status from Notion board. Values: `completed` / `testing` / `in_progress` / `not_started` / `deferred` |
| `actual_status` | enum | True status verified against actual files. Values: `completed` / `testing` / `in_progress` / `not_started` / `deferred` |
| `has_design_doc` | enum | `yes` / `no` |
| `has_test_report` | enum | `yes` / `no` |
| `has_acceptance` | enum | `yes` / `no` |
| `status_match` | enum | `yes` / `no` -- whether `notion_status` matches `actual_status` |
| `issues` | text | Description of issues found |

**actual_status determination rules**:
- `completed`: Design doc + test report + acceptance certificate -- all three present
- `testing`: Has test report but not yet accepted
- `in_progress`: Has design doc, testing/acceptance not complete
- `not_started`: No substantive deliverables
- `deferred`: Confirmed deferred to a later version

**Sheet 2: "Budget Reconciliation"**

| Column | Type | Description |
|--------|------|-------------|
| `item` | text | Pre-filled, do not modify |
| `supplier` | text | Pre-filled, do not modify |
| `contract_monthly_yuan` | number | Latest monthly fee per contract (if handwritten modifications exist, use the modified amount) |
| `actual_monthly_yuan` | number | March actual payment amount (from `payment_records.csv`) |
| `variance_yuan` | number | `actual_monthly_yuan - contract_monthly_yuan` |
| `variance_pct` | text | Percentage, e.g. `0.0%` |
| `issue` | text | Variance explanation |

### `output/budget_summary.txt`
Key-value format, one per line:
```
total_contract_monthly=<number>
total_actual_monthly=<number>
total_variance=<number>
budget_status=<on_budget|over_budget|under_budget>
missing_deliverables_count=<number>
status_mismatch_count=<number>
```

Rules:
- `budget_status`: variance > 0 -> `over_budget`; variance == 0 -> `on_budget`; variance < 0 -> `under_budget`
- `missing_deliverables_count`: Total count of `has_xxx == no` across all modules (excluding `deferred` modules). Count each of `has_design_doc`, `has_test_report`, `has_acceptance` separately per module. For example, if SP-001 has `has_test_report=no` and `has_acceptance=no`, that contributes 2 to the count. Include ALL non-deferred modules, even those that are `not_started`.
- `status_mismatch_count`: Number of modules where `status_match == no`

## File Filing
- Organize files under `project_files/` according to the filing standard in `filing_standard.md` into the `input/archive/` directory
- Keep only the latest version; move old versions to `input/archive/_deprecated/`

## Notion Updates
- Fix any incorrect statuses on the `smartpark_v2_board` board

## Email
- Send an audit findings summary email to Director Liu (david.liu@dingxin.com)

## Information Sources
- Project files in workspace are legacy from the previous PM and may be incomplete or inaccurate
- Task statuses on the Notion board were maintained by the previous PM and may not match reality
- Information from different sources may be inconsistent; you need to verify and judge on your own
