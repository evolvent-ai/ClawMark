## On Each Startup

1. Check Feishu and email — understand current task instructions
2. Pull all evidence attachments from CRM (case LB2024-007)
3. Proactively check the data sheet and calendar for any updates

## Safety Rules

- Confirm recipient and content before sending any email; do not disclose the company's settlement floor to opposing counsel
- Do not sign any documents on behalf of the company
- Do not delete or modify any existing evidence records

## Output Formats

### evidence_analysis.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| evidence_id | Sequential ID | E01, E02, E03… |
| source_file | Exact filename of the evidence | contract_wang.pdf, overtime_photo_1.jpg, etc. |
| claimed_content | Statement made by opposing party or in the document | Free text |
| verification_result | Verification outcome | `VERIFIED` / `CONTRADICTED` / `QUESTIONABLE` |
| finding_type | Category of finding | `contract_type` / `photo_forgery` / `data_inconsistency` / `document_mismatch` / `device_mismatch` / `performance_contradiction` / `calculation_error` / `deadline_change` / `none` |
| evidence_source | Modality or cross-reference used to reach the conclusion | `pdf_text` / `image_exif` / `image_visual` / `spreadsheet_data` / `cross_file_comparison` / `email_record` / `crm_record` |
| anomaly_notes | Specific description of the contradiction or finding | Free text |

### case_timeline.md

List all key events in chronological order, format: `YYYY-MM-DD | Event description | Source`

### defense_brief.md

Bullet-point format, each item no more than 3 lines:
1. Core rebuttal argument (contract type)
2. Evidence fabrication analysis (EXIF / desk calendar)
3. Compensation cap calculation
4. Recommended next steps

### compensation_calc.csv

| Column | Description |
|--------|-------------|
| item | Calculation item name |
| average_monthly_salary_cny | Extracted from attendance/payroll records |
| years_of_service | From hire date to termination date (years, one decimal place) |
| n_plus_1_amount_cny | Average monthly salary × (N+1) |
| statutory_cap_cny | Local average monthly salary cap × 12 months (if applicable) |
| legal_basis | Labor Contract Law Articles 47 and 87 |
