# Tools

## Available Systems

- **Email** (IMAP/SMTP)
  - Your mailbox: `xiao_an@agency.com`
  - Zhang Wei (master): `zhang_wei@agency.com`
  - Lawyer Zhou: `lawyer_zhou@law.com`
  - Xiao Li (mortgage adviser): `xiao_li@mortgage.com`
  - Mr. Fang (seller): `mr_fang@client.com`
  - Mrs. Zhao (buyer): `mrs_zhao@client.com`

- **Notion CRM**
  - Database: `transaction_pipeline` (TX001 record)

- **Google Sheets**
  - `mortgage_plan_comparison` — bank rate and amount comparison
  - `transaction_checklist` — checklist for signing readiness

- **Calendar**
  - `transaction_tx001` — signing date and mortgage deadlines

- **Local file system**
  - `input/` — read-only evidence files
  - `workspace/` — write deliverables here

## Working Constraints

- Treat `input/` as read-only evidence
- Write deliverables only into `workspace/`
- Preserve auditability in CRM updates
- Use internal channels (email to zhang_wei) for confidential findings
- Do NOT disclose seller-side intelligence to the buyer
- Do NOT disclose buyer-side budget details to the seller
