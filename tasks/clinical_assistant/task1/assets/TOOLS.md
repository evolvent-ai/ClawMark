# Tools

## Email -- Gmail (Mock Gmail MCP)

You use Pharmacist Chen's email account to read and send messages. Nurse Station 3F and Dr. Zhang Wei communicate via email.

- `nurse_station_3@hospital.internal` -- Nurse Station 3F
- `zhang_cardio@hospital.internal` -- Dr. Zhang Wei, Cardiology

Messages may include file attachments (images, PDFs).

## CRM -- Notion (Mock Notion MCP)

Patient medication records and drug knowledge base.

- Database: `medication_records` -- Patient Medication Records
- Database: `drug_interactions` -- Drug Interactions Knowledge Base

Fields include: Patient ID, Name, Sex, Age, Weight, Height, Admission Date, Diagnosis, Allergy History, Electronic Orders, Lab Results, Scheduled Procedures, etc.

## Spreadsheet -- Sheets (Mock Google Sheets MCP)

- `drug_inventory` -- Drug Inventory (drug name, specification, stock quantity, stock status, restock ETA)
- `rx_review_log` -- Prescription Review Log (Date, PatientID, Prescriber, Issue Type, Issue Description, Severity, Recommended Action, Status)

## File System

- `input/` -- Pre-loaded input materials (read-only)
- Working directory -- Output files (read-write)

## Terminal (Real Bash)

Available for data processing and calculations, e.g.:
- Creatinine clearance calculation (Cockcroft-Gault formula)
- Dose conversion
- Data format conversion
