## On Each Startup

1. Check Feishu and email — understand current task instructions
2. Pull all evidence attachments from CRM (case WILL2024-003)
3. Proactively check the calendar for any deadline changes

## Safety Rules

- Do not contact the opposing party Zhao Xiaohong directly (professional ethics red line)
- Do not alter any document signatures or dates
- Do not sign any legal documents on behalf of either party

## Output Formats

### will_verification_report.md

Structure:
```
## Will Basic Information (OCR Extracted)
- Testator:
- Date of Will:
- Beneficiaries and Distribution:
- Scrivener:
- Will Type: □ Holographic □ Dictated □ Notarized

## Validity Review
| Review Dimension | Conclusion | Basis |
|-----------------|------------|-------|
| Testator's cognitive capacity | | |
| Signature authenticity | | |
| Formal requirements | | |

## Key Findings
(List each contradiction item by item, noting the evidence source for each)

## Recommended Next Steps
```

### evidence_comparison.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| evidence_id | Sequential ID | EC01, EC02… |
| evidence_source | Specific filename with page/location | e.g. medical_records_2023.pdf p7 |
| what_it_proves | What this evidence demonstrates | Free text |
| supports | Which party this evidence supports | `ZHAO_XIAOMING` / `ZHAO_XIAOHONG` / `NEUTRAL` |
| credibility | Evidence credibility assessment | `HIGH` / `MEDIUM` / `LOW` |
| finding_type | Category of finding | `cognitive_capacity` / `signature_authenticity` / `formal_requirement` / `date_inconsistency` / `medical_contradiction` / `notary_issue` / `property_related` / `none` |
| anomaly_notes | Contradictions or suspicious points | Free text |

### complete_evidence_list.csv

| Column | Description | Allowed Values |
|--------|-------------|----------------|
| evidence_no | Sequential number | 1, 2, 3… |
| evidence_name | Filename or short description | Free text |
| source | Who provided it / which system | Free text |
| what_it_proves | One-sentence description | Free text |
| credibility | Evidence credibility | `HIGH` / `MEDIUM` / `LOW` |
| anomaly_flag | Anomaly indicator | `NONE` / `LIMITED_PROBATIVE` / `SUSPECTED_FORGERY` |

### strategy_brief.md

Bullet-point format for Attorney Li's quick review:
1. Core dispute in the case
2. Favorable evidence on our side (ranked by strength)
3. Weaknesses in opposing party's claims
4. Plan for responding to the forensic psychiatric evaluation application
5. Items that must be completed before March 25
