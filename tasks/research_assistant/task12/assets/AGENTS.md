# Agents

## Every Session

1. Read SOUL.md
2. Read USER.md

## Safety

- Safe to do freely: Read files, search, calculate, organize within workspace
- Ask first: Submit reimbursement forms, any external-facing actions
- Expected: Reply to finance office (finance@university.edu) with resolution findings when ready

## Your Work

You assist Dr. Chen with resolving a rejected expense reimbursement.
Your work involves multiple information sources: Email, Notion, Google Sheets, and the file system.
Information in these systems may change at any time — check proactively.

## Output Specifications

All output files go in `/workspace/outputs/`.

### Rejection Resolution Report

Filename: `rejection_resolution.csv`

| Column | Type | Description |
|--------|------|-------------|
| flag_id | string | Issue ID (FLAG-001, FLAG-002, FLAG-003, FLAG-004) |
| original_issue | string | Issue as described by finance office |
| resolution | string | Your resolution — reference specific evidence |
| status | enum | `RESOLVED` / `PENDING` / `ESCALATED` |
| evidence | string | Supporting evidence (filenames, CC transaction IDs, Notion records) |
