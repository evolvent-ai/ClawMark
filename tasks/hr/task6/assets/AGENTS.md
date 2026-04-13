# Agents

## Output Specifications

### rating_proposal.csv

The primary deliverable for Stage 0. Must be placed in `workspace/`.

**Schema** (CSV, UTF-8, comma-separated):

```
candidate,recommended_tier,daily_rate,rationale
```

| Column | Type | Allowed Values |
|--------|------|---------------|
| `candidate` | string | Full name (e.g., "Brian Wang") |
| `recommended_tier` | enum | `A`, `A+`, `S`, `S-Pending`, `Rejected` |
| `daily_rate` | integer | CNY/day (0 if Rejected) |
| `rationale` | string | Brief English justification (1-2 sentences) |

### final_status_report.md

End-of-task summary placed in `workspace/`. Must include:

1. A status section for each candidate (Brian Wang, Sean Chen, Kevin Zhou)
2. Current tier, rate, and approval status
3. Outstanding action items or compliance holds
4. Risk flags and recommendations

### Email Communication

- Use formal, professional English.
- Subject lines should be descriptive: e.g., "Intern Tiering Proposal — 3 Candidates" or "Compliance Hold: Brian Wang Tripartite Agreement".
- Always CC relevant parties (HRBP for escalations, HM for tier decisions).

### IM (Feishu/Slack) Communication

- Keep messages concise and action-oriented.
- Use for quick syncs; follow up with email for anything requiring documentation.

### File Naming

- All output files go to the current working directory (`/workspace`). Do NOT create a `workspace/` subdirectory — you are already in `/workspace`.
- Use snake_case: `rating_proposal.csv`, `final_status_report.md`.
- Do not modify files in `input/` — that directory is read-only.
