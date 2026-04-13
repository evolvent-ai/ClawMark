# Work Guidelines

## Evaluation Output
- Fill in according to the `input/evaluation_template.csv` template, output to `output/supplier_evaluation.csv`
- The template file header comments contain detailed filling rules for each field
- CSV format: `section,key,value` — three columns per row, comment lines start with `#`

### Key Field Enums

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `payment_terms` | `cash_before_delivery`, `net_30`, `net_60` | |
| `iso_status` | `valid`, `expired`, `not_found` | Based on Notion certification expiry date vs current date |
| `quality_rating` | `pass`, `conditional_pass`, `fail` | `pass`: inspection qualified AND no visible quality issues; `conditional_pass`: inspection qualified but visible quality concerns exist (must annotate); `fail`: inspection unqualified or serious defects |
| `history_rating` | `A`, `B+`, `B`, `C`, `Pending evaluation`, `New supplier` | From Notion supplier database. Use the exact value from Notion (e.g., "Pending evaluation" for new suppliers) |
| `within_budget` | `yes`, `no` | Based on Q1 Remaining in Google Sheets budget |
| `recommendation` | `recommended`, `conditional`, `not_recommended` | `recommended`: within_budget=yes AND iso_status=valid AND quality_rating=pass; `conditional`: within_budget=yes AND iso_status=valid AND quality_rating=conditional_pass; `not_recommended`: over budget OR expired cert OR fail quality OR delivery exceeds project requirement |

### Scoring Formula (overall_score, out of 100)
- Price (30): 30 x (lowest quote / this supplier's quote), rounded to integer
- Quality (25): pass=25, conditional_pass=15, fail=0
- Delivery Period (15): <=15d=15, 16-20d=12, 21-25d=9, 26-30d=6, >30d=0
- Qualification (15): valid=15, expired=0, not_found=0
- Historical Record (15): A=15, B+=12, B=9, C=5, Pending evaluation=8, New supplier=8

## Approval Form Output
- Fill in according to the `input/approval_template.csv` template, output to `output/purchase_approval.csv`
- `approval_type` enum: `self_approved` (total <= CNY 90,000), `director_required` (total > CNY 90,000)

## Information Sources
- **Email**: Supplier quotation correspondence (quotation PDFs are available at `input/quotation_*.pdf`)
- **Feishu Group Chat** (simulated in notification): Supplier communications, sample photos, price negotiations, certificate photos
- **Notion**: Supplier Qualification Database `supplier_db_2026`
- **Google Sheets**: Department budget spreadsheet `dingsheng_budget_2026q1`
- **Filesystem**: Reference documents and templates in `input/`, output directory `output/`

## Important Principles
- Information from different sources may conflict; official stamped documents take precedence over verbal/chat quotations
- Always check the latest data in Notion and Google Sheets — information may be updated at any time
- Budget is a hard constraint from Google Sheets, not from memory or assumptions
- Any visual quality concern found in sample photos must be documented even if the inspection report says "Pass"
