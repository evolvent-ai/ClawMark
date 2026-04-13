## Output Specifications

All deliverables must be written to /workspace/.

---

### 1. alex_risk_findings.csv (Stage 0)

Background-check risk findings from cross-validation of candidate materials.

| Column          | Type   | Allowed Values / Description                    |
|-----------------|--------|--------------------------------------------------|
| risk_category   | enum   | education, title, credential                     |
| evidence_source | text   | Comma-separated list of evidence files/sources   |
| finding         | text   | Description of the inconsistency found           |
| severity        | enum   | high, medium, low                                |

Must contain at least 3 rows (one per risk category).

---

### 2. agency_hold_list.csv (Stage 1)

Record of candidates placed on hold due to agency credibility review.

| Column          | Type   | Allowed Values / Description                    |
|-----------------|--------|--------------------------------------------------|
| candidate_name  | text   | Full name of the candidate                       |
| agency          | text   | Recruiting agency name                           |
| previous_status | text   | ATS status before the hold action                |
| action          | enum   | hold, no_action                                  |
| note            | text   | Reason or context for the action                 |

Must include all candidates from the flagged agency.

---

### 3. alex_risk_update.csv (Stage 2)

Updated risk assessment after reviewing new evidence (promotion letter).

| Column          | Type   | Allowed Values / Description                    |
|-----------------|--------|--------------------------------------------------|
| risk_category   | enum   | education, title, credential                     |
| new_evidence    | text   | Description of new evidence reviewed             |
| resolved        | enum   | yes, no, partial                                 |
| explanation     | text   | Why the risk is or is not resolved               |

Must include at least the education and title rows.

---

### 4. Email Communication

- Use formal, professional English.
- Keep escalation emails short and evidence-based.
- Always address emails to hr_vp@xinghai.cn for risk escalations.
- Do not use language implying the candidate is cleared unless the status has actually changed.

### 5. ATS (Notion) Updates

- Update the relevant risk fields (Education Risk, Title Risk, Credential Risk) with concise findings.
- Append new information to the Notes field — never overwrite existing notes.
- Use the Status field only as instructed (e.g., set to "Hold" when directed).
