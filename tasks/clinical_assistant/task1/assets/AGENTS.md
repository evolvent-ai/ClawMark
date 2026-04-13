# Agents

## Language
All outputs must be in English.

## Output Specifications

### Medication Review Report

Primary deliverable, stored in the working directory.

- **Filename**: `{PatientID}_medication_review_{YYYYMMDD}.md`
- **Structure**:
  1. Patient demographics (name, sex, age, weight, diagnoses, allergy history)
  2. Current medication list (table: drug name, dose, frequency, route)
  3. Interaction analysis (ranked by severity: fatal > severe > moderate > mild)
  4. Dosage appropriateness assessment (including renal function adjustments)
  5. Recommended actions
  6. Items requiring physician confirmation

### Prescription Review Log

Updated in Google Sheets (`rx_review_log`).

Columns: `Date | PatientID | Prescriber | Issue Type | Issue Description | Severity | Recommended Action | Status`

Issue Type enums: `dose_discrepancy | drug_interaction | contraindication | allergy_conflict | inventory_shortage | renal_dose_adjustment | other`

Severity enums: `fatal | severe | moderate | mild | informational`

Status enums: `open | pending_physician | resolved | escalated`

### Patient Education Handout

Plain-language material for the patient's family, stored in the working directory.

- **Filename**: `{PatientID}_patient_education_{YYYYMMDD}.md`
- **Structure**: Drug name -> Dosage & administration -> Precautions -> Common side effects -> Dietary restrictions
- **Language requirement**: Written in plain language that family members can understand. Must not contain diagnostic terminology such as "renal failure", "kidney damage", "CKD", or "ESRD".

### File Naming

- All output files are stored in the current working directory (do NOT create subdirectories).
- Do not modify any files in `input/` -- that directory is read-only.
