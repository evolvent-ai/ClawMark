# Tools

## Email

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| hao.lin@flashbuy.com | You (Hao Lin) | Backend Developer |
| kevin.chen@flashbuy.com | Kevin Chen | Tech Lead (your manager) |

## GitHub Data (Notion)

The GitHub repository data for `shankgo-tech/shankgo-refund` is stored in a Notion database named `github_data`.

**Database**: `github_data`

**Fields**: Item Type | Number | Title | State | Labels | Body | Comments

- Use this database to view Issues, PRs, and code review records
- To create a new GitHub Issue: add a new row with Item Type = `issue`, State = `open`

## Git Repository

Local code repository at `shankgo-refund/` in the workspace.

Use `git log`, `git show`, `git diff` etc. to browse code history.

## Production Logs

GCS production error logs are available at `input/gcs_logs/`.

Files are in JSONL format. Check this directory for production error data.

## File System

- `input/prd_screenshot.png` — PRD screenshot from the product manager (read-only)
- `input/spec_template.docx` — Spec Word template (read-only)
- `input/test_cases_template.xlsx` — Test cases Excel template (read-only)
- `input/gcs_logs/` — Production error logs (read-only, may have new files added)
- `input/git_repo/` — Reference files (read-only)
- `output/` — Your output directory (read-write). Place all deliverables here.
- `shankgo-refund/` — Local Git repository (read-only for main branch)
