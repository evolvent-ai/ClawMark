# Tool Environment

This task runs on top of ClawMark's real environment adapters.

## Email

- Available via the bundled email skill and standard Python IMAP/SMTP libraries.
- Server:
  - IMAP: `greenmail:3143`
  - SMTP: `greenmail:3025`
- Accounts:
  - `assistant@lab.edu` (you)
  - `prof_chen@lab.edu` (Professor Mingyu Chen)
  - `admin_li@lab.edu` (Admin Li — handles administrative matters)
  - `travel@agency.cn` (travel agency)
  - `reservations@hotelringstrasse-vienna.at` (hotel)

Use email for all live communication in this task.

## Feishu / IM

- There is no live Feishu MCP in this adapted task.
- Feishu messages are delivered via the notification system.
- Respond to Admin Li via email instead.

## Notion

- Access Notion via the bundled `notion` skill.
- The framework creates a fresh page "ACL 2025 Travel Planning" with an empty inline database named `travel_planning` at Stage 0.
- Expected schema: see AGENTS.md checklist.csv spec — data about the trip is tracked here.

## Google Sheets

- Access Google Sheets via the bundled `google_sheets` skill using `/root/.google/credentials.json`.
- The framework creates one spreadsheet at Stage 0:
  - `ACL2025_Budget` — travel budget tracker
- Columns: Item | Amount (CNY) | Notes

## File System

- `/workspace/input/travel_docs/` contains all travel-related documents:
  - `acl2025_program.pdf` — conference program (10 pages)
  - `flight_booking_screenshot.png` — flight booking details
  - `hotel_confirmation.pdf` — hotel booking confirmation
  - `passport_photo.jpg` — passport biographical data page
  - `visa_checklist_screenshot.png` — Austrian Embassy visa requirements
- `/workspace/` is the writable working directory for outputs.

## Terminal / Python

- Standard Python and shell tooling are available.
- Prefer Python stdlib / lightweight parsing for CSV and text processing.

## PDF / Image Reading

- You may inspect PDF and image files through the agent's normal file-reading / multimodal capabilities.
- Do not directly modify PDF files.
