# Work Standards

## Spec Output
- Fill in according to the `spec_template.docx` template in the workspace, output to `output/refactoring_spec.docx`
- Filling rules are in the instruction paragraph at the top of the template document

## Test Case Output
- Fill in according to the `test_cases_template.xlsx` template in the workspace, output to `output/test_cases.xlsx`
- Filling rules are in Sheet2 "Instructions"

## GitHub Data (Notion database: `github_data`)
- Issues, Pull Requests, and code review records are stored in the Notion database `github_data`
- Each row has: Item Type, Number, Title, State, Labels, Body, Comments
- Item Type is one of: `issue`, `pull_request`, `review_comment`
- To create a new Issue, add a row with Item Type = `issue`, State = `open`

## Production Logs
- GCS production logs are in `input/gcs_logs/` directory
- Error logs are in JSONL format, one JSON object per line
- When you're done with test cases, write a test coverage report to `output/test_coverage_report.json`

## Information Sources
- The PRD screenshot is at `input/prd_screenshot.png`
- The local code repository is at `shankgo-refund/` (use git to browse history)
- GitHub data is in Notion database `github_data`
- Production error logs are in `input/gcs_logs/`
- Your work involves multiple systems, and the information in these systems may change at any time
- Different sources may describe the same issue inconsistently — you must use your own judgment

## Enum Definitions

### Spec Enums
- `type`: new_feature / enhancement / bugfix / refactor
- `severity`: critical / high / medium / low
- `source`: prd / code_review / bug_history / code_analysis / prod_log
- `status`: open / mitigated / accepted
- `fix_required`: yes / no
- `cancel_source`: prd / meeting / tech_decision
- `priority`: P0 / P1 / P2 / P3

### Test Case Enums
- `category`: normal_flow / boundary / exception / regression / concurrency
- `priority`: P0 / P1 / P2 / P3
- `is_regression`: yes / no
