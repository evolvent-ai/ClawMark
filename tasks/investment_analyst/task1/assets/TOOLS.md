# Tools

## Email

Receive internal instructions and IR materials. Available mailboxes and threads:

| Mailbox / Thread | Person or Source | Role |
|------------------|------------------|------|
| research_inbox | Your working mailbox | Internal research inbox |
| li_chen_thread | Li Chen | Direct analyst instructions |
| jpm_ir_distribution | JPMorgan Chase IR | Earnings materials thread |

## Instant Messaging (via Email)

Internal communication with your supervisor is done via email. Send messages to Li Chen's email address listed below.

| Person | Email | Role |
|--------|-------|------|
| Li Chen | li.chen@research.fund | U.S. Banks Analyst (your supervisor) |

**Operations**:
- Send summary and update emails to `li.chen@research.fund`
- The notification text may include `[Feishu]` tags — treat these as messages received; respond via email

## Notion

Bank team knowledge base and internal tracking.

**Writable page**: `JPM watchlist`

**Writable fields**:
- `company`
- `reported_net_income`
- `adjusted_net_income`
- `difference_driver`
- `fy24_nii_ex_markets`
- `street_view`
- `lp_followup_answer`
- `peer_frame`
- `last_updated_stage`

**Read-only pages / databases**:
- `LP_questions`
- peer and competitor notes for the bank group

**Operations**:
- Read page fields
- Update fields on `JPM watchlist`
- Read new notes in `LP_questions`

## Google Sheet

Research tracker for market context and team watch items.

**Read-only tabs**:
- holdings tracker
- `StreetConsensus`
- `peer_monitor`

**Writable tab**: `jpm_stage_log`

**Schema** (rows appended by the agent):

```csv
stage,metric,value,unit,basis,direction,note
```

**Operations**:
- Read existing rows in `StreetConsensus` and `peer_monitor`
- Append rows to `jpm_stage_log`

## File System

- `input/` - Pre-seeded local source materials. Treat as read-only.
- `workspace/` - Output area for all deliverables.

## Terminal

Use for local search, extraction, and light analysis of transcripts, PDFs, images, and structured facts.
