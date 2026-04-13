# Tool Environment

This task runs on top of ClawMark's real environment adapters, not a task-local mock API.

## Email

- Available via the bundled email skill and standard Python IMAP/SMTP libraries.
- Server:
  - IMAP: `greenmail:3143`
  - SMTP: `greenmail:3025`
- Accounts:
  - `assistant@lab.edu` (you)
  - `prof_chen@lab.edu` (Prof. Chen Mingyu)
  - `zhao@lab.edu` (Zhao, PhD student)
  - `li_ming@lab.edu` (Li Ming, senior PhD student)
  - `wang@lab.edu` (Wang, Master's student)

Use email for all live communication in this task.

## Feishu / IM

- There is no live Feishu MCP in this adapted task.
- All communication that would go through Feishu in the original scenario is handled via email instead.
- When the task mentions "Feishu message," treat it as email communication.

## Audio / STT

- There is no dedicated STT tool in this adapted task.
- Audio clip transcripts are delivered via email from Prof. Chen at Stage 0.
- The `.m4a` audio files remain as reference material in `input/recordings/`.

## Notion

- Access Notion via the bundled `notion` skill.
- The framework creates a fresh page and inline databases at Stage 0.
- Databases:
  - `action_items` — for action item tracking

Expected schema for `action_items`:
- `item_id` (title)
- `owner`
- `task`
- `status` (select: open, in_progress, delayed, needs_confirmation, done, blocked)
- `deadline`
- `notes`

## Google Sheets

- Access Google Sheets via the bundled `google_sheets` skill using `/root/.google/credentials.json`.
- The framework creates one spreadsheet at Stage 0:
  - `progress_tracker` — task status and deadlines for each member

## File System

- `/workspace/input/` is read-only seeded input.
- `/workspace/` is the writable working directory for outputs.
- `input/recordings/` contains audio clips and whiteboard photo.
- `input/slides/` contains the meeting slides PDF.
- Files may be injected by the framework in later stages.

## PDF / Image Reading

- You may inspect PDF and image files through the agent's normal file-reading / multimodal capabilities.
- The slides PDF contains 4 pages with experiment results, action items, learning curves, and timeline.
- The whiteboard photo contains handwritten notes that must be visually inspected.
