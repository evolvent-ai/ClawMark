# Agents

**Language**: All your outputs (files, emails, database entries, calendar events) must be in **English**.

## Output Specifications

### Follow-up Record

Primary deliverable per patient, written to the working directory.

- **Filename**: `{PatientID}_followup_record_{YYYYMMDD}.md`
- **Structure**:
  1. Patient Info (ID, name, age, diagnosis)
  2. Follow-up Date
  3. Current Symptoms
  4. Monitoring Data (table: glucose, BP, weight, etc.)
  5. Medication Adherence Assessment
  6. Lifestyle Assessment (diet, exercise)
  7. Intervention Plan
  8. Next Follow-up Plan

### Patient Communication

Via email from Dr. Chen's account (`dr.chen@greenfieldchc.org`) to patient's email.

Content: key reminders, appointment confirmations, educational material, lifestyle guidance responses. Use plain, patient-friendly language.

### Follow-up Summary

Generated on request for Dr. Chen.

- **Filename**: `followup_summary_{YYYYMMDD}.md`
- **Structure**: Brief summary of each patient's status, key findings, recommendations, and pending actions.

### File Naming

- All output files stored in the working directory root (not under `workspace/` or `outputs/`).
- Do not modify any files in `input/` -- that directory is read-only.
