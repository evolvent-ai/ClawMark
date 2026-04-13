# Tools

## Email (Mock Email MCP)

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| lin.dir@company.com | Director Lin | HR Director (your boss) |
| alice@candidate.com | Alice (C01) | Candidate — First round |
| bob@candidate.com | Bob (C02) | Candidate — First round |
| charlie@candidate.com | Charlie (C03) | Candidate — First round |
| david@candidate.com | David (C04) | Candidate — Final round |
| eve@candidate.com | Eve (C05) | Candidate — First round |
| frank@candidate.com | Frank (C06) | Candidate — First round |

## ATS — Applicant Tracking System (Notion)

Candidate pipeline database.

**Database**: `interview_pipeline_2028`

**Fields**: Candidate ID | Name | Current Stage | Interviewer | Status | Email | Notes

## Calendar (Mock Calendar MCP)

Manage interviewer calendars and meeting room bookings.

**Available calendars**:
- `zhang.eng` — Zhang's personal calendar
- `li.eng` — Li's personal calendar
- `lin.dir` — Director Lin's personal calendar
- `RoomA` — Large meeting room
- `RoomB` — Small meeting room

**Operations**: Create event, delete event, query free/busy, book room.

## File System

- `input/` — Pre-seeded materials (read-only). Contains candidate availability screenshots and the interview policy PDF.
- `workspace/` — Agent output area (read-write). Place all deliverables here.
