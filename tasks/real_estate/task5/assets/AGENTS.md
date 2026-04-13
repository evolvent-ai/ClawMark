# Agents

## Language

All outputs must be in English.

## Output Specifications

### `handover_defects.csv`

| Column | Type | Description |
|--------|------|-------------|
| item | string | Short defect name (e.g., "Power shortfall") |
| category | enum | `power` / `drainage` / `storefront` / `fire_safety` / `structural` / `visual_defect` / `ventilation` / `water_supply` |
| promised | string | What was promised or expected (leave blank if not applicable) |
| actual | string | What was found on site |
| evidence | string | Source document or photo filename (e.g., "MEP_drawings.pdf", "storefront_photo.jpg") |
| severity | enum | `critical` / `high` / `medium` / `low` |
| owner | string | Responsible party (e.g., "landlord", "contractor", "fire_department") |
| status | enum | `open` / `in_progress` / `resolved` / `blocked` |
| deadline | string | Expected resolution date (YYYY-MM-DD) |

### `escalation_summary.md`

Include:

- Summary of all open defects grouped by severity
- Blockers preventing fit-out entry
- Responsible party and expected resolution date for each item
- Current fire inspection status and timeline risk
- Recommendation on whether fit-out entry is possible

## File Rules

- Write all outputs to `workspace/`
- Use exact filenames as specified above
- Do not edit files under `input/`
- Keep `handover_defects.csv` machine-readable and consistent across updates
- Do not update CRM handover status to "fit-out ready" unless all hard blockers are resolved
