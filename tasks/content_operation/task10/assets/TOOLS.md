# Tools

## Jira (via Notion)

**Database**: `incident_tickets` — Incident tickets `INC-4401` through `INC-4405`, including severity and status tracking.

## Dashboard (Google Sheet)

**Spreadsheet**: `Incident_Dashboard` — Incident timeline and status overview.

## Email

| Address | Person | Role |
|---------|--------|------|
| alex@techforward.com | You (Alex) | Your email address |
| sarah@techforward.com | Sarah | Engineering Manager |
| support@dbvendor.io | DB Vendor Support | Database vendor advisory |

## Slack

`#incident-warroom` and `#alerts` for timeline reconstruction and escalation.

## Calendar

On-call rotation and coverage checks.

**Calendar**: `oncall_rotation` — On-call engineer schedule with primary/backup assignments.

## Terminal

Use for log analysis and CSV pattern matching.

## File System

- `input/` contains seeded materials such as dashboards, logs, the bridge recording, and the runbook PDF.
- `workspace/` is the output area for `triage_summary.csv` and `postmortem_draft.md`.
- `memory/` stores source-generation artifacts that are not part of the task-facing input bundle.
