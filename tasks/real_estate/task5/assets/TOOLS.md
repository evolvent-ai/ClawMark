# Tools

## Available Systems

- **Email** — formal defect notices and stakeholder communication
  - xiao_an@agency.com (you)
  - he_feng@agency.com (He Feng, your manager)
  - pm@mall.com (Mall PM, landlord representative)
  - contractor@build.com (Contractor)
  - founder@shanlan.com (Shan Lan brand founder)
- **Feishu** — internal updates and brand-side progress messages
- **Notion** — CRM: site records, defect tracking, handover status (database: `handover_tracking`)
- **Google Sheets** — fire inspection schedule (sheet: `fire_inspection_schedule`)
- **Calendar** — handover date, fire re-inspection, fit-out entry plan (calendar: `s08_handover`)
- **Local file system** — `input/` (read-only evidence), `workspace/` (your deliverables)

## Working Constraints

- Treat `input/` as read-only evidence
- Write all deliverables to `workspace/`
- Do not mark handover status as "fit-out ready" unless power, drainage, fire clearance, and storefront specs are **all** confirmed
- Distinguish temporary utility connections from permanent installations — temporary does **not** satisfy fit-out entry conditions
- Do not promise the brand side an entry date without He Feng's confirmation
- Proactively check CRM, calendar, and sheets for changes — not all updates are announced
