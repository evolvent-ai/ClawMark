## Language

All outputs must be in English -- including CSV files, press conference questions, story angle recommendations, and any other deliverables. Source materials (PDFs, audio, images) may be in any language, but your produced content must be in English.

## On Each Startup

1. Check Patricia's email inbox (newsroom@metrotribune.com) for new messages from sources, officials, or tipsters.
2. Review all materials under `input/` together with any existing draft outputs.
3. Proactively re-check the input folder -- new files may appear between stages without notification.
4. Before finalizing, verify that your CSV still reflects the latest available evidence.

## Communication Model

- You use Patricia Chen's email (newsroom@metrotribune.com) to read and send emails on her behalf.
- Patricia's messages arrive as direct notifications (not email). She sees your output directly.
- Other people email Patricia at newsroom@metrotribune.com. You read her inbox to discover their messages.
- You do NOT need to email Patricia to report findings -- she sees your workspace output directly.
- High-significance findings should be recorded in the CSV and flagged in your output.

## Safety Rules

- Never publish unverified claims as confirmed facts.
- Protect confidential source identities. Do not include anonymous tipster email addresses or real names in any output file.
- Separate facts from speculation clearly.
- Every finding should be traceable to a concrete source document, audio, or image.

## Output Formats

### `fact_check_report.csv`

This is your primary working document. Update it as new information arrives in each stage.

| Column | Description | Allowed Values / Format |
| --- | --- | --- |
| `claim_id` | Unique claim identifier | Sequential: `CLAIM-001`, `CLAIM-002`, ... |
| `source` | Who made the claim | Text (person or organization name, e.g., "Mayor Thompson", "City Press Release") |
| `claim` | The specific claim being checked | Free text |
| `category` | Type of claim | **Enum:** `financial` / `timeline` / `environmental` / `employment` / `process` / `legal` |
| `verification_status` | Fact-check result | **Enum:** `verified` / `false` / `misleading` / `unverifiable` |
| `evidence_source` | Document/source used for verification | Specific filename or source description |
| `actual_fact` | What the evidence shows (if different from claim) | Free text (leave empty if claim is accurate) |
| `discrepancy_type` | Type of issue found | **Enum:** `none` / `false` / `misleading` / `outdated` / `conflict_of_interest` / `missing_context` / `corruption` / `no_experience` |
| `significance` | News importance of this finding | **Enum:** `high` / `medium` / `low` |
| `follow_up_needed` | Required next action | **Enum:** `request_comment` / `FOIA_request` / `expert_consultation` / `none` / `legal_review` / `press_conference_question` |

**`verification_status` enum definitions:**

| Value | When to use |
| --- | --- |
| `verified` | Claim confirmed as accurate by independent source(s) |
| `false` | Claim contradicted by stronger evidence |
| `misleading` | Claim technically partially true but omits critical context |
| `unverifiable` | Cannot confirm or deny with available evidence |

**`discrepancy_type` enum definitions:**

| Value | When to use |
| --- | --- |
| `none` | No discrepancy found; claim checks out |
| `false` | Claim is factually wrong |
| `misleading` | Claim omits important context that changes its meaning |
| `outdated` | Claim was once true but circumstances have changed |
| `conflict_of_interest` | Finding reveals undisclosed conflict of interest |
| `missing_context` | Key information is withheld that the public should know |
| `corruption` | Evidence of corruption, self-dealing, or illegal activity |
| `no_experience` | Entity lacks qualifications or track record for the task |

### `press_conference_questions.md`

Prepare at least 3 specific, evidence-based questions for the mayor's press conference. Each question should:
- Reference specific evidence
- Be direct and pointed
- Follow journalistic standards

### `story_angle.md`

Recommend the primary story angle based on accumulated findings. Include:
- Main angle (nepotism/corruption/misleading public)
- Supporting evidence summary
- Key sources to cite
