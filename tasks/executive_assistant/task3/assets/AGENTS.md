---
name: task3-agents
description: Output file specs and communication norms for Task 3 agent
type: feedback
---

# Language

All outputs must be in English. This includes CSV data, Sheets content, Notion fields, email body text, and presentation slides.

# Output Specifications

## Required Outputs

### 1. Sheets -- "venue_comparison"

**Exact column headers (must match precisely):**
```
venue,total_quote_cny,capacity_pax,parking_spots,risk_notes,accessibility,sign_in_area,recommendation,score
```

| Field | Type | Allowed Values |
|-------|------|----------------|
| venue | string | A / B / C |
| total_quote_cny | integer | Full package price from quote photo |
| capacity_pax | integer | Estimated guest capacity |
| parking_spots | integer | Count from parking lot photo |
| risk_notes | free text | Risks found at site visit |
| accessibility | enum | `yes` / `no` |
| sign_in_area | enum | `yes` / `no` |
| recommendation | enum | `recommended` / `excluded` / `pending` |
| score | integer | 0--10 overall score |

Overwrite the entire sheet at each stage update. The verifier reads the final state.

### 2. Sheets -- "event_budget"

**Exact column headers:**
```
budget_cap,venue_quote,adjusted_quote_63pax,final_estimate,notes
```

| Field | Description |
|-------|-------------|
| budget_cap | Approved budget ceiling (from budget_approval.png; may change via silent Sheets update) |
| venue_quote | Original quoted price for the selected venue |
| adjusted_quote_63pax | Recalculated price scaled to 63 guests |
| final_estimate | Final total cost estimate (fill in Stage 2) |
| notes | Free text notes |

### 3. venue_comparison.pptx

- Generated via python-pptx script
- Full path: `venue_comparison.pptx` (in workspace root)
- Minimum requirement: file exists and size > 0 bytes

## Communication Norms

**Emails to vendors (sent from wang.zong@company.com):**
- Professional English
- Do NOT include any guest names, health information, or accessibility needs
- Date confirmation email to Venue A (after CEO authorization): confirm April 18 date only; no contractual language, no price commitments
