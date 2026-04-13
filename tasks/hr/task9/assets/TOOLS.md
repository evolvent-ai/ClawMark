# Tools

## Email (Mock Email MCP)

Send and receive emails. All communication — including what would normally go through instant messaging — is handled via email in this environment.

| Address | Person | Role |
|---------|--------|------|
| `xiao.chen@starocean.cn` | Xiao Chen (you) | HR Onboarding Specialist |
| `wang.hr@starocean.cn` | Manager Wang | HR Manager |
| `zhao.ming@personal.com` | N01 Zhao Ming | Candidate — Backend Engineer |
| `li.wei@personal.com` | N02 Li Wei | Candidate — Product Manager |
| `wang.hao@personal.com` | N03 Wang Hao | Candidate — Sales Manager |
| `zhang.xue@personal.com` | N04 Zhang Xue | Candidate — Financial Analyst |
| `chen.lei@personal.com` | N05 Chen Lei | Candidate — Operations Engineer |
| `prev_employer_hr@techcorp.com` | Archived former-employer HR contact | Reference only; do NOT initiate contact |
| `legal@starocean.cn` | Legal team | Internal escalation recipient |
| `zhang.it@starocean.cn` | IT Engineer Zhang | IT account setup, equipment |
| `li.admin@starocean.cn` | Admin Coordinator Li | Desk arrangement, facilities |

## HRIS — Onboarding Database (Mock Notion MCP)

New-hire onboarding database with 5 employee records.

**Fields**: employee_id | name | position | onboarding_status | documents_checklist | notes

Check this database regularly — it may be updated silently by other departments.

## Calendar (Mock Calendar MCP)

Calendar name: `StarOcean HR`. Used for orientation scheduling and IT account setup slots.

## File System

- `/workspace/input/` — Pre-seeded materials (read-only): resumes, ID cards, degree certificates, health reports, resignation certificates, non-compete agreements, policy documents, and audio transcripts.
- `/workspace/` — Agent output area (read-write). Place CSV files and reports here.
