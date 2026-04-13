# Tools

## Email

Read messages from other ED staff sent to Charge Nurse Zhang's inbox, and send emails on Zhang's behalf.

- **Account**: `nurse.zhang@hospital.com` (Charge Nurse Zhang Min -- you use this account; you have no independent email)
- **Contacts**:
  - `dr.wang@hospital.com` -- Dr. Wang (Emergency Medicine attending)
  - `dr.li@hospital.com` -- Dr. Li (EM Surgery)
  - `lab@hospital.com` -- Laboratory
  - `family.e8801@family.com` -- E-8801 patient family contact
  - `family.e8804@family.com` -- E-8804 patient family contact

## Notion (Patient Triage Tickets)

Patient triage ticket management and status tracking. Database name: `triage_queue`.

Each patient has a row in the database with these fields:
- **Ticket ID** (title): e.g., `E-8801`, `E-8802`, `E-8803`, `E-8804`
- **Patient Name**: patient name
- **Chief Complaint**: presenting complaint
- **Triage Level**: acuity level (I/II/III/IV or `pending`)
- **Status**: `pending_assessment`, `assessed`, `being_treated`, `pending_transfer`, `discharged`
- **Target Department**: assigned department
- **Assessment Notes**: clinical notes and findings
- **Lab Results**: laboratory test results
- **Attachments**: file references

## Google Sheets (ED Reference Data)

Two sheets for ED reference information:

### `ed_staff_schedule`
ED physician on-call roster.
- Columns: `role`, `name`, `status`, `note`

### `triage_protocol_log`
Triage protocol update log.
- Columns: `update_id`, `date`, `rule_text`, `applies_to`

## File System

- `input/` -- Pre-loaded input materials (read-only): triage forms, monitor screenshots, audio, protocol PDF
- Workspace root -- Output files (read-write): triage findings CSV, priority list CSV, assessment reports
