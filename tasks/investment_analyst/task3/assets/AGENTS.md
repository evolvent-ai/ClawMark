# Agents

## Output Specifications

All required outputs must be placed in `workspace/`.

### facts.csv

The primary structured deliverable, maintained across all stages.

**Schema** (CSV, UTF-8, comma-separated):

```csv
stage,metric,value,unit,basis,direction,source_type,source_ref,confidence,note
```

- `stage`: One of `S1`, `S2`, `S3`
- `metric`: Canonical metric or reasoning label
- `value`: Numeric value, boolean flag, or short categorical value
- `unit`: Unit label such as `BUSD`, `PCT`, `PCT_POINT`, `count`, or empty when not needed
- `basis`: Classification such as `reported`, `constant_currency`, `guidance`, `comparison_to_prior`, `visual_extracted`, `classification`, `causal_driver`, `structural_signal`, `judgement`, or `policy_guardrail`
- `direction`: One of `above`, `below`, `flat`, `positive`, `negative`, `mixed`, or empty
- `source_type`: One or more source labels such as `audio`, `transcript`, `pdf`, `image`, `sheet`, `notion`, `news`, or `task`
- `source_ref`: Short reference to the relevant file, tab, note, or excerpt
- `confidence`: One of `high`, `medium`, `low`
- `note`: Short supporting explanation when needed

Keep reported growth, constant-currency growth, operational raise, and FX headwind separate in structured outputs.

### stage1_brief.md

The initial first-read summary for Chen Yi.

It should cover:
- subscription revenue and cRPO
- Q2 guide and FY24 published range
- large-deal and GenAI evidence
- reported versus constant-currency framing

### stage2_followup.md

The follow-up note for Chen Yi's second-stage questions.

It should cover:
- the old versus new FY24 subscription range
- operational raise versus FX headwind
- the public-sector drag on cRPO

### stage3_alert.md

The overnight sector-framing note.

It should cover:
- the software-sector sentiment change from the overnight update
- ServiceNow's relative resilience versus weaker peers
- the distinction between sector pressure and company-specific execution

### File Naming

- All output files go to `workspace/`.
- Use the exact filenames `facts.csv`, `stage1_brief.md`, `stage2_followup.md`, and `stage3_alert.md`.
- Do not modify files in `input/`.
