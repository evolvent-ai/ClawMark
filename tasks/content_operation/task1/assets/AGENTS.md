# Output File Spec

All output files go to `workspace/outputs/`. Use UTF-8, comma-separated CSV.

## Stage 0

### 1. `outputs/stage0_requests.csv`

The primary intake record. One row per input file in `design_requests/`.

**Schema:**
```
request_id,date,platform,request_type,budget_estimate,status,issue_flag,issue_type,source_file
```

- `request_id`: `REQ-YYYYMMDD-NN` — number matches the source filename (e.g. `REQ-20250318-01` for `req_20250318_01_xhs_cover.png`)
- `date`: `YYYY-MM-DD` extracted from the screenshot; `TBD` if missing
- `platform`: platform name as shown in the screenshot; `TBD` if missing
- `request_type`: e.g. `Cover`, `Banner`, `Card`, `Poster`, `Thumbnail`, `Popup`, `KV`
- `budget_estimate`: integer (CNY); `0` if missing
- `status`: one of {`ready`, `needs_clarification`, `blocked`}
- `issue_flag`: one of {`yes`, `no`}
- `issue_type`: one of {`brand_color_conflict`, `slot_conflict`, `budget_overrun`, `brief_missing_fields`, `none`}
- `source_file`: exact filename from `design_requests/` (e.g. `req_20250318_09_dark_mockup.png`)

Must contain **12 rows**. Rows with issues must have `status` ≠ `ready` and `issue_flag` = `yes`.

### 2. `outputs/stage0_exceptions.csv`

One row per detected exception.

**Schema:**
```
request_id,issue_type,evidence_source,escalated_to,resolution
```

- `request_id`: matches `stage0_requests.csv`
- `issue_type`: same enum as above
- `evidence_source`: where the evidence was found (e.g. `brand_guidelines.pdf section 4`, `calendar_week12_v3.png`, `Q1_Content_Budget row 1`)
- `escalated_to`: one of {`zhao_yue`, `design_team`, `finance`, `none`}
- `resolution`: one of {`pending_approval`, `blocked`, `needs_info`}

### 3. Emails (must actually send, not just write files)

- Send formal design request email to `design@company.com` listing the actionable requests
- Send exception report email to `zhao.yue@company.com` listing all exceptions with evidence and recommended actions

## Stage 1

### 1. `outputs/stage1_updates.csv`

One row per field change made during this stage.

**Schema:**
```
request_id,field_changed,old_value,new_value,reason
```

- `request_id`: the record being modified
- `field_changed`: which field (e.g. `date`, `status`)
- `old_value`: value before change
- `new_value`: value after change
- `reason`: brief English explanation

### 2. Email

- Reply to `zhao.yue@company.com` with color approval decision and budget risk assessment

## Stage 2

### 1. `outputs/stage2_summary.csv`

Weekly summary as key-value pairs.

**Schema:**
```
metric,value
```

Required metrics:
- `total_requests` — total intake count
- `ready_count` — requests in ready state
- `blocked_count` — requests in blocked state
- `delivered_count` — requests in delivered state
- `needs_clarification_count` — requests pending info
- `total_budget_spent` — total CNY amount
- `exceptions_resolved` — count of resolved exceptions
- `open_items` — count of unresolved items

### 2. Email

- Send weekly status summary to `zhao.yue@company.com`

## Field Enums

- `status`: {`ready`, `needs_clarification`, `blocked`, `approved`, `in_progress`, `delivered`}
- `issue_flag`: {`yes`, `no`}
- `issue_type`: {`brand_color_conflict`, `slot_conflict`, `budget_overrun`, `brief_missing_fields`, `none`}
- `escalated_to`: {`none`, `zhao_yue`, `design_team`, `finance`}

## Email Communication

- Use formal, clear, action-oriented English
- Exception emails to Zhao Yue must lead with the conclusion and list risks separately
- Design team emails must include actionable request details (platform, size, due date, budget)
- Never approve over-budget or non-compliant work without Zhao Yue's explicit approval

## File Naming

- All output files go to `workspace/outputs/`
- Do not modify files in `design_requests/` or `ref/` — those directories are read-only
