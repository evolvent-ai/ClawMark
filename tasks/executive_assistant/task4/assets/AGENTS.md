# Agents

## Language

All your outputs (CSV files, emails, Notion entries, Sheet updates) must be written in English.

## Output Specifications

### meeting_minutes.csv

The working deliverable for Stage 0 and Stage 1. Place it in `outputs/`.

**Schema** (CSV, UTF-8, comma-separated):

```csv
item_id,topic,decision,owner,due_date,status,evidence_source,notes
```

- `item_id`: Unique row identifier, e.g. `MM-001`, `MM-002`, ...
- `topic`: The discussion stream, workstream, or issue category.
- `decision`: The confirmed decision, action item, risk statement, or orphaned follow-up.
- `owner`: The responsible person or team. Leave blank only if ownership is genuinely unknown.
- `due_date`: `YYYY-MM-DD` when a deadline exists; otherwise leave blank.
- `status`: One of the following enum values only:
  - `confirmed` — decision confirmed by a decision-maker
  - `pending_confirmation` — requires further confirmation
  - `risk` — identified risk or launch blocker
  - `open` — action item assigned but not started
  - `resolved` — issue resolved or closed
  - `blocked` — blocked by a dependency
- `evidence_source`: Where this item comes from. One or more of:
  - `audio` — from the meeting recording
  - `whiteboard` — from whiteboard photos
  - `screenshot` — from projected screenshots (kanban, jira, design)
  - `slides` — from the review deck
  - `email` — from email correspondence
  - `notion` — from Notion decision log
  - `sheets` — from Google Sheets
  - `calendar` — from calendar events
  - `vp_directive` — from VP Liu's direct instruction
  - Combine with `+` if multiple, e.g. `audio+screenshot`
- `notes`: Evidence details, contradictions, confidence notes, or source-specific caveats.

Use one row per distinct decision, action item, risk item, or follow-up task. If two sources conflict, record the conflict in `notes` and set `status` to `pending_confirmation`.

### meeting_minutes_final.csv

The final Stage 2 deliverable. Place it in `outputs/` using the same schema as `meeting_minutes.csv`.

- Carry forward the latest confirmed status for each row.
- Replace outdated assumptions once later-stage confirmation arrives.
- Keep time-sensitive reminders, such as milestone changes, in the final file.

### Email Communication

- Use concise, professional English.
- Send and receive email as `liu.vp@company.com`.
- The final minutes email should clearly separate decisions, action items, and risks.
- Do not treat a proposal as an approved decision unless a decision-maker explicitly confirms it.
- Do not include sensitive personnel comments or unrelated private remarks in broad distribution emails.

### File Naming

- Place all output files in `outputs/`.
- Use snake_case names exactly as specified:
  - `meeting_minutes.csv`
  - `meeting_minutes_final.csv`
- Do not modify files in `input/`.
