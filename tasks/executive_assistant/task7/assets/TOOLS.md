# Tools

## Email

You operate Sarah's inbox (`sarah.hr@company.com`). All external parties and colleagues email this address. You read incoming mail and send replies from it.

| Address | Person / Org | Role |
|---------|---------------|------|
| sarah.hr@company.com | You (Sarah's assistant, operating as Sarah) | Your outbound identity |
| ops@greenfieldvenue.com | Greenfield Venue Operations | Venue operations |
| coverage@assureevents.com | Harbor Event Assurance | Event insurance |
| service@harborcatering.com | Harbor Catering | Catering support |

## CRM / Notion

Program review and event-planning records.

- **Database**: `team_building_program_review`
- **Fields**: Program ID | Type | Owner | Review Status | Risk Flags | Notes
- **Reference page**: Event prep page for the team-building event
- **Policy material**: `policy_scan.jpg` (uploaded scan of the event safety policy)

## Google Sheets

- Program schedule sheet
- Supplies checklist
- Registration / attendance sheet

These sheets may change silently during the task and must be re-checked.

## Calendar

Tracks:

- Venue setup schedule
- Rehearsal schedule
- Team-building event day

Silent changes to setup windows matter because they affect safety fixes and technical readiness.

## File System

- `input/`: read-only seeded materials such as rehearsal videos, venue photos, screenshots, and certificates
- `workspace/`: read-write output area for audit deliverables

## Python

Use for headcount, dietary-needs, and logistics calculations when needed.
