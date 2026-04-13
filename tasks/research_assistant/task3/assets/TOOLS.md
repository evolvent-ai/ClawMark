# Tools

## Email

Send and receive emails. Available addresses:

| Address | Person | Role |
|---------|--------|------|
| assistant@university.edu | You (Research Assistant) | Research group assistant |
| lin.fan@university.edu | 林凡 (Lin Fan) | Associate Professor (your boss) |
| xiaoming@university.edu | 小明 (Xiao Ming) | PhD student — CVPR paper |
| xiaohong@university.edu | 小红 (Xiao Hong) | PhD student — NeurIPS rebuttal |
| xiaowei@university.edu | 小伟 (Xiao Wei) | Master's student — Proposal defense |
| xiaogang@university.edu | 小刚 (Xiao Gang) | PhD student — Video understanding |
| liu.manager@enterprise.com | 刘经理 (Liu Manager) | Enterprise project contact |

## Notion (Student & Project Databases)

Two databases for tracking student progress and the enterprise project.

### student_db — Student Management

**Fields**: name (title, str) | project (str) | stage (str) | next_deadline (str) | blockers (str) | notes (str)

### project_db — Enterprise Project

**Fields**: milestone (title, str) | status (str) | deliverable (str) | deadline (str)

## Google Sheet

Lab meeting tracking spreadsheet.

### meeting_sheet

**Columns**: Date | Student | Topic | Action Items | Status

## File System

- `input/` — Pre-seeded materials (read-only). Contains student papers, review screenshots, enterprise documents, meeting recording transcript, and training screenshots.
- `workspace/` — Agent output area (read-write). Place all deliverables here.
