# Agents

## Output Specifications

### proposal_review.csv

A structured issue report for the proposal draft. Must be placed in `workspace/`.

**Schema** (columns):

| Column | Type | Description |
|--------|------|-------------|
| issue_id | string | Unique identifier (e.g., PR-001) |
| section | string | Which section of the proposal |
| severity | enum | `critical` / `warning` / `note` |
| issue_type | enum | `word_count_exceeded` / `reference_format_error` / `duplicate_reference` / `publication_status_mismatch` / `if_data_discrepancy` / `budget_ratio_violation` / `expired_quote` / `missing_section` / `ethics_incomplete` / `plagiarism_check_missing` / `other` |
| description | string | Detailed description of the issue |
| evidence_source | string | Which file or system the evidence came from |
| recommended_action | string | Suggested fix |

### Budget Files

Budget data should be entered into `budget_sheet` (Google Sheet). Final budget summary as `final_budget.csv` in `workspace/`.

**final_budget.csv schema**:

| Column | Type | Description |
|--------|------|-------------|
| category | string | Budget category (e.g., equipment, business, labor, indirect) |
| item | string | Specific item description |
| subtotal | number | Amount in RMB |
| year1 | number | Year 1 allocation |
| year2 | number | Year 2 allocation |
| year3 | number | Year 3 allocation |
| year4 | number | Year 4 allocation |
| total | number | Total across years |
| remarks | string | Notes or justification |

### precheck_report.csv

Pre-review self-check list. Must be placed in `workspace/`.

**Schema** (columns):

| Column | Type | Description |
|--------|------|-------------|
| item_id | string | Checklist item ID |
| item | string | Description of the checklist item |
| status | enum | `done` / `pending` / `blocked` |
| action_needed | string | What still needs to be done |

### submission_checklist.csv

Final submission checklist. Must be placed in `workspace/`.

**Schema** (columns):

| Column | Type | Description |
|--------|------|-------------|
| item_id | string | Checklist item ID |
| item | string | Description |
| status | enum | `complete` / `incomplete` / `needs_pi_action` |
| notes | string | Details or blockers |

### Email Communication

- Use formal Chinese for all emails to Research Office and Finance.
- Pre-review submission emails should clearly label materials as "pre-review version".
- Never send emails that could be construed as formal NSFC submission.

### File Naming

- All output files go to `workspace/`.
- Use snake_case naming.
- Do not modify files in `input/` — that directory is read-only.
