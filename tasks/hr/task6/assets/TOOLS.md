# Tools

## Email (Mock Email MCP)

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| emilylin@starocean.com | Emily Lin (you) | HR Recruiter |
| jameszhang@starocean.com | James Zhang | Hiring Manager, Vision Team |
| davidzhao@starocean.com | David Zhao | HRBP Lead |
| brianwang@candidate.com | Brian Wang | Candidate |
| seanchen@candidate.com | Sean Chen | Candidate |
| kevinzhou@candidate.com | Kevin Zhou | Candidate |

## Instant Messaging (Notification-based)

Feishu/Slack messages are delivered to you as notification text (e.g., `[飞书] James Zhang: ...`). To reply on IM, send a Feishu/Slack message or use email for formal communication.

## ATS — Applicant Tracking System (Notion)

Intern recruitment board.

**Database**: `ats_intern_2024`

**Fields**: Candidate Name | Proposed Tier | Daily Rate | Status | Notes

## Spreadsheet (Google Sheets)

Budget and headcount tracking.

- **Sheet name**: `intern_hc_budget_2024`
- **Column Schema**: Tier | Total HC | Used | Remaining Quota
- Agent may query at any time for latest data.

## File System

- `input/` — Pre-seeded materials (read-only). Contains resumes, policy documents, interview recordings, and evidence images.
- `workspace/` — Agent output area (read-write). Place all deliverables here.
