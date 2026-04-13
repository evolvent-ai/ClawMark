# Output Specifications

## Excel Feature Spec
- Template: `input/feature_spec_template.xlsx`
- Output: `output/feature_spec.xlsx`
- Fill-in rules are in the template's Sheet3 "Instructions"

### Key Field Enums

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `user_feedback` | `positive`, `neutral`, `issue` | `positive`=user explicitly expressed need; `neutral`=user did not specifically mention; `issue`=user reported a problem (e.g., cannot find entry point, feature malfunction) |
| `competitor_support` | `X/3` format (e.g., `2/3`) | Count of competitors (out of 3) supporting the feature. If feature not in comparison, use `0/3` |
| `priority` | `P0`, `P1`, `P2` | |
| `version` | `v2.5`, `v2.6` | `v2.5`=Phase 1 (priority P0 or P1); `v2.6`=Phase 2 (priority P2) |
| `has_data_issue` | `yes`, `no` | Whether there are data/status issues needing investigation |

### Summary Counting Rules
- `total_functions`: Total number of rows in Feature List
- `phase1_count`: Count where `version` == `v2.5`
- `phase2_count`: Count where `version` == `v2.6`
- `phase1_count` + `phase2_count` must equal `total_functions`
- `target_launch_date`: Format `YYYY-MM-DD`, from meeting minutes

## PPT Review Presentation
- Template: `input/ppt_template.pptx`
- Output: `output/product_review.pptx`
- Fill-in rules are in the notes of the first slide of the template
- Slide titles cannot be modified; only fill in the content area

## Notion Backlog
- Update feature statuses in the Notion `lingxi_backlog_q2` database when you discover issues
- Do not leave known issues unreported

## Email
- Send meeting notifications to attendees listed in the meeting minutes

## Important Principles
- Information from different sources may be inconsistent; cross-reference and use judgment
- Follow official team meeting decisions for product prioritization
- Always check the latest data in Notion and Google Sheets
