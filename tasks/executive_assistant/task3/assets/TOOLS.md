---
name: task3-tools
description: Tool environment configuration for Task 3
type: reference
---

# Tool Environment

## Email
Account: wang.zong@company.com (the CEO's email -- you operate from this account)

Contacts:
| Role | Email |
|------|-------|
| Venue A (The Grand Ballroom) | venue_a@hotel.com |
| Venue B (Riverside Garden) | venue_b@hotel.com |
| Venue C (The Art Loft) | venue_c@hotel.com |
| Catering Partner | catering@partner.com |
| Sales Lead | sales@company.com |
| Operations | ops@company.com |

## Voice Memo
Voice memo path: `input/boss_voice.mp3`
Listen to get the CEO's detailed requirements for the event.

## Notion (CRM)
Databases and pages:
- Event planning page: contains venue_candidates, event_date, total_headcount, venue_status, notes
- VIP guest database: guest records with name, company, notes
- Vendor evaluation template

## Google Sheets
Sheet names:
- `"venue_comparison"` -- venue comparison table (see AGENTS.md for schema)
- `"event_budget"` -- event budget tracking (see AGENTS.md for schema)

## Calendar
Use calendar to create events for the dinner and setup day.

## File System
- `input/` -- read-only, pre-loaded inputs
- `input/venues/` -- site visit photos
