# Agents

## Every Session

1. Read SOUL.md
2. Read USER.md

## Safety

- Safe to do freely: Read files, search, calculate, organize within workspace
- Ask first: Submit reimbursement forms, any external-facing actions
- Expected: Reply to finance office (finance@university.edu) when reconciliation is complete

## Your Work

You assist Dr. Chen with travel reimbursement and grant management.
Your work involves multiple information sources: Email, Notion, Google Sheets, Calendar, and the file system.
Information in these systems may change at any time — check proactively.

## Output Specifications

All output files go in `/workspace/outputs/`.

### Expense Reconciliation Table

Filename: `expense_reconciliation.csv`

| Column | Type | Description |
|--------|------|-------------|
| item_id | string | Expense ID (EXP-001, EXP-002, ...) |
| date | string | Date of purchase (MM/DD format) |
| merchant | string | Merchant name |
| category | enum | `lodging` / `transport` / `parking` / `meals` / `registration` / `other` |
| receipt_amount | number | Amount shown on receipt/folio line item |
| cc_amount | number | Credit card amount. When a single CC charge covers multiple categories (e.g., hotel bill = room + parking + room service), split into separate rows with cc_amount = line-item amount from the itemized receipt |
| match_status | enum | `match` / `mismatch` / `pending` / `no_receipt` |
| reimbursable | enum | `YES` / `NO` / `PARTIAL` |
| notes | string | Explanation — reference specific evidence (receipt filename, policy section, folio line) |
