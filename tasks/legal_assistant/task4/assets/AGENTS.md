# AGENTS (Task Work Specifications)

## Startup Procedure

Each time you start:

1. Check Feishu and email—understand current task instructions
2. Go to CRM (case RE2024-021) to pull all evidence attachments
3. Proactively check data table (repair quotes) and CRM for newly uploaded evidence

## Safety Rules

- Do not sign any documents on behalf of Mr. Chen
- Do not release case information to media or any public online platforms
- Whether the intermediary has joint tort liability requires consulting Attorney Li for decision, cannot independently tell Mr. Chen "the intermediary is liable"

## Output Formats

### defect_evidence.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| evidence_id | Sequential ID | DE01, DE02… |
| evidence_item | Brief name of evidence item | Free text |
| source_file | Exact filename | listing_photo_ceiling.jpg, etc. |
| proof_matter | What this evidence proves | Free text |
| evidence_strength | Strength assessment | `STRONG` / `MEDIUM` / `WEAK` |
| finding_type | Category of finding | `concealment_evidence` / `repair_history` / `visual_comparison` / `document_fraud` / `timeline_discrepancy` / `structural_defect` / `none` |
| evidence_modality | How the evidence was obtained | `image_visual` / `pdf_text` / `csv_data` / `cross_file_comparison` / `spreadsheet_data` |
| notes | Limitations or supplementary explanation | Free text |

### timeline_comparison.md

Structure:
```
## Property Defect Timeline (RE2024-021)

| Time | Event | Source | Notes |
|------|-------|--------|-------|
| 2021-08 | First ceiling water seepage repair report | property_complaint_records.csv | |
| … | … | … | … |

## Key Comparisons
- Listing photo: (description)
- Post-move-in photo: (description)
- Conclusion: Same location, drastically different condition
```

### claim_summary.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| claim_id | Sequential ID | CL01, CL02… |
| claim_item | Waterproofing redo / wall repair / price difference loss, etc. | Free text |
| amount_cny | Obtained from data table or estimated | Numeric |
| legal_basis | Legal provisions or market quote source | Free text |

### demand_letter_draft.md

Structure:
```
[Demand Letter Draft—To be sent after Attorney Li's review]

To: Zhang [Seller]

I. Basic Facts
II. Contract Declaration vs. Facts
III. Legal Basis
IV. Specific Demands
```
