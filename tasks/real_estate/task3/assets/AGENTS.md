# Agents

## Output Specifications

### `matching_matrix.csv`

Machine-readable matching matrix. Update this file after each stage.

| Column | Type | Description | Allowed Values |
|---|---|---|---|
| `client_id` | string | Client identifier | `Ms. Li`, `Mr. Wang`, `Zhao couple` |
| `listing_id` | string | Listing identifier | `L01` through `L09` |
| `score` | float | Match score, higher is better | `0.0` to `10.0` |
| `rationale` | string | Evidence-based matching reason | free text |

### `recommendations.md`

Human-readable recommendation summary. Update after each stage.

- Top 2-3 recommendations per client group
- Brief rationale tied to evidence (photos, data, constraints)
- Major exclusions with reason
- Viewing schedule summary

### `viewing_schedule.md`

- Proposed viewing day and time per client
- Listing-to-client-to-day mapping
- Conflict resolution notes if a preferred slot is unavailable

### `investment_analysis.csv`

Structured investment comparison for Mr. Wang.

| Column | Type | Description |
|---|---|---|
| `listing_id` | string | Listing identifier |
| `price` | string | Asking price |
| `monthly_rent` | string | Estimated monthly rent |
| `annualized_roi` | string | Annual rental yield percentage |
| `vacancy_rate` | string | Area vacancy rate |
| `decision_note` | string | Investment reasoning and recommendation |

## File Rules

- Write all outputs to `workspace/`
- Use exact filenames as specified above
- Do not edit files under `input/`
- Keep `matching_matrix.csv` machine-readable and consistent across stage updates
