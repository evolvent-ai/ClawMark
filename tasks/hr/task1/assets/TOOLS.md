# Tools

## Email

Send and receive emails.

| Address | Person | Role |
|---------|--------|------|
| mia.chen@company.com | You (Mia Chen) | Your email |
| hrbp@company.com | HRBP owner | Your direct stakeholder |

Manager email addresses are listed in `input/manager_mapping.xlsx`.

## ATS -- Intern Conversion Database (Notion)

Database: `intern_conversion_2024`

Fields:

- `Candidate ID` (title)
- `Name` (text)
- `Status` (select): Pending evaluation, Evaluated, Final decision
- `Recommendation` (select): convert, hold, reject
- `Ranking` (number): 1-5
- `Notes` (text)
- `Tags` (text)

## Feishu (IM)

Manager review audio messages are referenced in the Feishu thread `intern_conversion_reviews`.
Follow-up messages from managers appear in the notification feed.

## Spreadsheet / Workbook Access

Read-only access to local `.xlsx` files in `input/`.

Primary files:

- `input/intern_conversion_scorecard.xlsx` -- Performance scorecard (4 dimensions, 1.0-5.0 scale)
- `input/manager_mapping.xlsx` -- Candidate-to-manager mapping with contact info

## File System

- `input/` -- Source evidence only (read-only)
- `workspace/` -- Output area (read-write)
