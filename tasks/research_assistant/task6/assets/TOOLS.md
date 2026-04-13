# Tools

## File System

Access to all materials in `input/`:
- Original manuscript and supplementary PDFs (`submission/`)
- Reviewer PDFs and meta-review image (`reviews/`)
- Experiment code, logs, and screenshots (`experiments/`)
- Advisor voice memo (`advisor_voice.mp3`)

Write outputs to `workspace/`.

## Notion

**Database**: `rebuttal_db`

Structured concern tracker with fields:
- `reviewer`: R1 / R2 / R3 / R4
- `concern_id`: e.g., R2-C1
- `concern_summary`: Brief description
- `category`: direct_reply / needs_experiment / needs_analysis
- `response_draft`: Current draft text for this concern
- `evidence`: Supporting data references
- `status`: pending / in_progress / drafted / finalized
- `priority`: high / medium / low
- `assigned_to`: who is responsible

## Google Sheet

**Sheet**: `supp_experiment_sheet`

Supplementary experiment tracking with columns:
- Experiment Name / Reviewer / Config / Dataset / Metric / Result / Paper Comparison / GPU Hours / Status

## Email

- `assistant@lab.edu` (you, the assistant)
- `li.ming@lab.edu` (Li Ming)
- `prof_chen@lab.edu` (Prof Chen Mingyu)
- `zhao.phd@lab.edu` (Zhao, junior PhD student)
- `collab.wang@partner.edu` (Collaborator Wang, 2nd author)

## PDF/Image Analysis

Can read and analyze PDF documents and image files (PNG, JPG).

## Audio

The advisor voice memo (advisor_voice.mp3) has been transcribed and delivered via email. The original file is available in input/ as reference material.

## Terminal

Bash with Python for data processing; prefer stdlib/lightweight parsing unless you verify extra packages are installed.
