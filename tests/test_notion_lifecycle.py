"""Smoke test for NotionStateManager lifecycle.

Usage:
    uv run python tests/test_notion_lifecycle.py
"""
import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

from clawmark.state.notion import NotionStateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class _NoopSandbox:
    async def exec(self, *a, **kw): pass
    async def upload_dir(self, *a, **kw): pass
    async def download_dir(self, *a, **kw): pass
    async def upload_file(self, *a, **kw): pass
    async def download_file(self, *a, **kw): pass


TEMPLATE_SUBPAGE = "Online Resume"


async def main():
    sandbox = _NoopSandbox()
    mgr = NotionStateManager(config={})

    # ── SETUP ──
    print("\n" + "=" * 60)
    print("SETUP: initialize Notion clients")
    print("=" * 60)
    await mgr.setup(sandbox=sandbox)

    # ── COPY PAGE ──
    print("\n" + "=" * 60)
    print("COPY PAGE: duplicate template → move to eval")
    print("=" * 60)
    metadata = await mgr.copy_page(template=TEMPLATE_SUBPAGE)
    print(f"  page_id: {metadata['page_id']}")
    print(f"  page_url: {metadata['page_url']}")

    # ── READ PAGE ──
    print("\n" + "=" * 60)
    print("READ: read page content")
    print("=" * 60)
    content = await mgr.read_page()
    print(f"  content length: {len(content)}")

    # ── APPEND BLOCKS ──
    print("\n" + "=" * 60)
    print("APPEND: add a test block")
    print("=" * 60)
    await mgr.append_blocks([
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Injected by test script"}}],
            },
        }
    ])

    # ── READ AGAIN ──
    print("\n" + "=" * 60)
    print("READ (after append): verify block was added")
    print("=" * 60)
    content2 = await mgr.read_page()
    print(f"  content length: {len(content2)}")
    if "Injected by test script" in content2:
        print("  ✓ Injected block found in content!")
    else:
        print("  ✗ Injected block NOT found — check page manually")

    # ── CLEANUP (copy_page test) ──
    print("\n" + "=" * 60)
    print("CLEANUP: delete duplicated page")
    print("=" * 60)
    await mgr.cleanup()
    print("  Done.")

    # ── CREATE PAGE (API-only, no Playwright) ──
    print("\n" + "=" * 60)
    print("CREATE PAGE: create page via API (no template)")
    print("=" * 60)
    page_info = await mgr.create_page("Test ATS Page")
    print(f"  page_id: {page_info['page_id']}")
    print(f"  page_url: {page_info['page_url']}")

    # ── CREATE DATABASE ──
    print("\n" + "=" * 60)
    print("CREATE DATABASE: create inline database in page")
    print("=" * 60)
    db_id = await mgr.create_database("test_pipeline", {
        "Name": {"title": {}},
        "Status": {"select": {"options": [
            {"name": "Open"}, {"name": "Closed"},
        ]}},
        "Email": {"email": {}},
        "Notes": {"rich_text": {}},
    })
    print(f"  database_id: {db_id}")

    # ── ADD ROWS ──
    print("\n" + "=" * 60)
    print("ADD ROWS: insert 2 rows into database")
    print("=" * 60)
    row1_id = await mgr.add_database_row("test_pipeline", {
        "Name": {"title": [{"text": {"content": "Alice"}}]},
        "Status": {"select": {"name": "Open"}},
        "Email": {"email": "alice@example.com"},
        "Notes": {"rich_text": [{"text": {"content": "First candidate"}}]},
    })
    row2_id = await mgr.add_database_row("test_pipeline", {
        "Name": {"title": [{"text": {"content": "Bob"}}]},
        "Status": {"select": {"name": "Open"}},
        "Email": {"email": "bob@example.com"},
        "Notes": {"rich_text": [{"text": {"content": "Second candidate"}}]},
    })
    print(f"  row1: {row1_id}")
    print(f"  row2: {row2_id}")

    # ── QUERY DATABASE ──
    print("\n" + "=" * 60)
    print("QUERY: read all rows from database")
    print("=" * 60)
    rows = await mgr.query_db("test_pipeline")
    print(f"  rows: {len(rows)}")
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    print("  ✓ 2 rows found")

    # ── UPDATE ROW ──
    print("\n" + "=" * 60)
    print("UPDATE ROW: change Bob's status to Closed")
    print("=" * 60)
    await mgr.update_db_row(row2_id, {
        "Status": {"select": {"name": "Closed"}},
    })
    rows_after = await mgr.query_db("test_pipeline")
    for r in rows_after:
        status = r.get("properties", {}).get("Status", {}).get("select", {})
        name_parts = r.get("properties", {}).get("Name", {}).get("title", [])
        name = "".join(t.get("plain_text", "") for t in name_parts)
        if name == "Bob":
            assert status.get("name") == "Closed", f"Expected Closed, got {status}"
            print("  ✓ Bob's status updated to Closed")

    # ── CLEANUP (create_page test) ──
    print("\n" + "=" * 60)
    print("CLEANUP: delete created page + database")
    print("=" * 60)
    await mgr.cleanup()
    print("  Done.")

    print("\n" + "=" * 60)
    print("ALL STEPS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
