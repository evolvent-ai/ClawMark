# Tools

## Email

Send and receive emails. Used for formal communication and file sharing.

**Available addresses:**

| Address | Person | Role |
|---------|--------|------|
| assistant@uni.edu | Xiao Lin | You — the research assistant |
| chenxue@uni.edu | Chen Xue (陈雪) | PhD student — your primary user |
| wangwei@uni.edu | Prof. Wang Wei (王伟) | Doctoral advisor |
| zhangming@uni.edu | Zhang Ming (张明) | Collaborator — fellow PhD student |

## Notion — Paper Database

Paper tracking database for the literature survey.

**Database**: `paper_db`

**Fields**: Paper ID | Title | Venue | Year | Status | Key Metrics | Notes | (additional fields may be added by collaborators)

## Google Sheets — Comparison Spreadsheet

Structured metrics comparison table for the survey.

**Spreadsheet**: `NMT_Comparison`

## File System

Local file system access for reading input materials and writing outputs.

**Directories:**
- `input/` — Pre-seeded materials (read-only). Contains papers (PDF), reproduction logs, screenshots, and audio.
- `input/papers/` — Paper PDFs and survey draft PDF.
- `input/repro_logs/` — Reproduction experiment terminal logs.
- `input/screenshots/` — Screenshots received via email or referenced in messages.
- `workspace/outputs/` — Preferred agent output area (read-write). Place final deliverables here.
- `workspace/` — Writable scratch area for temporary scripts or intermediate files.

**Capabilities:**
- Can read PDF files and extract text, tables, and figures.
- Can read image files (PNG, JPG) for visual analysis (screenshots, photos, diagrams).
- Cannot directly edit PDF files — must produce new files (e.g., LaTeX) as replacements.

Environment note:
- There is no dedicated Feishu or STT manager in this benchmark variant. Communication arrives through email, and any voice-note content needed for the task is delivered via email transcript even if the original audio file is present in `input/`.
