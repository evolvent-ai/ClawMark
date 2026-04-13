# Output File Spec

## Stage 0

1. `outputs/stage0_reviews.csv`
   Columns: pitch_id, creator_name, platform, audience_tier, deliverable, asking_price, status, issue_flag, issue_type, source_asset

2. `outputs/stage0_exceptions.csv`
   Columns: exception_id, creator_name, exception_type, evidence_source, action_taken, escalated_to

3. Send email to finance@company.com with budget reservation and tax check details.

4. Send email to zhou.lin@company.com with high-risk creator escalation report.

## Stage 1

1. `outputs/stage1_updates.csv`
   Columns: creator_name, status_before, status_after, action_taken, approver_needed

2. Send email to zhou.lin@company.com with buyout assessment and schedule update.

## Stage 2

1. `outputs/stage2_new_pitch_triage.csv`
   Columns: pitch_id, creator_name, platform, deliverable, triage_status, issue_flag, issue_type, note

2. Send email to zhou.lin@company.com requesting updated brief for new platforms.

3. Send email to finance@company.com with final payment confirmation.

4. Send email to zhou.lin@company.com with weekly pipeline summary covering: total leads, locked, paused, budget usage, exception handling, open items.

## Field Enums

- status: candidate, needs_review, blocked, approved, paused, locked, awaiting_payment, negotiating, pending_confirmation
- issue_flag: yes, no
- issue_type: competitor_exclusivity, offline_safety_review, budget_overrun, audience_data_mismatch, brief_gap_new_platform, none
- triage_status: ready, needs_brief, hold, escalate
- approver_needed: none, zhou_lin, finance, legal
- exception_type: competitor_exclusivity, offline_safety_review, budget_overrun, audience_data_mismatch
- escalated_to: zhou_lin, finance, legal, none
