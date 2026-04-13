# Agents

## Output Specifications

### master_schedule.csv

The primary deliverable, maintained across all stages. Must be placed in `workspace/`.

**Schema** (CSV, UTF-8, comma-separated):

```
candidate_id,date,start_time,end_time,format,room_id,video_link,status
```

- `candidate_id`: Candidate code (e.g., "C01")
- `date`: `YYYY-MM-DD`
- `start_time`: `HH:MM` (24-hour, Beijing Time)
- `end_time`: `HH:MM`
- `format`: One of {video, on-site}
- `room_id`: Room identifier if on-site (e.g., "RoomA"), empty if video
- `video_link`: Video meeting URL if video, empty if on-site
- `status`: One of {scheduled, cancelled, withdrawn}

### Email Communication

- Use formal, professional Chinese.
- Confirmation emails to candidates must include: date, time, format (video link or office address + room), interviewer name.
- Rescheduling emails must give a neutral reason (e.g., "due to a scheduling adjustment") — never reveal personal details about the interviewer.
- When sending the final CSV to Director Lin, attach `master_schedule.csv` or include its contents inline.

### File Naming

- All output files go to `workspace/`.
- Use snake_case: `master_schedule.csv`.
- Do not modify files in `input/` — that directory is read-only.
