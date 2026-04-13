# Agent Output Specifications

## General Rules
- All output files MUST be written to `workspace/` directory
- Never write to `input/` — it is read-only
- All numerical values in outputs must come from verified sources (CSV ground truth preferred)
- Use Chinese (中文) for emails and messages to Zhao Yang, Prof. Liu, and Dr. Wang

---

## Output File: experiment_summary.md

**Path:** `workspace/experiment_summary.md`

**Purpose:** Comprehensive summary of experiment results, baseline comparisons, and any anomalies found.

**Required Sections:**

```markdown
# 实验总结报告

## 各版本汇总指标
| Version | Model | Reported Epoch | Best Epoch | Acc | F1 | Prec | Recall |
|---------|-------|----------------|------------|-----|----|------|--------|
| v1 | ... | 50 | ... | ... | ... | ... | ... |
| v2 | ... | 50 | ... | ... | ... | ... | ... |
| v3 | ... | 50 | ... | ... | ... | ... | ... |
| v4 | ... | 50 | ... | ... | ... | ... | ... |

## Baseline 对比
(Compare our best results against published baselines, with source citations)

## 数据异常与冲突
(List each discrepancy found:)
- 【冲突】Source A says X, Source B says Y. Authoritative value: Z (from source).
- ...

## 训练观察
(Observations from TensorBoard curves and other visualizations)

## 建议操作
1. ...
2. ...
```

**Quality Criteria:**
- Every reported metric value must match the final-row CSV ground truth
- `Best Epoch` must be computed from the highest `val_f1` in the CSV
- All discrepancies between sources must be listed, no matter how small
- Visual observations from charts must be included
- Recommendations must be specific and actionable

---

## Output File: latex_table4.tex

**Path:** `workspace/latex_table4.tex`

**Purpose:** LaTeX tabular code for the paper's Table 4, ready to paste into the draft.

**Format:**
```latex
\begin{table}[t]
\centering
\caption{Comparison of experiment results.}
\label{tab:results}
\begin{tabular}{lcccc}
\toprule
Method & Acc & F1 & Prec & Recall \\
\midrule
v1 (ResNet-50 base) & ... & ... & ... & ... \\
v2 (+ RandAugment) & ... & ... & ... & ... \\
v3 (Swin-B) & ... & ... & ... & ... \\
v4 (Swin-B + LBS) & ... & ... & ... & ... \\
\bottomrule
\end{tabular}
\end{table}
```

**Quality Criteria:**
- All values must match CSV ground truth exactly
- Use standard LaTeX tabular with booktabs
- Values can be in percentage form (e.g., 86.7) or decimal form (e.g., 0.867) — be consistent
- Include baseline rows if requested

---

## Output File: final_checklist.md

**Path:** `workspace/final_checklist.md`

**Purpose:** Pre-submission sanity check with per-item verification status.

**Required Sections:**

```markdown
# ICML 提交前最终检查

## Table 4 逐项核对 (vs CSV)
| Version | Metric | Draft Value | CSV Value | Status |
|---------|--------|------------|-----------|--------|
| v1 | acc | ... | ... | ✅/❌ |
| ... | ... | ... | ... | ... |

## Fig.6 核对
- ...

## 正文数值引用核对
- Page X, "..." → Source: CSV v?_?.csv, epoch ??, value matches ✅/❌

## 显著性检验建议
- ...

## 具体修正建议
1. 【修正】Table 4, vX recall: 当前值 A → 应改为 B (来源: vX_?.csv)
2. ...

## GPU 计算成本
- GPU Model: ...
- Estimated GPU hours: ...
```

**Quality Criteria:**
- Every cell in Table 4 must be individually checked against CSV
- Each ❌ item must have a specific correction suggestion (current value → correct value, with source)
- GPU info must be extracted from available sources (visualizations, logs)
- Must recommend whether significance testing is needed

---

## Email Format

**To Zhao Yang (routine summary):**
- Subject: Clear and specific (e.g., "实验整理完成 + 数据冲突报告")
- Body: Lead with key findings, then details
- Flag critical issues with 【注意】or 【数据冲突】
- Include tables for data comparisons
- End with action items or questions

**To Prof. Liu (advisor communication):**
- Subject: Professional and specific
- Body: Concise, data-driven, respectful tone
- Include requested data (comparisons, costs) in structured format
- Attach or reference relevant files

**To Dr. Wang (collaborator communication):**
- Subject: Clear context about what you're responding to
- Body: Acknowledge received data, provide comparison or analysis
- Professional and collaborative tone

---

## Notion Records

**Database:** experiment_db

**Per-record fields:**
- exp_name: version identifier (e.g., "v3_swin")
- date: experiment date
- model: model architecture description
- dataset: dataset used
- acc: reported accuracy — MUST match final-row CSV ground truth
- f1: reported F1 — MUST match final-row CSV ground truth
- prec: reported precision — MUST match final-row CSV ground truth
- recall: reported recall — MUST match final-row CSV ground truth
- best_epoch: diagnostic best epoch computed by `val_f1`
- status: experiment status (e.g., "completed")
- notes: any relevant observations

---

## Google Sheet Updates

**Spreadsheets:** `our_runs`, `baselines`

**`our_runs`:**
- Fill v1-v4 rows with metrics from CSV ground truth
- All values must exactly match CSV data

**`baselines`:**
- Read-only initially; check periodically for updates by others
- If changes detected, update analysis accordingly
