# Agents

## Language

All outputs must be in English — including review checklists, consistency reports, email messages, and the final board deck. Source materials (PPTs, PDFs, images, audio, video) may contain Chinese content, but your produced deliverables must be in English.

## On Each Startup

1. Check Wu Zong's email inbox (wu.zong@company.com) for new messages from departments or legal.
2. Review the relevant materials under `input/` together with any existing draft outputs.
3. Proactively re-check Notion (Board Materials Repository, Finance Caliber Crosswalk), Google Sheets (KPI Summary Sheet), and Calendar for silent updates that may have occurred between stages without notification.
4. Before finalizing, verify that your working state still matches the latest environment state, because figures, legal wording, calendar times, and cover templates may change between stages.

## Output Specifications

### `review_checklist.csv`

The primary review artifact, maintained from the initial review pass onward. Place it in the current working directory.

**Schema** (CSV, UTF-8, comma-separated):

```csv
source_ppt,page,issue_type,description,severity,status
```

- `source_ppt`: Source file name, such as `sales_q1.pptx`
- `page`: Slide number or page number
- `issue_type`: One of `{data_conflict, brand_issue, security_risk, disclosure_risk, chart_issue, headcount_conflict, other}`
- `description`: Concise issue summary with the observed values or evidence
- `severity`: One of `{critical, high, medium, low}`
- `status`: One of `{open, pending_confirmation, fixed, removed, resolved, removed_from_final, accepted_with_note}`

### `data_consistency_report.csv`

The final reconciliation artifact produced during final consolidation. Place it in the current working directory.

**Schema** (CSV, UTF-8, comma-separated):

```csv
check_id,category,source_a,source_b_or_rule,observed_value_a,observed_value_b_or_rule,resolution,status
```

- `check_id`: Stable identifier such as `REV_001`
- `category`: One of `{revenue, conversion_rate, headcount, brand, legal, security, disclosure}`
- `source_a`: First source or file
- `source_b_or_rule`: Second source, policy, or authoritative rule
- `observed_value_a`: Value or observation from source A
- `observed_value_b_or_rule`: Value or rule from source B
- `resolution`: Final disposition or clarification
- `status`: One of `{resolved, escalated, removed_from_final, accepted_with_note}`

### `board_final.pptx`

The consolidated final board deck. Place it in the current working directory.

Requirements:
- Use the latest approved cover template if a newer version becomes active in a later stage.
- Align all finance-facing numbers to the latest authoritative finance update.
- Remove content that legal marks as unsuitable for board circulation.
- Ensure no deprecated logo, exposed API key, or unapproved competitive content remains.

## Communication Specifications

### Email Communication

- Use professional, executive-support style wording.
- When escalating a discrepancy, cite the exact slide, number, or source conflict.
- For finance or legal wording changes, preserve the authorized source language instead of paraphrasing from memory.
- Highlight silent changes explicitly when you discover them.
- Include exact slide references when reporting issues.

## File Naming and Placement

- Place all agent-generated deliverables in the current working directory (do not create a `workspace/` subdirectory).
- Treat `input/` as source material and `memory/` as environment context.
- The original stage-split notes are preserved under `memory/archive/` for reference only.
- Do not modify source files in `input/`.
- Use snake_case file names for generated artifacts.
