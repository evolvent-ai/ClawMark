# Agents

## Output Specifications

All CSV files must be UTF-8 encoded and placed in `outputs/` directory.

---

### outputs/audit_metadata.csv

Single-row CSV documenting data quality checks and methodology decisions (audit trail).

| Column | Type | Description |
|--------|------|-------------|
| outlier_count | integer | Number of data outliers identified and excluded |
| outlier_ids | string | Semicolon-separated outlier employee IDs (e.g. "E011;E051;E151") |
| market_reference_type | enum {base, total_compensation} | Compensation type used for market benchmarking |
| market_conflict_detected | enum {true, false} | Whether chart vs text data conflict was detected in market report |
| tech_employee_count | integer | Number of valid tech employees after outlier removal |

---

### outputs/priority_adjustment_list.csv

Priority list of employees needing salary adjustment.

| Column | Type | Description |
|--------|------|-------------|
| employee_id | string | Employee ID (e.g. E001) |
| name | string | Employee name |
| sequence | enum {Algorithm, Data, Engineering, Testing} | Technical sequence |
| level | integer | Job level (1-6) |
| gender | enum {Male, Female} | Gender |
| current_base | number | Current monthly base salary (RMB) |
| market_p25 | number | Market P25 monthly base salary for this level |
| gap_pct | number | Gap percentage: (market_p25 - current_base) / market_p25 |
| performance | enum {A+, A, A-, B+} | Performance grade (B+ and above only) |
| priority_score | number | Weighted priority score |
| recommendation | string | Recommended action |

**Filters**: Only tech sequence employees with performance >= B+ and current_base < market P25. Exclude data outliers.

---

### outputs/retention_priority_list.csv

Detailed retention risk analysis sorted by risk score descending.

| Column | Type | Description |
|--------|------|-------------|
| employee_id | string | Employee ID |
| name | string | Employee name |
| level | integer | Job level |
| sequence | enum {Algorithm, Data, Engineering, Testing} | Technical sequence |
| current_base | number | Current monthly base salary |
| market_p25 | number | Market P25 monthly base salary |
| performance | enum {A+, A, A-, B+} | Performance grade |
| risk_score | number | Retention risk score (0-1 scale) |
| retention_risk_level | enum {low, medium, high} | Risk level classification |
| raise_suggestion | string | Suggested raise action |

**Risk score formula**: 0.4 x pay_deviation + 0.3 x performance_weight + 0.2 x inverse_tenure + 0.1 x job_search_proxy

**Sort**: By risk_score descending.

---

### outputs/risk_reassessment.csv

Updated risk assessment after competitor intelligence.

| Column | Type | Description |
|--------|------|-------------|
| employee_id | string | Employee ID |
| name | string | Employee name |
| level | integer | Job level |
| current_base | number | Current monthly base salary |
| previous_risk | enum {low, medium, high} | Risk level before competitor intel |
| updated_risk | enum {low, medium, high} | Updated risk level |
| competitor_pressure | enum {none, low, medium, high} | Competitor pressure assessment |
| recommended_raise_pct | number | Recommended raise percentage |

---

### outputs/comp_audit_report.md

Comprehensive audit report with:
- Executive summary (3 sentences max)
- Gender gap analysis by level / sequence
- Market benchmarking results (using base salary)
- Priority adjustment recommendations
- Methodology and assumptions section

---

### outputs/competitor_risk_update.md

Competitor intelligence response with:
- Competitor salary analysis
- Risk level reassessment rationale
- Emergency action recommendations (top 3 high-risk employees)
- Assumption documentation (salary type assumption)

---

## Communication Standards
- Email subject: Include "[Compensation Audit]" prefix
- Executive summary: 3-sentence format (key finding, evidence, recommendation)

## ATS Update Requirements
- **Stage 0**: Create records for priority list employees with status = "pending_review"
- **Stage 1**: Update retention_risk_level (low/medium/high), set status = "vp_prioritized"
- **Stage 2**: Set Competitor Pressure flag, update Recommended Raise Pct

## Google Sheets Update
- **Stage 2**: Populate "Salary Adjustment Tracker 2024" with final recommendations
