# Working Guidelines

## Output File
- Fill in the `release_plan_template.json` template found in the workspace
- Output to `workspace/output/release_plan.json`

## Tool Usage
- Email: Receive materials from external parties / management; send confirmation emails to VP
- Feishu: View audio and image messages in the project group chat
- Notion: Query and update the `product_backlog` database
- Google Sheets: Query `release_capacity_q2`
- Google Calendar: Create or update version milestones

## Scheduling and Decision Rules
- Date format: `YYYY-MM-DD`
- Business-day calculation excludes only Saturdays and Sundays
- Default admission rule: features with `priority_score >= 6.0` may enter the current version
- When a quantitative score conflicts with an explicit decision from a "more recent and higher authority" source, the latter takes precedence
- Decision priority order: VP explicit annotation / current-week management decision > current-week review meeting conclusion > stale system fields
- If an override occurs, the original score must be preserved in the JSON, and the reason must be stated in `reason` or `constraints_applied`

## Information Sources
- Information from different sources may have time lags or inconsistencies; you must judge on your own
- Information in these systems may change in subsequent stages
