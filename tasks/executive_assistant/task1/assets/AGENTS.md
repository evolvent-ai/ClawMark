---
name: task1-agents
description: Output file specs and communication norms for Task 1 agent
type: feedback
---

## Language
All outputs must be in English.

# Output Specifications

## Required Outputs

### 1. expense_report.csv

**Exact column headers (must match precisely):**
```
date,merchant,amount,category,status,payment_method,source_file,notes
```

| Field | Type | Allowed Values / Notes |
|-------|------|------------------------|
| date | string | YYYY-MM-DD format |
| merchant | string | Merchant name as shown on receipt (transliterate Chinese merchants to English or pinyin) |
| amount | float | Amount in CNY, no currency symbol, e.g. 553.00 |
| category | enum | `transportation` / `accommodation` / `dining` / `entertainment` / `office` / `other` |
| status | enum | `pending_review` / `compliant` / `rejected` / `needs_supplement` / `approved` |
| payment_method | enum | `wechat` / `alipay` / `cash` / `bank_card` / `unknown` |
| source_file | string | Source filename exactly, e.g. `receipt_01.png` |
| notes | string | Anomalies, rejection reasons, cross-reference findings, follow-up items |

**Rules:**
- One row per valid expense entry
- Excluded items (non-receipts like supermarket.PNG, hotel.PNG; personal consumption like spa_receipt.png; audio recordings; memos; dinner scene photos used as evidence) must NOT appear as rows
- Update this file in place across all stages; the verifier reads the final state
- Do NOT use `workspace/` prefix in the file path. Write directly to `expense_report.csv`.

### 2. weekly_summary.csv

**Exact column headers (must match precisely):**
```
metric,value,detail
```

| Field | Type | Notes |
|-------|------|-------|
| metric | string | Metric name (see required metrics below) |
| value | string | Numeric or text value |
| detail | string | Additional context or breakdown |

**Required metric rows (at minimum):**
- `total_reimbursable` — Total approved reimbursement amount in CNY
- `total_items` — Number of approved expense line items
- `rejected_count` — Number of rejected items
- `rejected_items` — List of rejected items with reasons
- `pending_count` — Number of items still pending
- `transportation_subtotal` — Transportation category subtotal
- `accommodation_subtotal` — Accommodation category subtotal
- `dining_subtotal` — Dining category subtotal
- `entertainment_subtotal` — Entertainment category subtotal
- `office_subtotal` — Office category subtotal
- `budget_status` — Summary of budget remaining per category

Do NOT use `workspace/` prefix in the file path. Write directly to `weekly_summary.csv`.

## Communication Norms

**Email to Finance (finance@company.com) -- sent from li.ming@company.com:**
- Subject line should include: Li Ming, Beijing trip, reimbursement
- Include: total amount, number of items, list of categories
- Do NOT include policy debates; just the facts and amounts

**Email to Manager (manager@company.com) -- sent from li.ming@company.com:**
- Use when requesting approval for no-receipt claims not exceeding CNY 100
- State: date, item, amount, reason receipt is unavailable

## Notion Database: expense_db

**Schema:**

| Field | Type | Allowed Values |
|-------|------|---------------|
| Item | title | Description of the expense item |
| Date | rich_text | YYYY-MM-DD |
| Merchant | rich_text | Merchant name |
| Amount | number | CNY amount |
| Category | select | `transportation` / `accommodation` / `dining` / `entertainment` / `office` / `other` |
| Status | select | `pending_review` / `compliant` / `rejected` / `needs_supplement` / `approved` |
| Payment Method | select | `wechat` / `alipay` / `cash` / `bank_card` / `unknown` |
| Notes | rich_text | Cross-reference notes, anomalies |
| Attachment | rich_text | Source filename |

## Google Sheets: budget_tracking

**Column headers:**
```
category,budget,used,remaining
```

Budget data must be populated from `budget_dashboard.PNG` image. Update `used` and `remaining` as expenses are processed. Check for silent updates each stage.
