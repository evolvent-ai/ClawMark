# Output File Spec

## Stage 0

1. `outputs/stage0_reviews.csv`
   Columns: content_id, title, platform, content_type, compliance_status, reject_reason, waiver_needed, issue_flag, issue_type, source_file

2. `outputs/stage0_exceptions.csv`
   Columns: exception_id, content_id, exception_type, evidence_source, action_taken, escalated_to

3. Send email to design@company.com with revision/rejection details.

4. Send email to lin.zhou@company.com with exception confirmation report.

## Stage 1

1. `outputs/stage1_updates.csv`
   Columns: content_id, status_before, status_after, action_taken, approver_needed

2. Send email to lin.zhou@company.com with waiver and schedule assessment.

## Stage 2

1. `outputs/stage2_new_content_triage.csv`
   Columns: content_id, title, platform, content_type, triage_status, issue_flag, issue_type, note

2. Send email to lin.zhou@company.com requesting updated brand guidelines.

3. Send email to design@company.com with final publication approval.

4. Send email to lin.zhou@company.com with weekly review summary covering: total reviewed, approved, rejected, exception outcomes, compliance rate, open items.

## Field Enums

- compliance_status: approved, rejected, needs_review, needs_waiver, pending_slot, locked, needs_recheck, under_review, confirmed, in_progress
- waiver_needed: yes, no
- issue_flag: yes, no
- issue_type: competitor_phrase, color_waiver_required, sensitive_title, slot_conflict, guideline_gap, none
- triage_status: ready, needs_guideline, needs_revision, escalate
- approver_needed: none, lin_zhou, design_team
- exception_type: competitor_phrase, color_waiver_required, sensitive_title, slot_conflict
- escalated_to: lin_zhou, design_team, none
