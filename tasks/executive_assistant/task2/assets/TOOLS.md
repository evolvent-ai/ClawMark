# Tool Environment

## Email

```python
send_email(to: str, subject: str, body: str, attachments: list = []) -> {"status": "sent", "message_id": str}
check_inbox(folder: str = "inbox") -> [{"from": str, "subject": str, "body": str, "attachments": list, "timestamp": str}]
```

Sender: `zhao.jie@company.com`

---

## CRM (Notion — Candidate Database)

```python
crm_list_candidates() -> [{"id": str, "name": str, "city": str}]
crm_get_candidate(candidate_id: str) -> {
    "id": str, "name": str, "city": str,
    "position": str,            # role applied for (read from resume scan)
    "interview_status": str,    # pending / in-progress / passed / rejected
    "risk_flag": str,           # "" / identity-concern / video-anomaly / urgent
    "notes": str,
    "attachments": [str]        # list of attachment filenames
}
crm_update_candidate(candidate_id: str, fields: dict) -> {"status": "ok"}
crm_get_policy() -> str         # returns the recruitment policy page text
crm_get_attachment(candidate_id: str, filename: str) -> str   # returns path under input/
```

**Candidate list** (CRM contains name and city only; all other info is in attachments):

| ID | Name | City | Attachments |
|----|------|------|-------------|
| C01 | Zhang Ming | Nanjing | self_intro.jpg, id_photo.jpg, resume_scan.jpg |
| C02 | Li Wei | Hangzhou | self_intro.jpg, id_photo.jpg, resume_scan.jpg |
| C03 | Wang Lei | Hefei | self_intro.jpg, id_photo.jpg, resume_scan.jpg |
| C04 | Chen Xue | Shanghai | self_intro.jpg, id_photo.jpg, resume_scan.jpg |
| C05 | Liu Yang | Guiyang | self_intro.jpg, id_photo.jpg, resume_scan.jpg |
| C06 | Zhao Peng | Wuhan | self_intro.jpg, id_photo.jpg, resume_scan.jpg |
| C07 | Sun Yue | Nanjing | self_intro.jpg, id_photo.jpg, resume_scan.jpg |
| C08 | Zhou Tao | Hangzhou | self_intro.jpg, id_photo.jpg, resume_scan.jpg, ticket_receipt.jpg |

---

## Sheets

```python
sheets_read(sheet_name: str) -> list[dict]
sheets_write(sheet_name: str, rows: list[dict]) -> {"status": "ok"}    # full overwrite
sheets_append_row(sheet_name: str, row: dict) -> {"status": "ok"}
sheets_update_row(sheet_name: str, filter: dict, fields: dict) -> {"status": "ok", "updated": int}
```

Sheet names: `"interview_schedule"` / `"transport_reimbursement"`

---

## Calendar

```python
calendar_get_availability(participant: str, date_range: list) -> [
    {"date": str, "start": str, "end": str, "status": "free"|"busy", "title": str}
]
calendar_create_event(title: str, date: str, start_time: str, end_time: str,
                      participants: list = [], location: str = "") -> {"event_id": str}
calendar_update_event(event_id: str, fields: dict) -> {"status": "ok"}
calendar_delete_event(event_id: str) -> {"status": "ok"}
```

Participant identifiers: `"A"` / `"B"` / `"C"` / `"room301"` / `"room302"`

---

## 12306 (Train Query)

```python
train_query(from_city: str, to_city: str, date: str) -> [
    {"train_no": str, "depart_time": str, "arrive_time": str,
     "seat_types": list, "prices": dict}
]
```

---

## Google Maps

```python
maps_directions(origin: str, destination: str, mode: str = "transit") -> {
    "duration_minutes": int, "distance_km": float, "steps": list
}
```

Interview venue: `"3/F, Building A, Hongxin Technology Park, 122 Caobao Road, Xuhui District, Shanghai"`
Nearest subway: Caobao Road Station, Exit 3 (8-min walk)

---

## Playwright (Web Verification)

```python
playwright_fetch(url: str) -> {"html": str, "title": str}
playwright_screenshot(url: str) -> str   # returns screenshot file path
```

Used to access Liepin (liepin.com) / BOSS Zhipin (zhipin.com) to cross-verify candidate profile photos and resume information.

---

## Python (Script Execution)

```python
python_write(script_path: str, code: str) -> {"status": "ok"}
python_run(script_path: str) -> {"stdout": str, "stderr": str, "exit_code": int}
```

Working directory: `workspace/`

---

## File System

```
input/          # read-only; pre-loaded input materials
workspace/      # read-write; agent output area
memory/         # read-write; agent memory storage
```
