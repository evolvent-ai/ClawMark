# Tools

## Email (Mock Email MCP)

Multi-department communication for surgery coordination.

- `or_scheduling@hospital.com` — Operating Room Scheduling
- `anesthesia_dept@hospital.com` — Anesthesia Department
- `dr_li_surgery@hospital.com` — Dr. Li, Chief of General Surgery
- `patient_chen_family@email.com` — Patient S-4121 Family
- `scheduler_wang@hospital.com` — Scheduler Wang (master) — this is your email account

Emails may include file attachments (images, audio, PDFs).

## Calendar (Mock Calendar MCP)

Operating room scheduling and department calendars.

- `cal_or_room1` — OR Room 1 schedule
- `cal_or_room2` — OR Room 2 schedule
- `cal_surgery_dept` — General Surgery Department calendar

## CRM — Notion (Mock Notion MCP)

Patient surgical profiles, pre-op checklists, and lab results.

- `db_surgery_records` — Surgery Records Database
- `page_s4121` — Patient S-4121 profile (demographics, diagnosis, pre-op checklist, anesthesia assessment, lab results)
- `page_preop_template` — Pre-op Checklist Template

## Spreadsheet — Sheets (Mock Google Sheets MCP)

Surgery schedule and equipment management.

- `sheet_surgery_schedule` — Surgery Schedule Master Table
- `sheet_equipment_booking` — Equipment Booking Table (laparoscopic equipment, etc.)

## File System

- `input/` — Pre-loaded input materials (read-only)
- `workspace/` — Output files (read-write)
- `memory/` — Working memory / scratch area

## Terminal (Real Bash)

Available for data processing and calculations, e.g.:
- Surgery duration estimation
- Schedule conflict analysis
- Data format conversion
