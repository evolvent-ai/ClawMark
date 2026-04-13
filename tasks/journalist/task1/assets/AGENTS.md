## Language

All outputs must be in English — including CMS drafts, fact-check sheet entries, CSV files, evening summaries, and any other deliverables. Source materials (PDFs, audio, video) may be in Chinese, but your produced content must be in English.

## On Each Startup

1. Check the managing editor's email inbox (liu.ying@newsroom.com) for new messages from the reporter or external contacts.
2. Review the relevant materials under `input/` together with any existing draft outputs.
3. Proactively re-check the fact-check sheet — new rows may appear between stages without notification.
4. Before finalizing, verify that your draft still matches the latest shared source state, because facts and supporting materials may change between stages.

## Safety Rules

- Unverified casualty numbers must not appear in headlines or leads.
- Eyewitness shouts or single-source rumors must stay marked as unverified until an official or cross-checked source confirms them.
- Images or videos from uncertain origin must not be used in the article.
- Protect anonymous-source identity in every outward-facing output (CMS body, workspace files). Never include tipster email addresses or names.
- Every confirmed statement should be traceable to a concrete source file, sheet row, or official message.

## Output Formats

### `conflict_report.csv`

All columns are required. Every row must have non-empty `source_a` and `source_b`.

| Column | Description | Allowed Values / Example |
| --- | --- | --- |
| `conflict_id` | Unique conflict ID | `C001`, `C002`, ... |
| `fact_field` | The fact in dispute | `起火时间`, `伤亡人数`, `起火楼层` |
| `source_a` | First source (must be a specific filename, tool, or person) | `witness_video.mp4`, `interview_1.wav` |
| `value_a` | Claim from source A | `14:20` |
| `source_b` | Second source (must be a specific filename, tool, or person) | `official_bulletin.pdf` |
| `value_b` | Claim from source B | `14:35接警` |
| `resolution_type` | How this conflict is handled | **Enum:** `official_prevails` / `pending_verification` / `sources_reconciled` / `rejected` |
| `resolution` | Explanation of the resolution | `区分冒烟时间与接警时间，两者不矛盾` |

**`resolution_type` enum definitions:**

| Value | When to use |
| --- | --- |
| `official_prevails` | Official source (bulletin, briefing) overrides rumor or unverified claim |
| `pending_verification` | Neither source can be confirmed yet; hold for follow-up |
| `sources_reconciled` | The two values are not actually contradictory once context is understood (e.g., smoke time vs alarm time) |
| `rejected` | One source is determined to be false, fabricated, or unrelated |

### `evening_summary.md`

Keep the summary concise and structured. Must include all four sections:

1. **Confirmed timeline** — the final reconstructed sequence of events with timestamps
2. **Confirmed casualty wording** — the official final wording on injuries
3. **Rejected or risky materials** — materials excluded from the article and why
4. **Follow-up angles** — investigative leads for deep reporting

### CMS News Draft (`news_db`)

Create or update one record in `news_db` with:

| Field | Description |
| --- | --- |
| `title` | Headline (must not contain unverified claims) |
| `section` | `突发` |
| `status` | `draft` / `updated` / `final` |
| `body` | Article body text |
| `confirmed_facts` | Bullet list of verified facts with source attribution |
| `pending_verification_items` | Items still awaiting confirmation |

### Fact-Check Sheet (`factcheck_001`)

Fill each pre-seeded row using these columns:

| Column | Description | Allowed Values |
| --- | --- | --- |
| `source` | Where this fact comes from | Specific filename or source name |
| `value` | The raw value from the source | Free text |
| `confidence` | How reliable this value is | **Enum:** `High` / `Medium` / `Low` |
| `conflict` | Description of any conflict with other sources (empty if none) | Free text |
| `final_value` | The confirmed final value after cross-verification | Free text (must be non-empty for completed rows) |
| `note` | Additional context or caveats | Free text |
