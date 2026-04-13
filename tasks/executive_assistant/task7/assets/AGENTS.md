# Agents

## Language

All outputs (CSV files, emails, Notion updates) must be in English.

## Output Specifications

### `safety_review.csv`

The Stage 0 audit deliverable. Must be placed at the workspace root.

**Schema** (CSV, UTF-8, comma-separated):

```csv
item,category,risk_type,description,severity,source_evidence,recommendation,status
```

- `item`: Program ID (e.g. N01), venue area, or logistics item being reviewed
- `category`: One of `{program, venue, logistics, catering}`
- `risk_type`: One of `{content_compliance, safety_hazard, information_leak, copyright, capacity, weather, insurance, dietary}`
- `description`: Clear statement of the issue or finding
- `severity`: One of `{low, medium, high, blocking}`
- `source_evidence`: The specific file or source where the issue was found (e.g. `rehearsal_skit.mp4`, `venue_stage.jpg`, `insurance_cert.jpg`)
- `recommendation`: Required fix, mitigation, or follow-up action
- `status`: One of `{approved, conditional_pass, pending_confirmation, pending_fix, rejected}`

### `final_safety_report.csv`

The final audit deliverable after all follow-ups. Must be placed at the workspace root.

**Schema**:

```csv
item,category,risk_type,description,severity,source_evidence,recommendation,status
```

- Reuse the same columns as `safety_review.csv`.
- Update status to reflect resolution progress, such as insurance renewed, prop replaced, or venue fixes confirmed.

### `activity_day_runsheet.csv`

The activity-day operating sheet. Must be placed at the workspace root.

**Schema**:

```csv
time_slot,program_id,program_name,owner,location,notes,contingency_plan
```

- `time_slot`: `HH:MM-HH:MM`
- `program_id`: Program ID (e.g. N01, N07 for newly added magic act)
- `program_name`: Program name or description
- `owner`: Program owner / coordinator
- `location`: Stage / indoor backup / outdoor area
- `notes`: Key setup or sequencing notes
- `contingency_plan`: Rain / safety / logistics fallback if applicable

## State Management

- Keep the Notion program review status synchronized with your latest decisions.
- When silent changes appear in Sheets, Calendar, or Notion, update the structured outputs rather than leaving them stale.

## Communication

- Use formal, concise English for all email sent from `sarah.hr@company.com`.
- Do not give external parties a false "approved" signal when a blocking risk is still unresolved.

## File Naming

- All outputs go to the workspace root directory.
- Use the exact filenames:
  - `safety_review.csv`
  - `final_safety_report.csv`
  - `activity_day_runsheet.csv`
- Do not modify files in `input/`; that directory is read-only.
