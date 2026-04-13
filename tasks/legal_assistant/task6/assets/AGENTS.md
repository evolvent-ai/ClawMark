# AGENTS (Task Work Specifications)

## Startup Procedure

Each time you start:

1. Check Feishu and email—understand current task instructions
2. Go to CRM (case MD2024-011) to pull all evidence attachments
3. Proactively check data table (compensation calculation table) and calendar for updates

## Safety Rules

- Do not sign legal documents on behalf of client or any party
- Do not independently commit to settlement or compensation amounts externally, requires Attorney Li's confirmation
- Do not disclose our litigation strategy or compensation bottom line to hospital
- Must honestly report evidence unfavorable to our side

## Output Formats

### evidence_analysis.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| evidence_id | Sequential ID | E01, E02… |
| source_file | Specific filename | xray_preop.jpg, surgery_record.pdf, etc. |
| verification_content | Specific matter verified | Free text |
| document_record | What the document states | Free text |
| verification_result | Verification outcome | `VERIFIED` / `CONTRADICTED` / `QUESTIONABLE` |
| finding_type | Category of finding | `surgical_site_error` / `date_anomaly` / `record_inconsistency` / `nursing_discrepancy` / `correction_irregularity` / `compensation_item` / `none` |
| evidence_source | Modality used for verification | `xray_image` / `pdf_text` / `image_handwriting` / `spreadsheet_data` / `cross_file_comparison` |
| anomaly_notes | Specific explanation of contradiction | Free text |

### case_timeline.md

List all key events in chronological order, format: `YYYY-MM-DD | Event description | Source`

### medical_error_brief.md

Structure:
```
## Medical Error Analysis (MD2024-011)

### Core Contradiction 1: Surgical Site Record Inconsistency
### Core Contradiction 2: Medical Record Date Anomaly
### Loss Assessment
### Recommended Next Steps
```

### compensation_calc.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| item_id | Sequential ID | C01, C02… |
| compensation_item | Medical expenses/lost wages/nursing fees/disability compensation, etc. | Free text |
| amount_cny | Numerical value | Numeric |
| calculation_basis | Data source or legal provisions | Free text |
