# Tools

## Email (Mock Email MCP)

You use the managing editor's mailbox `liu.ying@newsroom.com` to read and send emails.

| Address | Person | Role |
|---------|--------|------|
| `liu.ying@newsroom.com` | Liu Ying | Managing Editor (your master — you use this mailbox) |
| `reporter.zhao@newsroom.com` | Lao Zhao | Reporter |
| `pr@xuebagongshe.com` | Xueba Academy PR | Institution PR Department |

## CMS (Mock Notion MCP)

News article database.

**Database**: `news_db` (News Articles)

**Fields**: Title, Section, Status, Body, Confirmed Facts, Pending Verification Items

## Data Sheets (Google Sheets)

Two sheets available:

**Sheet 1**: `factcheck_edu` (Fact-Check Sheet)

Pre-populated fact_field column; agent fills in source / value / confidence / conflict / final_value / note.

**Sheet 2**: `student_data` (Student Performance Data)

Contains 120 student records with columns: student_id, course, enrolled_date, exam_date, target_score, actual_score, passed.

## File System

- `input/` — Pre-seeded materials (read-only). Contains promotional flyers, teacher certificates, business registration, contract templates, franchise data, undercover chat screenshots, and teacher profile photos.
- `workspace/` — Agent output area (read-write). Place all deliverables here.

## Terminal (Real Bash)

Data processing, pass-rate calculations, EXIF inspection, file manipulation.
