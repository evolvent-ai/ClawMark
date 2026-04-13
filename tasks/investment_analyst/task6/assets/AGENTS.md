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
- revenue growth on a spot basis versus FX-neutral basis
- transaction margin dollars, TPV, and mix by branded checkout versus PSP as separate bases
- actual Q1 performance versus prior-quarter guide
- watch items around mix dilution, interest / loss tailwind, and deferred investment timing

### stage2_followup.md

The second-stage follow-up note.

It should cover:
- current guidance / methodology versus prior-quarter setup
- one clean transaction-margin-quality conclusion
- any answer required by the silent LP question on whether margin improvement is structural or mostly timing / tailwind driven

### stage3_alert.md

The overnight peer-framing note.

It should cover:
- the Block peer update
- the sector read-through implied by the peer update
- PayPal's relative positioning versus peers

### File Naming

- All output files go to `workspace/`.
- Use the exact filenames `facts.csv`, `stage1_brief.md`, `stage2_followup.md`, and `stage3_alert.md`.
- Do not modify files in `input/`.
