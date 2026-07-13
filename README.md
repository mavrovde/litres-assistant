# litres-downloader

A small, local-only tool to back up **your own purchased litres.ru library**
(books and audiobooks) as a zip file, with one click. Runs entirely on your
own machine -- your login/password never go anywhere except litres.ru
itself.

It comes in two forms that share the same login/session logic:

- **A local web app** -- open a page in your browser, log in once, click
  "Download my library."
- **An MCP server** -- so Claude (or any other MCP client) can list your
  library and download individual books as tools.

---

## Quick start (non-technical)

1. Install [Python 3.11+](https://www.python.org/downloads/) if you don't
   have it already.
2. Open a terminal in this folder and run:
   ```
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/playwright install chromium
   ```
3. Start it:
   ```
   .venv/bin/python run.py
   ```
4. Open **http://127.0.0.1:8420** in your browser, log in with your
   litres.ru account, and click "Download my library."

That's it -- your library downloads as `litres-library.zip`. Your password
is remembered securely in your Mac's Keychain, so you won't need to log in
again next time.

---

## Quick start (developer)

```bash
git clone https://github.com/mavrovde/litres-downloader.git
cd litres-downloader
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium

cp .env.example .env   # optional -- fill in creds to skip the login form
.venv/bin/python run.py
```

The app binds to `127.0.0.1:8420` only (see `run.py`) -- it's a personal,
single-user tool, not a multi-user service.

### Project layout

```
app/
  client.py      LitresClient -- Playwright-driven login + library/file/download API calls
  session.py     shared login/session-restore logic (used by both web.py and mcp_server.py)
  credentials.py password storage via the OS keychain (the `keyring` package)
  web.py         FastAPI app: login form + "download my library" button
  mcp_server.py  MCP server exposing the same functionality as tools
  templates/     the one HTML page the web app serves
run.py           starts the web app (uvicorn, 127.0.0.1:8420)
```

### Why Playwright instead of plain HTTP requests?

litres.ru's login endpoint (`api.litres.ru/foundation/api/auth/login`)
rejects plain scripted `POST` requests with a generic "incorrect
credentials" error regardless of whether the password is right -- the site
sets DataDome-style anti-bot cookies (`__ddg9_`, `__ddg1_`) that only a
real, JS-executing browser can obtain. So `LitresClient` drives an actual
headless Chromium browser (via Playwright) through the real login form.

Being logged in isn't sufficient either: the API also requires several
app-level headers (`app-id`, `session-id`, `client-host`, `ui-currency`,
...) that the site's own frontend code attaches to every call. Rather than
guessing/hardcoding them, `LitresClient` captures them once from a request
the site's own JS fires automatically right after login, and replays them
on subsequent calls.

### Running the MCP server

```bash
.venv/bin/python -m app.mcp_server
```

It communicates over stdio, so normally you don't run it directly --
instead point an MCP client at it. For Claude Desktop, add this to your MCP
config:

```json
{
  "mcpServers": {
    "litres-downloader": {
      "command": "/absolute/path/to/litres-downloader/.venv/bin/python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/litres-downloader"
    }
  }
}
```

Available tools: `login_status`, `login_to_litres(login, password)`,
`list_library(limit)`, `download_book(art_id)`. Downloaded books are saved
to `~/Downloads/litres-library/`.

---

## Configuration

Copy `.env.example` to `.env` and fill in your litres.ru credentials:

```
LITRES_LOGIN=you@example.com
LITRES_PASSWORD=your-litres-password
```

This is **optional** -- without it, you can still log in through the web
UI's login form (or the `login_to_litres` MCP tool), and the session will
be remembered from then on. `.env` just lets the app bootstrap a session
automatically on startup, with no manual login step.

`.env` is gitignored and never committed. See **Security notes** below for
where your credentials/session actually live.

---

## Security notes

- Your password is stored in your OS keychain (via the `keyring` package),
  never in a plaintext file.
- Your browser session (cookies) is cached in `.litres_session.json` at the
  project root, so you don't have to log in on every run. This file is
  gitignored -- **do not commit or share it**, it's equivalent to being
  logged into your account.
- `.env`, `.venv/`, and `.litres_session.json` are all gitignored.
- Both the web app and the MCP server are single-user and local-only by
  design. There is no multi-user support, and none is planned -- see the
  architecture notes above for why (this is intentionally *not* built to
  hold other people's credentials).

---

## Known limitations

Tracked as [GitHub issues](https://github.com/mavrovde/litres-downloader/issues):

- Whole-audiobook downloads can be ~2GB and are currently buffered in
  memory before being written to disk.
- The web UI's "download my library" runs synchronously with no live
  progress feedback in the browser (console logs only).
- Response-shape assumptions for the library/file-listing endpoints were
  confirmed against a limited sample of real library items; edge cases in
  large/varied libraries (podcasts, webtoons, DRM-restricted items) may need
  follow-up fixes.
