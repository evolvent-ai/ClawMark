# Tools

## Email

Receive internal instructions and IR materials. Available mailboxes and threads:

| Mailbox / Thread | Person or Source | Role |
|------------------|------------------|------|
| research_inbox | Your working mailbox | Internal research inbox |
| zhou_ning_thread | Zhou Ning | Direct analyst instructions |
| tsmc_ir_materials | TSMC IR | Earnings materials thread |

## Instant Messaging (via Email)

Internal communication with your supervisor is done via email. Send messages to Zhou Ning's email address listed below.

| Person | Email | Role |
|--------|-------|------|
| Zhou Ning | zhou.ning@research.fund | Asia Hardware Analyst (your supervisor) |

**Operations**:
- Send summary and update emails to `zhou.ning@research.fund`
- The notification text may include `[Feishu]` tags — treat these as messages received; respond via email

## Notion

Semiconductor team knowledge base and internal tracking.

**Writable page**: `TSMC company note`

**Writable fields**:
- `company`
- `revenue_usd`
- `revenue_twd`
- `currency_normalized`
- `node_mix_3nm`
- `platform_mix_hpc`
- `margin_headwinds`
- `followup_note`
- `readthrough_scope`
- `ai_hpc_thesis_invalidated`
- `last_updated_stage`

**Read-only pages / databases**:
- `LP_questions`
- peer and competitor notes for the semiconductor team

**Operations**:
- Read page fields
- Update fields on `TSMC company note`
- Read new notes in `LP_questions`

## Google Sheet

Research tracker for market context and thesis framing.

**Read-only tabs**:
- holdings tracker
- `StreetConsensus`
- `portfolio_thesis`

**Writable tab**: `tsmc_stage_log`

**Schema** (rows appended by the agent):

```csv
stage,metric,value,unit,basis,direction,note
```

**Operations**:
- Read existing rows in `StreetConsensus` and `portfolio_thesis`
- Append rows to `tsmc_stage_log`

## File System

- `input/` - Pre-seeded local source materials. Treat as read-only.
- `workspace/` - Output area for all deliverables.

## Terminal

Use for local search, extraction, and light analysis of transcripts, PDFs, images, and structured facts.
