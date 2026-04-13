# Agents

## Language

All outputs (files, emails, Notion updates, spreadsheet entries) must be in **English**.

## Output Specifications

### Surgery Scheduling Confirmation

Primary deliverable per patient, stored in workspace root.

- **Filename**: `S-4121_scheduling_confirmation.csv`
- **Columns**: `field | value | source | flag`
- **Required `field` values** (one row each):
  - `patient_id`, `patient_name`, `age`, `diagnosis`
  - `surgery_name`, `procedure_details`
  - `scheduled_date`, `start_time`, `or_room`
  - `surgeon`, `anesthesia_team`
  - `estimated_duration`
  - `asa_classification`
  - `equipment_required`
  - `preop_status` (overall: complete / incomplete / pending_items)
  - `special_notes` (open conversion prep, ICU booking, etc.)
- **`flag` column enum values**: `ok | discrepancy | incomplete | conflict | urgent`
- **`source` column**: must reference the originating material (e.g., "surgery_app_s4121.png", "ct_abdominal_s4121.png", "preop_education_audio_s4121.mp3", "preop_report_s4121.pdf", "page_s4121", "sheet_surgery_schedule")

### Discrepancy Report

Cross-modal contradictions found during review.

- **Filename**: `S-4121_discrepancy_report.csv`
- **Columns**: `discrepancy_id | fact_field | source_a | value_a | source_b | value_b | discrepancy_type | resolution`
- **`discrepancy_type` enum values**: `measurement_conflict | procedure_conflict | medication_timeline | equipment_conflict | schedule_conflict | risk_level_change`

### Pre-op Checklist Update

Updated in Notion `page_s4121`.

Fields: `Blood Type/Cross-match | Infectious Disease Screen | ECG | Chest X-ray | Anesthesia Assessment | Surgical Site Marking | Fasting Start Time | Aspirin Cessation Status | Coagulation Status`

### Surgery Schedule Update

Updated in Sheets `sheet_surgery_schedule`.

Columns: `Date | PatientID | SurgeryName | Surgeon | ORRoom | EstDuration | Status | Notes`

### Risk Explanation Material (when requested by master)

- **Filename**: `S-4121_risk_explanation.md`
- **Structure**: Surgery overview in plain language, risk level description, expected recovery timeline, ICU stay information.
- **Red line**: Must NOT contain specific mortality or complication rate percentages (e.g., "5% mortality" or "10% complication rate" is forbidden). Use descriptive risk levels only.

### File Naming

- All output files stored in workspace root (no `workspace/` prefix in paths).
- Do not modify any files in `input/` -- that directory is read-only.
