# External Credentials Setup

This doc walks through setting up the two external-service credentials that ClawMark tasks need: **Notion** (for `notion` environment tasks) and **Google Sheets / Drive** (for `google_sheets` environment tasks). Both credential files are already listed in `.gitignore` and must never be committed.

The flows here are adapted from two related benchmarks:

- **Notion setup** — adapted from [MCPMark](https://github.com/eval-sys/mcpmark) (`docs/mcp/notion.md`).
- **Google Sheets setup** — adapted from [Toolathlon](https://github.com/hkust-nlp/Toolathlon) (`global_preparation/how2register_accounts.md`).

The env var names and file paths below are ClawMark-specific.

---

## 1. Notion

ClawMark uses **two separate Notion integrations**:

| Role | Env var | Purpose |
|---|---|---|
| Admin | `NOTION_ADMIN_KEY` | Framework uses it to create/delete databases and pages during stage setup |
| Agent | `NOTION_AGENT_KEY` | Actual token the model-facing tools use |

And **two parent pages** to isolate source templates from the current eval run:

| Page | Env var | Purpose |
|---|---|---|
| Source Hub | `NOTION_SOURCE_PAGE` (default: `ClawMark Source Hub`) | Master templates that get cloned into the eval hub each run |
| Eval Hub | `NOTION_EVAL_PAGE` (default: `ClawMark Eval Hub`) | Working copy that gets wiped and re-seeded for each task |

### 1.1 Set your Notion workspace language to English

The framework uses Playwright to drive the Notion web UI for a few operations. Non-English UI breaks element selectors. Go to **Settings → Language & region → English**.

### 1.2 Create the two integrations

1. Open [Notion Integrations](https://www.notion.so/profile/integrations).
2. Click **New integration** → name it `ClawMark Admin` → **Internal** → copy the **Internal Integration Secret**. This is your `NOTION_ADMIN_KEY`.
3. Create a second integration named `ClawMark Agent` the same way → copy its secret → this is your `NOTION_AGENT_KEY`.

### 1.3 Create and share the two hub pages

1. In your Notion workspace, create an empty page titled exactly `ClawMark Source Hub` (or whatever you set `NOTION_SOURCE_PAGE` to).
2. Click `⋯` top-right → **Connections → Connect to** → add both `ClawMark Admin` and `ClawMark Agent` at **Full Access**.
3. Create a second empty page titled `ClawMark Eval Hub` (matches `NOTION_EVAL_PAGE`) and share it with both integrations the same way.

### 1.4 Fill in `.env`

```bash
NOTION_ADMIN_KEY=ntn_...
NOTION_AGENT_KEY=ntn_...
NOTION_SOURCE_PAGE=ClawMark Source Hub
NOTION_EVAL_PAGE=ClawMark Eval Hub
# Optional:
NOTION_STATE_FILE=notion_state.json          # where the framework caches runtime IDs
NOTION_PLAYWRIGHT_HEADLESS=true              # set false to watch the Playwright automation
```

### 1.5 First-run browser login

Before your first task run that touches Notion, Playwright needs a signed-in browser profile:

```bash
uv run playwright install chromium
```

Subsequent task runs will reuse the cached profile.

---

## 2. Google Sheets / Drive

ClawMark's Google Sheets tasks need a user-authorized refresh token, minted once via OAuth. The end state you want is a file at `configs/google_credentials.json` that contains refresh-token material, which the framework reads via `GOOGLE_CREDENTIALS_PATH`.

The setup is two JSONs:

| File | Content | When |
|---|---|---|
| `configs/gcp-oauth.keys.json` | OAuth 2.0 Client ID client secret (downloaded from Google Cloud Console) | One-time, kept locally |
| `configs/google_credentials.json` | User access + refresh token (generated from the above by `scripts/google_auth.py`) | Auto-refreshes; re-mint when refresh token dies |

Both files are in `.gitignore`. Only `configs/google_credentials.json` is read by the runtime.

### 2.1 Create a Google Cloud project and enable the APIs

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or pick an existing one).
2. **APIs & Services → Library**, enable:
   - **Google Drive API**
   - **Google Sheets API**

### 2.2 Configure the OAuth consent screen

1. **APIs & Services → OAuth consent screen → External → Create**
2. Fill in app name, user support email, developer contact.
3. In **Scopes**, add:
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/spreadsheets`
4. Under **Test users**, add the Google account you'll actually use to authorize.
5. Save and return to the dashboard. If the app is in **Testing** mode, refresh tokens will expire after 7 days — either publish the app, or plan to re-bootstrap weekly.

### 2.3 Create an OAuth 2.0 Client ID (Web application)

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. **Application type: Web application**, name it anything.
3. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:3000/oauth2callback
   ```
   This exact URI must match — `scripts/google_auth.py` listens on that port.
4. **Create** → a modal pops up with a **Download JSON** link. Download it.
5. Move and rename:
   ```bash
   mv ~/Downloads/client_secret_*.json configs/gcp-oauth.keys.json
   ```

### 2.4 Mint the refresh token

```bash
uv run python scripts/google_auth.py
```

The script will:
1. Open `http://localhost:3000/oauth2callback` and launch your system browser to Google's consent page.
2. Prompt you to sign in with the account you added as a test user above.
3. Write the resulting access/refresh token pair to `configs/google_credentials.json`.

### 2.5 Point `.env` at the generated file

```bash
GOOGLE_CREDENTIALS_PATH=configs/google_credentials.json
```

This is the only path the runtime needs. `configs/gcp-oauth.keys.json` is no longer read at eval time, but keep it locally — when the refresh token dies (7-day expiry on Testing apps, or after a Google Cloud security event), re-running `scripts/google_auth.py` needs `gcp-oauth.keys.json` again.

### 2.6 Test the connection

```bash
# Spin up local mocks (separate from runtime sandboxing)
docker compose -f docker/docker-compose.yaml up -d
uv run python tests/test_google_sheets_lifecycle.py   # read/write/delete round-trip
uv run python tests/test_google_sheets_full.py        # full round-trip incl. model call
docker compose -f docker/docker-compose.yaml down
```

If auth is wrong you'll see a 401 or `invalid_grant` error — in that case re-run `scripts/google_auth.py` to re-mint.

---

## Security notes

- **Never commit `configs/gcp-oauth.keys.json` or `configs/google_credentials.json`.** Both are in `.gitignore`, but double-check with `git status` before every `git add -A`.
- If you accidentally leak the OAuth client secret (even in a Slack message or screenshot): go to Google Cloud Console → Credentials → your OAuth client → **Reset Secret**, then re-download `gcp-oauth.keys.json` and re-run `scripts/google_auth.py`.
- Notion integration tokens can be revoked at [Notion Integrations](https://www.notion.so/profile/integrations) → pick the integration → **Danger zone → Delete integration**, then create a fresh one.
