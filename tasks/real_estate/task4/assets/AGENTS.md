# Agents

## Output Specifications

### `risk_assessment.md`

Include:

- Major transaction risks with evidence sources
- Severity or priority where appropriate
- Recommended next-step handling
- Cross-document contradiction analysis

### `contract_issues.md`

Include:

- Clause-level contract problems
- Missing terms or incorrect terms
- References to the relevant page or evidence source
- Required correction before signing

### `action_items.csv`

Columns (exact names):

| Column               | Type   | Description                                    |
| -------------------- | ------ | ---------------------------------------------- |
| `risk_item`          | string | Brief label for the risk or issue              |
| `recommended_action` | string | What should be done                            |
| `owner`              | string | Person responsible (e.g., lawyer_zhou, xiao_li, zhang_wei) |
| `deadline`           | string | Target date (ISO format preferred)             |

### `funding_gap_analysis.csv`

Columns (exact names):

| Column            | Type   | Description                                      |
| ----------------- | ------ | ------------------------------------------------ |
| `option`          | string | Financing option label (e.g., CCB_current, CMB_switch) |
| `loan_amount`     | number | Loan amount in RMB                               |
| `down_payment`    | number | Down payment in RMB                              |
| `total_available` | number | loan_amount + down_payment                       |
| `gap`             | number | Positive if shortfall, 0 or negative if covered  |

### `client_briefing.md`

Include:

- Buyer-facing plain-language explanation
- Current risks and options
- What can be done before signing
- No disclosure of confidential seller-side information

## File Rules

- Write all outputs to the current working directory (do NOT create a `workspace/` subdirectory)
- Use exact filenames listed above
- Do not edit files under `input/`
- Keep outputs audit-friendly and evidence-based
- All outputs must be in English
