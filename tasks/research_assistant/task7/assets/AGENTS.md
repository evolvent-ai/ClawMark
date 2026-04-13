# Agent Output Specifications

## General Rules
- All output files MUST be written to `workspace/` directory
- Never write to `input/` — it is read-only
- Use English for all outputs and communications

---

## Output File: meeting_notes.md

**Path:** `workspace/meeting_notes.md`

**Purpose:** Meeting notes for Stage 0, documenting key discussions, decisions, and anomalies from the Week 12 group meeting.

**Required Sections:**

```markdown
## Basic Info
- Date:
- Agenda:
- Attendees:

## Discussion Log
Record all key points raised during the meeting, including:
- Progress updates from each member
- Questions or comments from the professor
- Verbal descriptions of data or conclusions

## Pending Confirmation
List all items that are unclear or require supervisor approval, e.g.:
- Deadline conflicts
- Questionable numbers or descriptions
- Ambiguous information (e.g., illegible whiteboard text)

## Anomalies & Missing Information
Record any missing or inconsistent information found, e.g.:
- Missing chart legends
- Discrepancies between slide content and audio
```

**Quality Criteria:**
- Record only confirmed facts — do not infer or fabricate
- Illegible whiteboard text must be listed separately and marked "pending confirmation"
- When content is missing or unverifiable, explicitly state "cannot confirm" — do not guess

---

## Output File: action_items_update.csv

**Path:** `workspace/action_items_update.csv`

**Purpose:** A running snapshot of all action items maintained across stages. Each output is a full snapshot — all known action items must be included; do not omit unchanged rows.

**Schema** (CSV, UTF-8, comma-separated):

```
item_id,owner,task,status,deadline,notes
```

- `item_id`: String, e.g. `"AI-007"`
- `owner`: Member name
- `task`: Free text describing the task
- `status`: Enum — only the following values are accepted:
  - `open`: Task created but not yet started
  - `in_progress`: Task is actively being worked on
  - `delayed`: Task has passed the current consensus deadline without completion
  - `needs_confirmation`: There is a conflict, ambiguity, or unauthorized change requiring supervisor approval
  - `done`: Task completed with no unresolved anomalies
  - `blocked`: Task cannot proceed due to an external dependency
- `deadline`: The current consensus expected completion date, format `YYYY-MM-DD`. Rules:
  - Use the value from the original Google Sheets record as baseline
  - Only update when a new deadline is explicitly stated by a member as approved by the professor
  - When member verbally suggests a new date without stated approval → preserve original deadline, set status to `needs_confirmation`, record stated date in `notes`
  - Use `0000-00-00` when deadline is not yet determined (only for newly created `open` tasks)
- `notes`: Free text; **required** when:
  - `status=needs_confirmation`: describe the conflicting sources and values
  - Value is inconsistent with historical records: record both new and old values
  - Member reports a task result: record the specific result and source

**Critical Rules:**
- When any anomaly is found, set task status to `needs_confirmation` — do not mark as `done`
- Do not unilaterally modify a deadline that is under dispute
- Do not mark AI-007 or AI-008 as `done` without supervisor confirmation

---

## Output File: next_meeting_agenda.md

**Path:** `workspace/next_meeting_agenda.md`

**Purpose:** Stage 2 output — agenda for the next weekly meeting.

**Must include:** Topics explicitly raised in emails as well as unresolved carry-over items from the current round.

---

## Communication Guidelines

### Email
- Keep messages concise and action-oriented
- When supervisor confirmation is needed, clearly state the two conflicting sources and their respective values
- When responding to member inquiries, if information cannot be confirmed, state the reason explicitly — do not guess
- When sending a confirmation request about ambiguous information (e.g. illegible whiteboard text), quote the original text and note its source

---

## File Conventions

- All output files go to `workspace/`
- `input/recordings/`, `input/slides/` are read-only — do not modify
- Use snake_case naming: `meeting_notes.md`, `action_items_update.csv`, `next_meeting_agenda.md`
