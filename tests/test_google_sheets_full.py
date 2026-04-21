"""Comprehensive Google Sheets integration test.

Covers three scenarios:
  1. Serial task reset: Task A mutates sheet → cleanup → Task B gets clean slate
  2. Normal CRUD operations work correctly
  3. Model tool_use → host apply → host API verify

Usage:
    uv run python tests/test_google_sheets_full.py

Prerequisites:
    - configs/google_credentials.json
    - ANTHROPIC_API_KEY env var (for model test)
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

from clawmark.state.google_sheets import GoogleSheetsStateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TEMPLATE_URL = os.environ.get(
    "GOOGLE_SHEETS_TEMPLATE_URL",
    "https://docs.google.com/spreadsheets/d/1HSNo1wDj9Nx8YWjeVOsK9opfLvipB29hLFuz3xb0JU4/edit",
)
# Template has: Name | Status | Priority / Alpha | Open | High / Beta | Closed | Low

MODEL = os.environ.get("E2E_MODEL", "claude-sonnet-4-5-20250929")
API_BASE = os.environ.get("ANTHROPIC_API_BASE", "")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

UPDATE_CELLS_TOOL = {
    "name": "update_cells",
    "description": "Update cells in the Google Sheet. Provide a list of updates, each with a cell range (e.g. 'B2') and the new value.",
    "input_schema": {
        "type": "object",
        "properties": {
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cell": {"type": "string", "description": "Cell reference like 'B2'"},
                        "value": {"type": "string", "description": "New cell value"},
                    },
                    "required": ["cell", "value"],
                },
            }
        },
        "required": ["updates"],
    },
}

passed = 0
failed = 0


class _NoopSandbox:
    async def exec(self, *a, **kw):
        class _R:
            stdout = "{}"
            return_code = 0
        return _R()
    async def upload_dir(self, *a, **kw): pass
    async def download_dir(self, *a, **kw): pass
    async def upload_file(self, *a, **kw): pass
    async def download_file(self, *a, **kw): pass


def check(cond: bool, msg: str) -> None:
    global passed, failed
    if not cond:
        print(f"  FAIL: {msg}")
        failed += 1
    else:
        print(f"  PASS: {msg}")
        passed += 1


async def call_model(sheet_data: list[list[str]], prompt: str) -> list[dict]:
    """Call model with sheet data, return tool_use updates."""
    sheet_text = "\n".join(" | ".join(row) for row in sheet_data)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{API_BASE}/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 1024,
                "tools": [UPDATE_CELLS_TOOL],
                "messages": [{"role": "user", "content": (
                    f"Here is a Google Sheet:\n\n{sheet_text}\n\n"
                    f"{prompt}\n\nUse the update_cells tool to make the changes."
                )}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    updates = []
    for block in data.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "update_cells":
            updates.extend(block["input"].get("updates", []))
    return updates


async def main():
    sandbox = _NoopSandbox()

    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 1: Serial Task Reset — Task A mutations don't leak to Task B")
    print("=" * 70)
    # ══════════════════════════════════════════════════════════════════

    # ── Task A: setup → copy template → mutate heavily → cleanup ──
    print("\n── Task A: setup + mutate ──")
    task_a = GoogleSheetsStateManager(config={"task_id": "task_a"})
    await task_a.setup(sandbox=sandbox)
    res_a = await task_a.copy_template(TEMPLATE_URL)
    sid_a = res_a["sheet_id"]

    # Read original template data (for comparison later)
    original_data = await task_a.read_values(sid_a, "Sheet1")
    print(f"  Template original: {original_data}")

    # Mutate: change cells, append rows, overwrite headers
    await task_a.update_values(sid_a, "Sheet1!B2", [["MODIFIED_BY_TASK_A"]])
    await task_a.append_rows(sid_a, "Sheet1", [
        ["TaskA-Extra1", "TaskA-Val", "TaskA-Pri"],
        ["TaskA-Extra2", "TaskA-Val2", "TaskA-Pri2"],
    ])
    await task_a.update_values(sid_a, "Sheet1!C1", [["CORRUPTED_HEADER"]])

    mutated = await task_a.read_values(sid_a, "Sheet1")
    print(f"  After mutation: {mutated}")
    check(len(mutated) == 5, f"Task A has 5 rows (original 3 + 2 appended): got {len(mutated)}")
    check(mutated[1][1] == "MODIFIED_BY_TASK_A", "Task A cell B2 was modified")

    # Cleanup Task A
    print("\n── Task A: cleanup ──")
    await task_a.cleanup()

    # ── Task B: setup → copy same template → verify clean state ──
    print("\n── Task B: setup + verify clean slate ──")
    task_b = GoogleSheetsStateManager(config={"task_id": "task_b"})
    await task_b.setup(sandbox=sandbox)
    res_b = await task_b.copy_template(TEMPLATE_URL)
    sid_b = res_b["sheet_id"]

    task_b_data = await task_b.read_values(sid_b, "Sheet1")
    print(f"  Task B data: {task_b_data}")

    # Key assertions: Task B should have the exact same clean template
    check(
        task_b_data == original_data,
        f"Task B data matches original template exactly"
    )
    check(
        len(task_b_data) == 3,
        f"Task B has 3 rows (no Task A appended rows): got {len(task_b_data)}"
    )
    has_task_a_data = any("MODIFIED_BY_TASK_A" in str(row) for row in task_b_data)
    check(not has_task_a_data, "No 'MODIFIED_BY_TASK_A' in Task B — reset confirmed")
    has_corrupted = any("CORRUPTED_HEADER" in str(row) for row in task_b_data)
    check(not has_corrupted, "No 'CORRUPTED_HEADER' in Task B — headers intact")
    has_extra = any("TaskA-Extra" in str(row) for row in task_b_data)
    check(not has_extra, "No 'TaskA-Extra' rows in Task B — appended rows gone")

    # Verify different folder IDs
    check(
        res_a["sheet_id"] != res_b["sheet_id"],
        f"Different sheet IDs: A={sid_a[:12]}... B={sid_b[:12]}..."
    )

    await task_b.cleanup()

    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 2: Normal CRUD Operations")
    print("=" * 70)
    # ══════════════════════════════════════════════════════════════════

    mgr = GoogleSheetsStateManager(config={"task_id": "crud_test"})
    await mgr.setup(sandbox=sandbox)
    res = await mgr.copy_template(TEMPLATE_URL)
    sid = res["sheet_id"]

    # Read
    print("\n── Read ──")
    vals = await mgr.read_values(sid, "Sheet1")
    check(vals[0] == ["Name", "Status", "Priority"], f"Headers correct: {vals[0]}")
    check(vals[1] == ["Alpha", "Open", "High"], f"Row 1 correct: {vals[1]}")
    check(vals[2] == ["Beta", "Closed", "Low"], f"Row 2 correct: {vals[2]}")

    # Update
    print("\n── Update ──")
    await mgr.update_values(sid, "Sheet1!B2", [["Done"]])
    vals = await mgr.read_values(sid, "Sheet1!B2")
    check(vals == [["Done"]], f"Update read-back: {vals}")

    # Append
    print("\n── Append ──")
    await mgr.append_rows(sid, "Sheet1", [["Charlie", "New", "Medium"]])
    vals = await mgr.read_values(sid, "Sheet1")
    check(len(vals) == 4, f"4 rows after append: got {len(vals)}")
    check(vals[3] == ["Charlie", "New", "Medium"], f"Appended row: {vals[3]}")

    # Find row
    print("\n── Find Row ──")
    row = await mgr.find_row(sid, "Sheet1", 0, "Charlie")
    check(row is not None, "find_row found Charlie")
    check(row["Status"] == "New", f"Charlie Status={row['Status']}")
    check(row["Priority"] == "Medium", f"Charlie Priority={row['Priority']}")

    # Find row (not found)
    missing = await mgr.find_row(sid, "Sheet1", 0, "NonExistent")
    check(missing is None, "find_row returns None for missing value")

    # Get spreadsheet by name
    print("\n── Get spreadsheet by name ──")
    found = await mgr.get_spreadsheet_id("mmclaw-test-template")
    check(found == sid, f"Found sheet by name: {found}")
    not_found = await mgr.get_spreadsheet_id("nonexistent-sheet-xyz")
    check(not_found is None, "Returns None for nonexistent sheet name")

    await mgr.cleanup()

    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 3: Model Operation + API Verification")
    print("=" * 70)
    # ══════════════════════════════════════════════════════════════════

    if not API_KEY:
        print("  SKIP: ANTHROPIC_API_KEY not set, skipping model test")
    else:
        mgr = GoogleSheetsStateManager(config={"task_id": "model_verify"})
        await mgr.setup(sandbox=sandbox)
        res = await mgr.copy_template(TEMPLATE_URL)
        sid = res["sheet_id"]

        # Seed with task-specific data
        await mgr.update_values(sid, "Sheet1!A1:C5", [
            ["Project", "Status", "Owner"],
            ["Website Redesign", "In Progress", "Alice"],
            ["API Migration", "Blocked", "Bob"],
            ["Mobile App", "Not Started", "Charlie"],
            ["Database Upgrade", "Completed", "Alice"],
        ])

        before = await mgr.read_values(sid, "Sheet1")
        print(f"  Before model:")
        for r in before:
            print(f"    {r}")

        # Ask model to make specific changes
        print(f"\n  Calling model ({MODEL})...")
        updates = await call_model(before, (
            "Change the Status of 'API Migration' from 'Blocked' to 'In Progress'. "
            "Change the Owner of 'Mobile App' from 'Charlie' to 'Diana'. "
            "Do NOT modify any other rows."
        ))
        print(f"  Model returned {len(updates)} updates:")
        for u in updates:
            print(f"    {u['cell']} → {u['value']}")

        check(len(updates) >= 2, f"Model returned at least 2 updates: got {len(updates)}")

        # Apply edits
        for u in updates:
            cell = u["cell"]
            if not cell.startswith("Sheet1!"):
                cell = f"Sheet1!{cell}"
            await mgr.update_values(sid, cell, [[u["value"]]])

        # Verify via API
        after = await mgr.read_values(sid, "Sheet1")
        print(f"\n  After model edits:")
        for r in after:
            print(f"    {r}")

        # Build lookup
        headers = after[0]
        rows = {row[0]: dict(zip(headers, row)) for row in after[1:]}

        # Verify model's changes took effect
        check(
            rows["API Migration"]["Status"] == "In Progress",
            f"API Migration Status → In Progress: got '{rows['API Migration']['Status']}'"
        )
        check(
            rows["Mobile App"]["Owner"] == "Diana",
            f"Mobile App Owner → Diana: got '{rows['Mobile App']['Owner']}'"
        )

        # Verify untouched rows are intact
        check(
            rows["Website Redesign"]["Status"] == "In Progress",
            f"Website Redesign unchanged: Status='{rows['Website Redesign']['Status']}'"
        )
        check(
            rows["Website Redesign"]["Owner"] == "Alice",
            f"Website Redesign unchanged: Owner='{rows['Website Redesign']['Owner']}'"
        )
        check(
            rows["Database Upgrade"]["Status"] == "Completed",
            f"Database Upgrade unchanged: Status='{rows['Database Upgrade']['Status']}'"
        )
        check(
            rows["Database Upgrade"]["Owner"] == "Alice",
            f"Database Upgrade unchanged: Owner='{rows['Database Upgrade']['Owner']}'"
        )

        await mgr.cleanup()

    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 4: create_spreadsheet + Model Edit + API Verify")
    print("=" * 70)
    # ══════════════════════════════════════════════════════════════════

    if not API_KEY:
        print("  SKIP: ANTHROPIC_API_KEY not set, skipping model test")
    else:
        mgr = GoogleSheetsStateManager(config={"task_id": "create_model"})
        await mgr.setup(sandbox=sandbox)

        # Create blank sheet and seed budget data (no template needed)
        print("\n── Create + seed ──")
        res = await mgr.create_spreadsheet("Campaign_Budget")
        sid = res["sheet_id"]
        check(sid is not None, f"create_spreadsheet returned id: {sid[:16]}...")

        await mgr.update_values(sid, "Sheet1!A1:E4", [
            ["Campaign", "Budget", "Committed", "Actual", "Note"],
            ["Spring Launch", "15000", "8200", "3000", ""],
            ["Summer Promo", "6000", "2400", "0", ""],
            ["Flash Sale", "9000", "4500", "0", "reserved for homepage"],
        ])

        before = await mgr.read_values(sid, "Sheet1")
        print(f"  Seeded data:")
        for r in before:
            print(f"    {r}")
        check(len(before) == 4, f"has 4 rows: got {len(before)}")

        # Ask model to update budget
        print(f"\n  Calling model ({MODEL})...")
        updates = await call_model(before, (
            "Finance says: add 'PR placement added' to the Note column for Spring Launch, "
            "and change Summer Promo's Committed from 2400 to 3900. "
            "Do NOT change any other cells."
        ))
        print(f"  Model returned {len(updates)} updates:")
        for u in updates:
            print(f"    {u['cell']} → {u['value']}")

        check(len(updates) >= 2, f"at least 2 updates: got {len(updates)}")

        # Apply
        for u in updates:
            cell = u["cell"]
            if not cell.startswith("Sheet1!"):
                cell = f"Sheet1!{cell}"
            await mgr.update_values(sid, cell, [[u["value"]]])

        # Verify
        after = await mgr.read_values(sid, "Sheet1")
        print(f"\n  After model edits:")
        for r in after:
            print(f"    {r}")

        headers = after[0]
        rows = {row[0]: dict(zip(headers, row)) for row in after[1:]}

        check(
            rows["Spring Launch"].get("Note") == "PR placement added",
            f"Spring Launch Note updated: got '{rows['Spring Launch'].get('Note')}'"
        )
        check(
            rows["Summer Promo"].get("Committed") == "3900",
            f"Summer Promo Committed → 3900: got '{rows['Summer Promo'].get('Committed')}'"
        )
        check(
            rows["Flash Sale"].get("Note") == "reserved for homepage",
            f"Flash Sale unchanged: Note='{rows['Flash Sale'].get('Note')}'"
        )
        check(
            rows["Flash Sale"].get("Committed") == "4500",
            f"Flash Sale unchanged: Committed='{rows['Flash Sale'].get('Committed')}'"
        )

        # Find by name
        print("\n── Find by name ──")
        found = await mgr.get_spreadsheet_id("Campaign_Budget")
        check(found == sid, f"found by name: {found}")

        await mgr.cleanup()

    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
