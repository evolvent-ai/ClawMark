# AGENTS (Task Work Specifications)

## Startup Procedure

Each time you start:

1. Check Feishu and email—understand current task instructions
2. Go to CRM (case EQ2024-009) to pull all evidence attachments
3. Proactively check calendar for deadline updates

## Safety Rules

- Do not disclose preservation application plan to Boss Li or his attorney (core litigation strategy)
- Do not sign any documents on behalf of Mr. Zhao
- Immediately notify Attorney Li upon discovering urgent nodes like business registration publicity period

## Output Formats

### resolution_analysis.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| check_id | Sequential ID | RA01, RA02… |
| verification_item | Specific claim in resolution | Free text |
| resolution_claims | Original resolution content | Free text |
| actual_situation | Actual state discovered through verification | Free text |
| verification_result | Verification outcome | `VERIFIED` / `CONTRADICTED` / `QUESTIONABLE` |
| finding_type | Category of finding | `headcount_discrepancy` / `signature_anomaly` / `alibi_proof` / `procedural_defect` / `timeline_inconsistency` / `registration_urgency` / `none` |
| evidence_source | Specific file | Exact filename |

### forgery_evidence.md

Structure:
```
## Resolution Forgery Evidence Analysis (EQ2024-009)

### Evidence 1: Attendance Number Contradiction
### Evidence 2: Signature Method Anomaly
### Evidence 3: Alibi Proof
### Business Registration Emergency Situation
```

### urgent_evidence_summary.md

For preservation application, requires judge to understand directly.

### complete_evidence_list.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| evidence_no | Sequential number | 1, 2, 3… |
| evidence_name | Filename or brief name | Free text |
| source | Who provided / which system | Free text |
| proof_matter | One sentence explanation | Free text |
| evidence_strength | Strength assessment | `STRONG` / `MEDIUM` / `WEAK` |

### case_brief.md

In plain language for Mr. Zhao to read, avoid legal jargon.
