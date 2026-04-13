# Tools

## Email

Receive internal instructions and IR materials. Available mailboxes and threads:

| Mailbox / Thread | Person or Source | Role |
|------------------|------------------|------|
| research_inbox | Your working mailbox | Internal research inbox |
| chen_yi_thread | Chen Yi | Direct analyst instructions |
| now_ir_materials | ServiceNow IR | Earnings materials thread |

## Instant Messaging (via Email)

Internal communication with your supervisor is done via email. Send messages to Chen Yi's email address listed below.

| Person | Email | Role |
|--------|-------|------|
| Chen Yi | chen.yi@research.fund | U.S. Software Analyst (your supervisor) |

**Operations**:
- Send summary and update emails to `chen.yi@research.fund`
- The notification text may include `[Feishu]` tags — treat these as messages received; respond via email

## Notion

Software team knowledge base and internal tracking.

**Writable page**: `ServiceNow company note`

**Writable fields**:
- `company`
- `subscription_growth_reported`
- `subscription_growth_constant_currency`
- `q2_vs_street_direction`
- `genai_signal`
- `guide_bridge`
- `relative_resilience`
- `last_updated_stage`

**Read-only pages / databases**:
- `LP_questions`
- competitor and peer notes for the software team

**Operations**:
- Read page fields
- Update fields on `ServiceNow company note`
- Read new notes in `LP_questions`

## Google Sheet

Research tracker for sector context and peer positioning.

**Read-only tabs**:
- holdings tracker
- `StreetConsensus`
- `software_comp`

**Writable tab**: `now_stage_log`

**Schema** (rows appended by the agent):

```csv
stage,metric,value,unit,basis,direction,note
```

**Operations**:
- Read existing rows in `StreetConsensus` and `software_comp`
- Append rows to `now_stage_log`

## File System

- `input/` - Pre-seeded local source materials. Treat as read-only.
- `workspace/` - Output area for all deliverables.

## Terminal

Use for local search, extraction, and light analysis of transcripts, PDFs, HTML files, images, and structured facts.
