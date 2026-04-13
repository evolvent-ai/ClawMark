# Agents

## Output Specifications

All output files should be placed in `/workspace/outputs/`. Use `snake_case` for filenames.

### Expected Outputs

| File | Description | Format | Stage |
|------|-------------|--------|-------|
| `code_audit_report.csv` | All issues found during codebase audit | CSV (see schema below) | Stage 0 |
| `README.md` | Complete README for public GitHub repository | Markdown | Stage 1 |
| `MODEL_CARD.md` | HuggingFace-style Model Card | Markdown | Stage 1 |
| `RELEASE_NOTES.md` | Release notes with known issues | Markdown | Stage 2 |
| `final_checklist.csv` | Final pre-release checklist with status | CSV (see schema below) | Stage 2 |

### code_audit_report.csv Schema

| Column | Type | Allowed Values |
|--------|------|----------------|
| `issue_id` | string | Sequential: `ISSUE-001`, `ISSUE-002`, ... |
| `file_path` | string | Relative path from codebase root (e.g., `train.py`) |
| `line_number` | integer | Line number where issue occurs (0 if N/A) |
| `severity` | enum | `critical`, `high`, `medium`, `low` |
| `category` | enum | `security`, `dead_code`, `hardcoded_path`, `missing_dependency`, `broken_link`, `config_gap`, `data_integrity`, `compliance`, `code_quality`, `import_error` |
| `description` | string | Brief description of the issue |
| `recommendation` | string | Recommended fix |

### final_checklist.csv Schema

| Column | Type | Allowed Values |
|--------|------|----------------|
| `item_id` | string | Sequential: `CHK-001`, `CHK-002`, ... |
| `category` | enum | `security`, `reproducibility`, `documentation`, `compliance`, `code_quality`, `dependencies` |
| `item` | string | Description of the check item |
| `status` | enum | `pass`, `fail`, `partial`, `blocked` |
| `notes` | string | Details, especially for non-pass items |

### Notion release_db Fields

| Field | Type | Values |
|-------|------|--------|
| `task` | title | Task name |
| `category` | select | `code_cleanup`, `documentation`, `reproduction`, `weights`, `license`, `model_card` |
| `status` | select | `not_started`, `in_progress`, `completed`, `blocked` |
| `owner` | rich_text | Person responsible |
| `blocker` | rich_text | Blocker description (if any) |
| `notes` | rich_text | Additional notes |

### Google Sheet repro_sheet Columns

| Column | Description |
|--------|-------------|
| `paper_ref` | Paper Table/Figure number (e.g., `Table 1 MSCOCO`) |
| `script` | Script used to reproduce (e.g., `scripts/run_table1.sh`) |
| `config_file` | Config YAML path |
| `dataset` | Dataset name |
| `expected_metric` | Paper-reported value |
| `actual_output` | Actual log/run value |
| `consistency` | `consistent`, `inconsistent`, `pending`, `partial` |
| `notes` | Additional notes (e.g., tolerance, OOM issues) |

### Output Format Guidelines

- CSV files must use standard comma-separated format with headers.
- Markdown files should use clear section headers and bullet points.
- Include timestamps and specific file paths/line numbers where relevant.
- Reference severity rankings: Critical > High > Medium > Low.
