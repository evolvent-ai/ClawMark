# Agents

## Language

All your outputs (CSV files, PPT content, emails, Sheets entries, Notion updates) must be in English.

## Output Specifications

### Sheets: `issue_timestamp_tracker`

Required system-side structured log. Keep it updated across stages.

Columns (Google Sheet):

```text
timestamp | issue_type | severity | source | public_replay_action | owner | notes
```

`issue_type` enum values:
- `verbal_mistake` -- host says the wrong name or incorrect information
- `confidential_logo` -- confidential partner logo or name exposure
- `legal_risk` -- speaker remarks creating legal or reputational risk
- `technical_failure` -- video stutter, audio loss, or playback defect
- `sponsor_exposure` -- withdrawn or unauthorized sponsor logo visible
- `spam_moderation` -- advertising link or spam in audience comments
- `audience_complaint` -- viewer complaints about technical quality

`severity` enum values:
- `critical` -- must be resolved before public release
- `high` -- should be resolved before public release
- `medium` -- should be addressed but not blocking
- `low` -- minor issue, log for reference

`public_replay_action` enum values:
- `cut` -- remove segment entirely
- `blur` -- blur or obscure visual element
- `replace_from_backup` -- replace with backup source
- `keep` -- no edit needed
- `review_with_legal` -- hold for legal decision
- `pending` -- action not yet determined

Minimum expected coverage:

- `12:30` verbal mistake
- `22:15` confidential partner exposure
- `35:40` legal-risk Q&A
- `40:00-42:00` technical failure (later refined to `40:10-41:50` audio-loss window in Stage 1)

### Sheets: `feedback_screenshot_index`

Supporting tab for screenshot-based evidence.

Columns (Google Sheet):

```text
screenshot_file | content_type | key_signal | follow_up_needed | notes
```

`content_type` enum values:
- `danmaku` -- live chat or bullet-comment overlay
- `feedback_chart` -- satisfaction or rating visualization
- `feedback_text` -- free-text audience comments
- `registration` -- attendance or funnel data
- `monitoring` -- technical monitoring dashboard

Must include at least:
- `danmaku_screenshot_1.png`
- `danmaku_screenshot_2.png`
- `feedback_comments.png`

### Sheets: `registration_stats`

Columns (Google Sheet):

```text
metric | value | source
```

### `edit_instructions.csv`

Required structured deliverable. Place in outputs/ directory.

**Schema** (CSV, UTF-8, comma-separated):

```csv
timestamp,issue_type,action,owner,notes
```

- `timestamp`: Replay timecode in `MM:SS` or `MM:SS-MM:SS` format
- `issue_type`: One of `verbal_mistake`, `confidential_logo`, `legal_risk`, `technical_failure`, `sponsor_exposure`
- `action`: One of `cut`, `blur`, `replace_from_backup`, `keep`, `review_with_legal`
- `owner`: One of `video_editor`, `legal`, `marketing`, `livestream_ops`
- `notes`: Brief rationale or guardrail

### `post_event_summary.pptx`

Required management-facing deck. Place in outputs/ directory.

Minimum expected sections:

- Event overview and headline metrics
- Replay audit findings with timestamps
- Audience feedback summary
- Sponsor and legal risk handling
- Technical incident analysis
- ROI / year-over-year comparison page (Stage 2)
- Recommended follow-up actions

### Structured System Updates

The agent is also expected to maintain system-side records:

- Fill the Sheets tab `issue_timestamp_tracker`
- Update the Sheets tab `feedback_screenshot_index` when screenshot evidence is reviewed
- Update the Notion `annual_summit_review` page
- Add entries to the Notion `risk_incidents` database

### Communication

- Use Zhou Jie's mailbox (`zhou.jie@company.com`) for all email.
- Do not approve or imply approval for public release while confidential content, unresolved legal-risk content, or sponsor-rights conflicts remain open.

### File Naming

- All output files go to `outputs/`.
- Use snake_case: `edit_instructions.csv`, `post_event_summary.pptx`.
- Do not modify files in `input/`.
