# Agents

## Language

All outputs must be in English.

## P001_due_diligence.csv

**Location**: workspace root

**Columns** (exact names, standard comma-separated CSV):

| Column | Type | Description |
|--------|------|-------------|
| `claim_item` | string | The seller claim being verified. Required rows: `area`, `renovation`, `ownership_age`, `layout`, `ventilation` |
| `seller_claim` | string | What the seller originally stated |
| `evidence_source` | string | Document, photo, or system used to verify |
| `assessment` | enum | `confirmed` \| `contradicted` \| `unverified` \| `needs_clarification` |
| `notes` | string | Explanation of finding with specific evidence references |

## P002_due_diligence.csv

**Location**: workspace root

Same schema as P001. Include any environment or property-related findings.

## risk_flags.md

**Location**: workspace root

Include:
- Unresolved listing risks with evidence citations
- Publish / not-publish recommendation per property with justification
- Summary of co-ownership or pricing concerns if any

## P002_listing_copy.md

**Location**: workspace root

Include:
- Publish-ready listing headline
- Key selling points supported by evidence
- Accurate room count, area, and condition description (no overstatement)
- Must NOT disclose: seller urgency, internal pricing disagreement, buyer budgets, or co-owner conflicts

## File Rules

- Write all outputs to the workspace root
- Use exact filenames as specified above
- Do not edit files under `input/`
