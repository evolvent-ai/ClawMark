# Agents

## Output Specifications

### conversion_summary.json

Primary deliverable. Must be placed in the current working directory (i.e. `./conversion_summary.json`).

**Schema**:

```json
[
  {
    "candidate_id": "I01",
    "recommendation": "convert",
    "ranking": 1,
    "risk_flags": [],
    "drop_reason": ""
  }
]
```

- `candidate_id`: One of `{I01, I02, I03, I04, I05}`
- `recommendation`: One of `{convert, hold, reject}`
  - In the final HC-constrained result, exactly 3 candidates should be `convert`
- `ranking`: Integer `1-5`, unique across all 5 candidates
- `risk_flags`: Array of machine-readable strings
  - Suggested values include:
    - `attendance_output_conflict`
    - `public_private_support_conflict`
    - `core_business_priority`
    - `weak_manager_support`
- `drop_reason`: String
  - Empty string allowed for retained candidates
  - Must be non-empty for the final non-retained candidates after HC contraction
  - In the expected final ground truth, `I03` and `I05` must have non-empty `drop_reason`

### ATS Updates

For every candidate, write:

- `recommendation`
- `ranking`
- `notes`

Notes should be concise but structured enough for deterministic review.

### Email Communication

- Stage 0 email to HRBP must summarize the full 1-5 ranking and notable risks, and attach `conversion_summary.json`.
- Stage 1 email to HRBP must explicitly list the final retained 3 (`I01`, `I02`, `I04`) and the reasons for dropping `I03` and `I05`, and attach the updated `conversion_summary.json`.

### File Naming

- All output files go to the current working directory.
- Use snake_case: `conversion_summary.json`.
- Do not modify files in `input/` -- that directory is read-only source evidence.
