# Tools

## Waveform Viewer

- FST file (`tc_reset_rr_17.fst`) is binary -- agent cannot directly parse it.
- PNG screenshots provided for visual analysis:
  - `input/waveform/wave_overview.png` -- full simulation timeline with key signals
  - `input/waveform/wave_zoom_fail.png` -- zoomed view around failure point
- Agent should analyze PNG images to understand signal behavior at the cycle level.

## PDF Reader

- `input/spec/arbiter_protocol_spec.pdf` -- protocol specification document
- Agent reads this to verify expected behavior against spec.

## Email

Available addresses include:

- `mike.zhang@starwave.com` (Design Engineer, arbiter owner)
- `david.liu@starwave.com` (Senior Verification Lead)

## Issue Tracker (Mock)

- Agent writes triage output to `workspace/issue_tracker.json`.
- Issue metadata may appear in `workspace/issue_metadata.json` (injected by framework between stages).

## Terminal (Bash)

- Available for grep, text processing, data extraction from logs.
- Can be used for scripting analysis tasks.

## File System

- `input/` contains RTL, testbench, logs, waveforms, spec, Slack notes, JIRA history, and later-injected files (read-only).
- `workspace/` is writable for deliverables.
