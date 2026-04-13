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
- `unit`: Unit label such as `BUSD`, `BTWD`, `PCT`, `count`, or empty when not needed
- `basis`: Classification such as `reported`, `guidance`, `consensus`, `peer_readthrough`, `visual_extracted`, `comparison_to_prior`, `classification`, `causal_driver`, `structural_signal`, or `judgement`
- `direction`: One of `above`, `below`, `flat`, `positive`, `negative`, `mixed`, or empty
- `source_type`: One or more source labels such as `audio`, `transcript`, `pdf`, `image`, `sheet`, `notion`, or `news`
- `source_ref`: Short reference to the relevant file, tab, note, or excerpt
- `confidence`: One of `high`, `medium`, `low`
- `note`: Short supporting explanation when needed

USD and TWD revenue facts may both appear, but they must be stored as a normalized currency difference rather than a contradiction.

### stage1_brief.md

The initial first-read brief for Zhou Ning.

It should cover:
- revenue, margins, Q2 guide, and capex
- USD versus TWD normalization
- node mix and platform mix from the image input
- AI demand and near-term margin headwinds

### stage2_followup.md

The follow-up note for Zhou Ning's second-stage questions.

It should cover:
- whether capex changed versus the prior quarter
- CoWoS or advanced-packaging tightness into 2025
- quantitative AI server mix framing
- the 3nm mix change versus 4Q23 when the silent LP question is found

### stage3_alert.md

The overnight peer read-through note.

It should cover:
- the STMicro guidance cut
- the mature-node, auto, and industrial read-through
- why that read-through does or does not break the core TSMC AI or HPC thesis

### File Naming

- All output files go to `workspace/`.
- Use the exact filenames `facts.csv`, `stage1_brief.md`, `stage2_followup.md`, and `stage3_alert.md`.
- Do not modify files in `input/`.
