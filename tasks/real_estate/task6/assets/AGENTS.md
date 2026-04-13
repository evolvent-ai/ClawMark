# Output Specifications

**Language:** All outputs must be in English.

## `loi_comparison.csv`

Write to `outputs/loi_comparison.csv`.

| Column | Type | Description | Allowed Values |
|--------|------|-------------|----------------|
| site_id | string | Site identifier | S01, S06, S08 |
| clause | string | Clause being compared | base_rent, cam, rent_free, deposit, exclusivity, signage, exhaust, trading_hours, lease_term, fit_out, all_in_cost |
| loi_value | string | Value as stated in the LOI | free text |
| actual_value | string | Actual value after cross-checking all sources | free text |
| risk_level | enum | Risk assessment for this clause | high, medium, low, none |
| note | string | Explanation of discrepancy or risk | free text |

**Rules:**
- One row per (site_id, clause) combination
- Update existing rows when new information arrives in later stages; add new rows as needed
- `risk_level` must reflect cross-checked findings, not LOI face value
- Always cross-check: summary vs. appendix, printed text vs. handwritten amendments, stated dates vs. calculated dates

## `recommendation.csv`

Write to `outputs/recommendation.csv`.

| Column | Type | Description | Allowed Values |
|--------|------|-------------|----------------|
| site_id | string | Site identifier | S01, S06, S08 |
| recommendation | enum | Final recommendation | primary, backup, not_recommended |
| rank | integer | Priority rank (1 = best) | 1, 2, 3 |
| all_in_monthly_cost | number | All-in occupancy cost per month (RMB) | numeric |
| key_risk | string | Primary risk factor for this site | free text |

## File Rules

- Write all outputs to `outputs/`
- Use exact filenames and column names as specified above
- Do not edit files under `input/`
- Keep CSV files machine-readable with consistent column names across updates
- Do not record any LOI as "accepted" in CRM without He Feng's explicit instruction
