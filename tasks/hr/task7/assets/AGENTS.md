# Agents

## Output Specifications

### `attendance_resolution.csv`

Primary resolution log in `workspace/`.

**Schema:**

| Column | Type | Allowed Values |
|--------|------|----------------|
| employee_id | string | E01–E12 |
| exception_date | date | YYYY-MM-DD |
| final_status | enum | `approved_leave`, `field_work`, `absent`, `pending_review` |
| evidence | string | Filename or description of proof used |
| note | string | Free text explanation |

All 12 exception rows must appear. The `final_status` must use one of the four enum values exactly.

### `attendance_Nov_processed.xlsx`

Updated workbook in `workspace/`. Preserve the original 100-row structure and add a dedicated `final_status` column. Values must match the same enum above.

### `attendance_followups.md`

Place in `workspace/`. Must record:

- Employees still requiring payroll sync
- Why they remain pending
- Any follow-up owner or verification note

### Email Communication

- Use formal, professional Chinese.
- Absence emails must state the specific reason for the decision.
- When a case is under review, avoid sounding final.

### File Naming

- Write all outputs to `workspace/`.
- Use the exact filenames above.
- Do not modify anything in `input/`.
