---
name: google_sheets
description: "Read and update Google Sheets spreadsheets via Python"
---

# Google Sheets Skill

Read and update Google Sheets using Python's `gspread` library (pre-installed in container).

## Credentials

Credentials are pre-configured at `/root/.google/credentials.json`. No manual setup needed.

## Connect

```python
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import gspread

with open("/root/.google/credentials.json") as f:
    cred_data = json.load(f)

creds = Credentials(
    token=cred_data.get("token"),
    refresh_token=cred_data["refresh_token"],
    token_uri=cred_data["token_uri"],
    client_id=cred_data["client_id"],
    client_secret=cred_data["client_secret"],
)
creds.refresh(Request())

gc = gspread.authorize(creds)
```

## Open a Spreadsheet

```python
# By name
sheet = gc.open("Q1_Content_Budget")

# By URL
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/SHEET_ID/edit")

# Get the first worksheet
ws = sheet.sheet1
```

## Read Data

```python
# All values
all_data = ws.get_all_values()       # list of lists
all_records = ws.get_all_records()    # list of dicts (header row as keys)

# Specific cell
val = ws.acell("B2").value

# Range
vals = ws.get("A1:D4")               # list of lists
```

## Write Data

```python
# Single cell
ws.update_acell("B2", "new value")

# Range
ws.update("A1:C2", [
    ["Name", "Status", "Amount"],
    ["Campaign A", "Active", "5000"],
])

# Append a row after existing data
ws.append_row(["Campaign B", "Pending", "3000"])
```

## Find Cells

```python
# Find first cell matching value
cell = ws.find("Campaign A")
print(f"Found at row {cell.row}, col {cell.col}")

# Find all matches
cells = ws.findall("Active")
```

Spreadsheet name and other task-specific details will be provided in the task context.
