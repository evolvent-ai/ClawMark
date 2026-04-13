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
- `unit`: Unit label such as `BUSD`, `PCT`, `count`, or empty when not needed
- `basis`: Classification such as `reported`, `adjusted`, `guidance`, `consensus`, `peer_readthrough`, `visual_extracted`, `comparison_to_prior`, `classification`, `causal_driver`, `judgement`, `watch_item`, or `silent_followup`
- `direction`: One of `above`, `below`, `flat`, `positive`, `negative`, `mixed`, or empty
- `source_type`: One or more source labels such as `audio`, `transcript`, `pdf`, `image`, `sheet`, `notion`, or `news`
- `source_ref`: Short reference to the relevant file, tab, note, or excerpt
- `confidence`: One of `high`, `medium`, `low`
- `note`: Short supporting explanation when needed

Keep reported and adjusted figures separate. Do not collapse basis-sensitive facts into a single row.

### stage1_brief.md

The initial morning-meeting brief. It should be short, direct, and easy for Li Chen to speak from.

It should cover:
- reported versus adjusted net income
- FY24 total NII, NII excluding Markets, and adjusted expense
- comparison versus Street expectations
- watch items around deposit margin, office CRE, and card reserve build

### stage2_followup.md

The follow-up note for Li Chen's second-stage questions.

It should cover:
- 1Q24 versus 4Q23 guidance changes
- one clean office CRE conclusion
- any answer required by the silent LP question on deposit beta or over-earning

### stage3_alert.md

The overnight peer-framing note.

It should cover:
- the Wells Fargo guidance change
- the sector read-through implied by the overnight update
- JPM's relative positioning versus peers

### File Naming

- All output files go to `workspace/`.
- Use the exact filenames `facts.csv`, `stage1_brief.md`, `stage2_followup.md`, and `stage3_alert.md`.
- Do not modify files in `input/`.
