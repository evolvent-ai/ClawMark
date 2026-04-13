# Tools

## Email (Mock Email MCP)

Your email address: **claims@xxlife.com.cn**

| Address | Person | Role |
|---------|--------|------|
| zhang.wei@client.com | Zhang Wei | Insured (client) |
| claims@rjh.com.cn | Ruijin Hospital Claims Dept | Hospital claims coordination office |

## IM — Feishu (Lark)

Feishu messages are delivered via notifications. You may reply by writing to workspace files.

| Username | Person | Role |
|----------|--------|------|
| zhang.wei | Zhang Wei | Client |
| zhang.mgr | Supervisor Zhang | Claims supervisor (your manager) |

## CRM (Notion)

Database: `med_claims_crm`

**Fields**: Customer ID | Name | Policy ID | Health Declaration | Underwriting Notes | Active Claim | Underwriting Disclosure Flag

## Google Sheets

Medical insurance reimbursement rate schedule: `med_rate_MED-2024-089234`

**Fields**: Item Type | Rate | Note

Note: Reimbursement rates may be adjusted per Article 5. Always check the latest version before calculating payout.

## File System

- `input/` — Read-only: `ecg_20240318.png`, `echo_20240319.dcm.png`, `discharge_summary.pdf`, `hospital_bill_detail.xlsx`, `policy_MED-2024-089234.pdf`, `patient_intake_audio.mp3`
- `workspace/` — Output area: write `claim_decision.json`
