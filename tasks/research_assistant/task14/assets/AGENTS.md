# Agents

## Safety

- Safe to do freely: Read files, search, calculate, compare prices
- Ask first: Approve purchases, submit orders, email vendors directly
- Expected: Reply to procurement office (procurement@university.edu) with review findings when complete

## Output Specifications

All output files go in `/workspace/outputs/`.

### Procurement Review Report

Filename: `procurement_review.csv`

| Column | Type | Description |
|--------|------|-------------|
| request_id | string | Request ID (REQ-001 through REQ-005) |
| item_desc | string | Item description |
| vendor | string | Vendor name |
| quoted_price | number | Vendor quoted price (total) |
| market_price | number | Market reference **unit** price (from Amazon/other sources). Use per-unit price, not total. 0 if not available |
| grant | enum | `NSF` / `DARPA` |
| policy_check | enum | `compliant` / `non_compliant` / `needs_review` |
| issue_type | enum | `none` / `overpriced` / `duplicate` / `conflict_of_interest` / `budget_overrun` / `contract_violation` / `compliance_flag` |
| recommendation | enum | `approve` / `reject` / `negotiate` / `escalate` |
| notes | string | Justification and evidence references |
