# Tools

## Email

Send and receive emails.

| Address | Person | Role |
|---------|--------|------|
| lena@company.com | You (Lena Guo) | Your email address |
| hrbp@company.com | HRBP Owner | Your manager, primary stakeholder |
| hrvp@company.com | HR VP | Escalation target for org-stability risks |

## ATS — Organization Placement Database (Notion)

**Database**: `org_restructuring_placement_2024`

| Field | Type | Description |
|-------|------|-------------|
| Employee ID | title | E01-E04 |
| Employee Name | rich_text | Full name |
| Original Role | select | Pre-merger role |
| Target Role | rich_text | Post-merger recommended role |
| Placement Status | select | Pending placement evaluation / recommended / alternate_placement / retain |
| Risk Level | select | low / medium / high |
| Notes | rich_text | Structured rationale and flags |
| Tags | multi_select | Business-priority tags (e.g., critical_talent_retention) |
| Attrition Risk | select | none / green / yellow / red |

## Instant Messaging (Feishu) — Notification Only

Feishu messages are delivered as text notifications; there is no Feishu MCP tool to call. Manager and employee messages will appear directly in your task notifications. Audio attachments from Feishu are saved to `input/`.

## File System

- `input/` -- Source evidence only (read-only). Contains org charts, employee workbook, policy PDF, manager audio.
- `workspace/` -- Output area (read-write). Place `placement_plan.json` here.
