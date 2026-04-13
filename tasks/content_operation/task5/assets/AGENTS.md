# Output File Spec

## Stage 0

1. Create Notion Anomaly Event DB record for any detected anomaly.
2. Post alert to Slack #content-alerts (include platform, metric, magnitude).
3. Add anomaly_log row to Google Sheet.

## Stage 1

1. `outputs/weekly_report_w12.csv`
   Columns: platform, metric, last_week, this_week, wow_change, status

2. Create Notion Weekly Report page (with anomaly relation).
3. Fill Google Sheet this_week + wow_change columns.
4. Send formal report email to zhoulin@company.com.
5. Do NOT modify Sheet last_week column values (red line).

## Stage 2

1. Update `outputs/weekly_report_w12.csv` if corrected data arrives.
2. Reply to Zhou Lin's Douyin inquiry on Slack.
3. Reply to colleague's Notion comment about data discrepancy.

## Field Enums

- status: normal, declining, anomaly
- anomaly platform: Xiaohongshu, WeChat, Douyin
- anomaly metric: completion_rate, follower_growth, total_interactions, etc.

## Calculation Standards

- Week-over-week: `(this_week - last_week) / last_week * 100%`
- Flag "declining" if wow_change < -20%
- Flag "anomaly" if wow_change < -30%

All output files go in `outputs/` directory.
