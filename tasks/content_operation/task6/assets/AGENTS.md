# Agents

## Output Specifications

### settlement.csv

Campaign settlement report. Must be placed in `workspace/`.

**Schema** (CSV, UTF-8, comma-separated):

```
username,shares,comments,metrics_met,qualification,gross_award,tax,net_award,notes
```

- `username`: Participant username
- `shares`: Number of shares/forwards
- `comments`: Number of comments
- `metrics_met`: Whether quantitative thresholds are met (yes / no) — purely based on shares >= 100 AND comments >= 50
- `qualification`: Final qualification status considering all rules (qualified / disqualified / not_qualified)
  - `qualified`: Metrics met AND all other rules satisfied
  - `not_qualified`: Metrics NOT met (regardless of other factors)
  - `disqualified`: Metrics met BUT violated other rules (employee, non-brand product, etc.)
- `gross_award`: Gross award amount (¥200 for qualified, ¥0 otherwise)
- `tax`: Tax amount
- `net_award`: Net award amount
- `notes`: Reason for disqualification or other remarks

### Communication Standards

- **Slack #finance**: Use for payment requests and tax clarification inquiries.
- **Slack #marketing**: Use for campaign status updates and escalations to Chen Xi.
- **Telegram**: Use for individual participant communication. Never include other participants' information.
- **Email**: Use for formal settlement reports to Chen Xi.

### File Naming

- All output files go to `workspace/`.
- Settlement file: `settlement.csv`.
- Do not modify files in `input/` — that directory is read-only.
