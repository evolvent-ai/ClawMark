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
- `unit`: Unit label such as `BUSD`, `MUSD`, `PCT`, `count`, `USD_per_share`, or empty when not needed
- `basis`: Classification such as `reported`, `fx_neutral`, `guidance`, `prior_guidance`, `public_consensus`, `peer_readthrough`, `metric_scope`, `comparison_to_prior`, `classification`, `causal_driver`, `judgement`, `watch_item`, `silent_followup`, or `deal_terms`
- `direction`: One of `above`, `below`, `flat`, `positive`, `negative`, `mixed`, or empty
- `source_type`: One or more source labels such as `transcript`, `pdf`, `html`, `image`, `sheet`, `notion`, or `news`
- `source_ref`: Short reference to the relevant file, tab, page, note, or excerpt
- `confidence`: One of `high`, `medium`, `low`
- `note`: Short supporting explanation when needed

Keep basis-sensitive figures separate. Do not collapse nearby figures that are on different bases into a single row.

### stage1_brief.md

The initial first-read brief. It should be short, direct, and easy for the supervising analyst / partner to speak from.

It should cover:
- revenue versus constant-currency revenue growth
- bookings, ARRR, ARPUS, adjusted EBITDA, and UFCF as separate bases
- Q1 actual versus prior Q1 guide
- key transaction terms and watch items around Google Domains contribution and metric-scope exclusions

### stage2_followup.md

The second-stage follow-up note.

It should cover:
- updated FY24 guide versus prior FY24 guide
- one clean revenue-quality / metric-scope sentence
- any answer required by the silent IC question on Google Domains and excluded acquired-domain KPIs

### stage3_alert.md

The overnight peer-framing note.

It should cover:
- the Wix peer update
- the sector read-through implied by the peer update
- Squarespace's deal / quality framing versus peers

### File Naming

- All output files go to `workspace/`.
- Use the exact filenames `facts.csv`, `stage1_brief.md`, `stage2_followup.md`, and `stage3_alert.md`.
- Do not modify files in `input/`.
