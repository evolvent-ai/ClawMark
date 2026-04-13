# Tools

## Email

Receive internal instructions and source materials. Available mailboxes and threads:

| Mailbox / Thread | Person or Source | Role |
|------------------|------------------|------|
| project_inbox | Your working mailbox | Internal workstream inbox |
| mia_sun_thread | Mia Sun | Direct partner instructions |
| public_source_pack | Public-source assembly thread | Source packaging / benchmark build context |

## Instant Messaging (via Email)

Internal communication with your supervisor is done via email. Send messages to Mia Sun's email address listed below.

| Person | Email | Role |
|--------|-------|------|
| Mia Sun | mia.sun@research.fund | Transformation partner (your supervisor) |

**Operations**:
- Send summary and update emails to `mia.sun@research.fund`
- The notification text may include `[Feishu]` tags — treat these as messages received; respond via email

## Notion

Primary project / coverage knowledge base.

**Writable page**: `PayPal margin note`

**Writable fields**:
- `company`
- `q1_revenue_growth`
- `q1_tm_dollars`
- `mix_quality_view`
- `guide_change_view`
- `lp_followup_answer`
- `peer_frame`
- `last_updated_stage`

**Read-only pages / databases**:
- LP_questions
- peer and competitor notes for payments / fintech

**Operations**:
- Read page fields
- Update fields on `PayPal margin note`
- Read new notes in the read-only pages above

## Google Sheet

Tracker for market context and team watch items.

**Read-only tabs**:
- PaymentsConsensus
- peer_monitor

**Writable tab**: `pypl_stage_log`

**Schema** (rows appended by the agent):

```csv
stage,metric,value,unit,basis,direction,note
```

**Operations**:
- Read existing rows in the read-only tabs
- Append rows to `pypl_stage_log`

## File System

- `input/` - Pre-seeded local source materials. Treat as read-only.
- `workspace/` - Output area for all deliverables.

## Terminal

Use for local search, extraction, and light analysis of public filings, releases, transcripts, images, and structured facts.
