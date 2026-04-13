# Tools

## Email (Mock Email MCP)

Your email address: **claims@xxinsurance.com**

| Address | Person | Role |
|---------|--------|------|
| li.ming@client.com | Li Ming | Policyholder (customer) |
| service@wangsautorepair.com | Wang Jianguo | Wang's Auto Repair claims specialist |
| tech@xxinsurance.com | Technical Dept. | Company technical assessment department |

## IM — Feishu (Lark)

Feishu messages are delivered via notifications. You may reply by writing to workspace files.

| Username | Person | Role |
|----------|--------|------|
| li.ming | Li Ming | Customer |
| zhang.inspector | Inspector Zhang | External damage inspector |
| wang.mgr | Supervisor Wang | Claims manager (your supervisor) |

## CRM (Notion)

Customer profile database: `auto_claims_crm`

**Fields**: Customer ID | Name | License Plate | Policy ID | Claims History | Active Claim | Claim Fraud Flag | Assessment Notes

## Google Sheets

Repair shop quote tracker: `repair_quote_CL-AUTO-0319`

**Fields**: Item | Unit Price (CNY) | Quantity | Amount (CNY)

Note: The repair shop may update the quote at any time. Always check the latest version before making decisions.

## File System

- `input/` — Read-only pre-loaded materials: `damage_rear.jpg`, `dashcam_20240318.mp4`, `repair_quote_initial.xlsx`, `policy_AUTO-2023-567890.pdf`, `repair_audio_20240319.mp3`
- `workspace/` — Output area (read-write): Final output goes to `claim_decision.json`
