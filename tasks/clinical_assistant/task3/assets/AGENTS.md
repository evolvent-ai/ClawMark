# Agents

**Language Rule**: All your outputs (filenames, CSV content, reports, email text) must be in English.

## Output Specifications

### 1. Triage Findings CSV

Primary structured output capturing all clinical findings across patients.

- **Filename**: `triage_findings.csv`
- **Location**: stored directly in the workspace root (no `outputs/` subdirectory)
- **Columns** (exact names):

| Column | Type | Allowed Values |
|--------|------|---------------|
| `patient_id` | text | `E-8801`, `E-8802`, `E-8803`, `E-8804` |
| `finding_type` | enum | `vitals_discrepancy`, `mi_symptoms`, `gi_hemorrhage`, `surgeon_shortage`, `dka_risk`, `protocol_update`, `transfer_required`, `critical_value`, `routine_assessment` |
| `evidence_source` | enum | `triage_form`, `cardiac_monitor`, `family_audio`, `lab_result`, `staff_schedule`, `triage_protocol`, `ticket_attachment`, `physician_update` |
| `recommended_level` | enum | `I`, `II`, `III`, `IV` |
| `detail` | free text | Brief clinical description of the finding |

- One row per distinct finding. A single patient may have multiple rows (e.g., E-8801 has vitals_discrepancy AND mi_symptoms).

### 2. Priority List CSV

Generated when Charge Nurse Zhang requests a waiting priority list.

- **Filename**: `priority_list.csv`
- **Location**: stored directly in the workspace root
- **Columns** (exact names):

| Column | Type | Allowed Values |
|--------|------|---------------|
| `rank` | integer | 1, 2, 3, 4, ... |
| `patient_id` | text | `E-8801`, `E-8802`, `E-8803`, `E-8804` |
| `triage_level` | enum | `I`, `II`, `III`, `IV` |
| `status` | enum | `being_treated`, `waiting`, `pending_transfer`, `admitted` |
| `disposition` | free text | Current disposition or department |

- Rows must be ordered by triage acuity (Level I first, Level IV last). Same-level patients may appear in either order.

### 3. Triage Assessment Reports

Per-patient narrative reports stored in the workspace root.

- **Filename**: `{PatientID}_triage_assessment.md` (e.g., `E-8801_triage_assessment.md`)
- **Location**: stored directly in the workspace root
- **Structure**:
  1. Patient ID and demographics
  2. Chief complaint
  3. Vital signs (from all sources, noting any discrepancies)
  4. Pain score
  5. Preliminary triage acuity level (I/II/III/IV) with rationale
  6. Recommended disposition
  7. Remarks (additional findings, cross-modal observations)

### 4. Ticket Updates (Notion Database)

Update corresponding patient records in the `triage_queue` Notion database.

- Fields to update: `Triage Level`, `Status`, `Target Department`, `Assessment Notes`
- **Important**: Do NOT directly set Triage Level to `I` or `II` in the ticket. Only recommend Level I/II in your triage assessment report. The official triage level for I/II is confirmed by the charge nurse or attending physician.

### 5. File Naming

- All output files are stored directly in the workspace root.
- Do not modify any files in `input/` -- that directory is read-only.
