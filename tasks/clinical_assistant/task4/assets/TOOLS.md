# Tools

## Email (Mock Email MCP)

Patient communication and correspondence, using Dr. Chen's email (`dr.chen@greenfieldchc.org`).

- Dr. Chen's inbox -- receives emails from patients and their family members
- `patient_d5011@email.com` -- Patient D-5011, Margaret Zhang
- `patient_d5012@email.com` -- Patient D-5012, Henry Li

Emails may include file attachments (images, audio, PDFs).

## Notion (Patient Health Profiles)

Structured patient data and follow-up records.

- Database: `patient_profiles` -- Patient demographics, diagnosis, medications, lab results, vitals
- Database: `followup_records` -- Follow-up visit records for all patients

## Google Sheets (Follow-up Data Tracker)

Tabular follow-up data and monitoring values.

- Spreadsheet: `followup_tracker` -- Monitoring data: glucose, BP, HbA1c, medication adherence, interventions

## Calendar (Mock Calendar MCP)

Follow-up appointments and clinic scheduling.

- `dr_chen_clinic` -- Dr. Chen's clinic calendar

## File System

- `input/` -- Pre-loaded input materials (read-only): glucose photos, diet diaries, audio recordings, PDF guides
- Working directory root -- Output files (read-write)
