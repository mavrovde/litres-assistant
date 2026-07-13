# Changelog

## [0.1.0] - Initial release

### Added
- Local web app to browse and back up your own purchased litres.ru library:
  login, per-book selection with search/filter, cover thumbnails, authors,
  audio/book tags, and per-book file sizes with a running estimate of the
  selected total.
- Default format pickers for e-books (epub, fb2, mobi, PDF, txt, rtf, ...)
  and audiobooks (zip-of-mp3 vs. single m4b), applied per book with
  automatic fallback when unavailable.
- Live download progress (status badge, progress bar, per-book log) backed
  by a background job the browser polls, plus a Stop button.
- MCP server (`app/mcp_server.py`) exposing `login_status`,
  `login_to_litres`, `list_library`, and `download_book` as tools.
- Playwright-driven login flow to get past litres.ru's DataDome-style bot
  protection, capturing the app-level API headers the site's own frontend
  attaches to every call and reusing them for subsequent requests.
- A single dedicated worker thread (`session.py`) that every
  Playwright-touching call is routed through, since Playwright's sync API
  only tolerates being used from the thread that created it.
- Configuration via environment variables: `LITRES_APP_PORT`,
  `LITRES_DOWNLOAD_DIR`, `LITRES_SESSION_FILE`,
  `LITRES_DOWNLOAD_TIMEOUT_MS`, `LITRES_HEADLESS` (see README).
- Test suite (pytest) covering format-picking logic, pagination/error
  handling, session restore/login/logout precedence, download-job
  orchestration and cancellation, web routes, and MCP tools -- fully
  mocked, no real Playwright/network involved.
- GitHub Actions workflow running the test suite on every push/PR.
- A GitHub MCP server config (`.mcp.json`) for repo contributors, separate
  from the litres MCP server, authenticated via `gh auth token` at
  connection time rather than a stored secret.

### Fixed
- An explicitly empty book selection was silently treated the same as "no
  filter" and downloaded the entire library instead of nothing.
- A stalled download (observed on a real ~350MB audiobook bundle) could
  hang the whole job for up to 30 minutes; the per-file timeout is now 5
  minutes, and one book failing no longer aborts the rest of the run.
- A thread-affinity bug where the download job's own thread (and the MCP
  server's tool implementations) could run Playwright calls on a different
  thread than the one holding the browser session, crashing outright.
