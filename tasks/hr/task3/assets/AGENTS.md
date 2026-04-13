# AGENTS — Output Specifications

## Output File Specifications

All structured outputs go to `/workspace/outputs/`.

### interview_exception_triage.csv (Stage 0)

Initial exception assessment. One row per interview.

| Column | Type | Allowed Values |
|--------|------|----------------|
| interview_id | string | `INT_2024_03_25_A`, `INT_2024_03_25_B`, `INT_2024_03_25_C` |
| candidate | string | candidate name |
| violation_type | enum | `score_conflict`, `fertility`, `process_deviation`, `discrimination`, `none` |
| risk_level | enum | `high`, `medium`, `low` |
| legal_escalation | enum | `yes`, `no` |
| note | string | brief description of the finding |

### weekly_summary.csv (Stage 2)

Weekly metrics report. One row per metric.

| Column | Type | Description |
|--------|------|-------------|
| metric | string | metric name (e.g., `total_interviews`, `exception_count`, `exception_rate_pct`) |
| value | string | metric value |

Required metrics:
- `total_interviews` — total interviews this week (23)
- `exception_count` — number of exceptions (3)
- `exception_rate_pct` — exception rate as percentage (13.0)
- `score_conflict_count` — count of score conflict violations
- `fertility_count` — count of fertility question violations
- `process_deviation_count` — count of process deviation violations
- `corrected_count` — interviews with status=corrected
- `legal_pending_count` — interviews with status=legal_pending
- `closed_count` — interviews with status=closed

## ATS (Notion) Update Requirements

**Database**: `interview_exception_2024`

### Fields
| Field | Type | Allowed Values |
|-------|------|----------------|
| Interview ID | title | `INT_2024_03_25_A`, `INT_2024_03_25_B`, `INT_2024_03_25_C` |
| Candidate | text | candidate name |
| Interviewer | text | interviewer name |
| Violation Type | select | `score_conflict`, `fertility`, `process_deviation`, `discrimination`, `none` |
| Risk Level | select | `high`, `medium`, `low` |
| Status | select | `open`, `investigating`, `corrected`, `coached`, `legal_review`, `legal_pending`, `closed` |
| Legal Escalation Required | select | `yes`, `no` |
| Root Cause | text | investigation findings |
| Notes | text | additional notes, timestamps, evidence |

### Status Workflow
- Stage 0: `open` (initial triage)
- Stage 1: A → `corrected`, B → `legal_review`, C → `coached`
- Stage 2: A → `closed`, B → `legal_pending`, C → `closed`

## Email Communication Standards

### Subject Format
`[Interview Exception] {Brief Description} - {Interview ID}`

### Templates
- **HR Manager alerts**: Concise summary + triage list + key evidence timestamps
- **Candidate responses**: Apologetic, fact-based, legally safe — no admission of subjective fault
- **Legal coordination**: Structured evidence package with specific questions and policy references
- **Interviewer coaching**: Constructive feedback with policy section citations
