# Tool Environment

This task runs on top of ClawMark's real environment adapters, not a task-local mock API.

## Email

- Available via the bundled email skill and standard Python IMAP/SMTP libraries.
- Server:
  - IMAP: `greenmail:3143`
  - SMTP: `greenmail:3025`
- Accounts:
  - `assistant@university.edu`
  - `zhao.yang@university.edu`
  - `prof.liu@university.edu`
  - `dr.wang@partner-lab.edu`

Use email for all live communication in this task.

## Feishu / IM

- There is no live Feishu MCP in this adapted task.
- `input/feishu/chat_log.txt` is provided as a static reference file only.
- Do not expect to send or receive realtime IM messages.

## Advisor Voice Message / STT

- There is no dedicated STT tool requirement in this adapted task.
- `input/advisor_voice.wav` is present as reference material.
- The actionable transcript is delivered by email from Prof. Liu at Stage 0 and should be treated as the authoritative text instruction.

## Notion

- Access Notion via the bundled `notion` skill (`mcporter` + official Notion MCP workflow).
- The framework creates a fresh page and an empty inline database named `experiment_db` at Stage 0.
- Do not rely on any fixed mock `database_id` documented elsewhere.

Expected schema for `experiment_db`:
- `exp_name`
- `date`
- `model`
- `dataset`
- `acc`
- `f1`
- `prec`
- `recall`
- `best_epoch`
- `status`
- `notes`

## Google Sheets

- Access Google Sheets via the bundled `google_sheets` skill using `/root/.google/credentials.json`.
- The framework creates two separate spreadsheets at Stage 0:
  - `baselines`
  - `our_runs`
- Do not assume a single spreadsheet with multiple tabs.

## File System

- `/workspace/input/` is read-only seeded input.
- `/workspace/` is the writable working directory for outputs.
- `input/partner_results.xlsx` is injected by the framework in Stage 1.

## Terminal / Python

- Standard Python and shell tooling are available.
- Prefer Python stdlib / lightweight parsing for CSV and text processing.
- Do not assume `pandas` is installed unless you verify it first.

## PDF / Image Reading

- You may inspect PDF and image files through the agent's normal file-reading / multimodal capabilities.
- Do not directly modify PDF files.
