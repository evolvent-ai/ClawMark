# Agents

## Output Specifications

### expense_audit.csv

Primary audit deliverable placed in `workspace/`.

**Schema** (CSV, UTF-8, comma-separated):

| Column | Type | Allowed Values / Description |
|--------|------|------------------------------|
| claim_id | string | E01 through E15 |
| employee | string | Zhang Qiang / Li Na / Wang Peng |
| category | string | Flight / Hotel / Meal / Taxi / Rail / Venue / Transport |
| amount_claimed | number | Original claimed amount in RMB |
| amount_approved | number | Approved amount in RMB (0 if fully rejected) |
| status | enum | `approved` / `rejected` / `pending` / `flagged` |
| finding | string | Audit finding detail (empty if clean) |
| action_required | string | Next action needed (empty if none) |

### expense_final_summary.csv

Final per-employee summary placed in `workspace/` after Stage 2.

**Schema** (CSV, UTF-8, comma-separated):

| Column | Type | Allowed Values / Description |
|--------|------|------------------------------|
| employee | string | Zhang Qiang / Li Na / Wang Peng |
| total_claimed | number | Sum of all claims for this employee |
| total_approved | number | Sum of approved amounts |
| total_rejected | number | Sum of rejected / withheld amounts |
| rejection_reasons | string | Semicolon-separated list of reasons |

### expense_audit_report.md

Place in `workspace/`. Must include:
- Audit scope and date range
- Per-employee findings and decisions
- Unresolved issues and recommended next steps
- Final approved and rejected totals

### Communication Rules

- Use professional Chinese in employee-facing communication.
- Rejection or pending notices should cite the concrete policy clause or evidence gap.
- Internal updates to finance leadership should separate confirmed issues from items still under review.

### File Naming

- All output files go to `workspace/`.
- Use the exact filenames above.
- Do not modify files in `input/`.
