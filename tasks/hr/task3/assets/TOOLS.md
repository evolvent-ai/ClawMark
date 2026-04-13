# TOOLS

## Available Environments

### Email (Mock Email MCP)
| Account | Email | Role |
|---------|-------|------|
| Your account | hr-ops@xinghai.cn | HR Operations Specialist |
| HR Manager | wulei@xinghai.cn | Wu Lei |
| Legal Counsel | chenlvshi@xinghai.cn | Chen Lvshi |
| Candidate A | candidate_a@stu.edu.cn | For complaint resolution |
| Interviewer C | wang@xinghai.cn | Wang Engineer (for coaching) |

### ATS — Notion (Mock Notion MCP)
- **Database**: `interview_exception_2024`
- **Operations**: Create records, update status, add notes, track legal escalation

### File System
- **input/** — read-only materials: transcripts, score sheets, policy PDF, complaint screenshot, interview schedule
- **outputs/** — your deliverables: CSVs, reports, evidence packages

## Input Materials in input/
| File | Description |
|------|-------------|
| interview_A_transcript.txt | Interview A full transcript |
| interview_B_transcript.txt | Interview B full transcript — contains policy violation |
| interview_C_transcript.txt | Interview C full transcript — shows overtime |
| score_sheet.csv | Interview scores (also available as score_sheet.xlsx) |
| scoring_system_log.txt | Scoring system audit log — shows score entry timestamps and overrides |
| interview_schedule.csv | Schedule with durations and consent flags |
| weekly_interviews_all.csv | Full week's interview log (23 interviews, 3 flagged + 20 normal) |
| interview_policy.pdf | Company interview policy (§2.3, §4.1, §5.1, §5.2) |
| complaint_email_screenshot.png | Candidate A's complaint email screenshot |
