# Agents

## Output Specifications

### weekly_status.md

The primary routine deliverable, produced during the initial assessment (S0). Must be placed in `workspace/`.

**Format**:

```markdown
# Weekly Status Report — [Date]

## Student Status Overview

| Student | Project | Deadline | Status | Risk Level | Key Issues |
|---------|---------|----------|--------|------------|------------|
| ...     | ...     | ...      | ...    | ...        | ...        |

## Detailed Assessment

### [Student Name]
- **Progress**: ...
- **Issues Found**: ...
- **Action Items**: ...
- **Risk**: High / Medium / Low

## Enterprise Project
- **Milestone**: ...
- **Deadline**: ...
- **Status**: ...
- **Issues**: ...

## Action Items for Lin Fan
1. ...
2. ...
```

- Include one section per student with progress, issues, and action items.
- Include a separate section for the enterprise project.
- End with a prioritized list of items requiring Lin Fan's attention.
- Risk levels: High (deadline imminent + blocking issues), Medium (issues found but manageable), Low (on track).

### advisor_briefing.md

Urgent summary produced when Lin Fan requests a final overview (S2). Must be placed in `workspace/`.

**Format**:

```markdown
# Advisor Briefing — [Date]

## Deadline Countdown

| Student/Project | Deadline | Days Left | Status | Needs Intervention |
|-----------------|----------|-----------|--------|--------------------|
| ...             | ...      | ...       | ...    | Yes / No           |

## Critical Issues Requiring Your Decision
1. ...
2. ...

## Student-by-Student Update

### [Student Name]
- **Status**: ...
- **What was resolved**: ...
- **What remains**: ...
- **Recommendation**: ...

## Enterprise Project Update
- ...

## Recommended Priorities
1. ...
2. ...
```

- Lead with the deadline countdown table for quick scanning.
- Clearly separate "issues requiring Lin Fan's decision" from "issues being handled."
- Be action-oriented: every issue should have a recommended next step.

### Email Communication

- When pointing out paper issues to students, be specific: cite the exact table/figure/section.
- When reporting to Lin Fan, be concise and structured.

### Google Sheet Updates

- When filling in meeting_sheet action_items, use concise bullet-style entries.

### Notion Updates

- Update student_db notes with factual progress information after each stage.
- Use the notes field to record issues found, actions taken, and current blockers.
- Do NOT modify the project or stage fields based on your own judgment — only update them to reflect confirmed factual changes.

### File Naming

- All output files go to `workspace/`.
- Use snake_case: `weekly_status.md`, `advisor_briefing.md`.
- Do not modify files in `input/` — that directory is read-only.
