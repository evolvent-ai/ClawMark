---
name: calendar
description: "Manage calendars and events via Radicale CalDAV server"
---

# Calendar Skill

Create, query, and delete calendar events on a CalDAV server using Python's `caldav` library (pre-installed in container).

## Server Info

| Setting | Value |
|---------|-------|
| URL | `http://radicale:5232` |
| Username | `benchmark` |
| Password | (empty) |

Available calendar names will be provided in the task context.

## Connect

```python
import caldav

client = caldav.DAVClient(url="http://radicale:5232", username="benchmark", password="")
principal = client.principal()
```

## List Calendars

```python
for cal in principal.calendars():
    print(cal.name, cal.url)
```

## Get a Calendar by Name

```python
cal = principal.calendar(name="my_calendar")
```

## List Events

```python
# All events
for event in cal.events():
    print(event.data)

# Events in a date range
from datetime import datetime
events = cal.search(event=True, start=datetime(2028, 4, 12), end=datetime(2028, 4, 13), expand=True)
```

## Create Event

```python
from datetime import datetime

cal.save_event(
    dtstart=datetime(2028, 4, 12, 14, 0),
    dtend=datetime(2028, 4, 12, 15, 0),
    summary="Meeting Title",
    uid="unique-event-id",
    location="Room A",
    description="Additional details or video link",
)
```

**Key fields:**
- `uid`: Unique identifier (for later lookup/deletion)
- `dtstart`/`dtend`: Python datetime objects (local time)
- `summary`: Event title
- `location`: Physical room name or "Video"
- `description`: Details, video link, etc.

## Find Event by UID

```python
event = cal.event_by_uid("unique-event-id")
print(event.data)
```

## Delete Event

```python
event = cal.event_by_uid("unique-event-id")
event.delete()
```

## Read Event Properties

```python
event = cal.event_by_uid("unique-event-id")
comp = event.icalendar_component
print(comp.get("summary"))      # Event title
print(comp.get("dtstart").dt)   # Start time (datetime)
print(comp.get("dtend").dt)     # End time (datetime)
print(comp.get("location"))     # Location
print(comp.get("description"))  # Description
```
