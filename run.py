"""Run the local LitRes library downloader.

Host is intentionally not configurable: this app holds your logged-in
litres.ru session, so it's bound to 127.0.0.1 (localhost-only) by design,
not as a tunable default. Port can be changed via LITRES_APP_PORT if 8420
is taken by something else.
"""
import logging
import os

from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LITRES_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    load_dotenv()
    port = int(os.environ.get("LITRES_APP_PORT", "8420"))
    # log_config=None: uvicorn's own dictConfig would otherwise reset/replace
    # the logging setup above (root handler + format) once it starts, which
    # is why app.* log lines (session restore, download progress, ...)
    # wouldn't show up even at INFO level.
    #
    # reload_dirs=["app"]: without this, uvicorn watches the whole project
    # (including tests/) -- editing a test file then restarts the live
    # server mid-session, which silently kills anything in progress (e.g. a
    # download): the reload replaces the whole process, wiping every
    # module-level in-memory state (session, download_job, cache).
    uvicorn.run("app.web:app", host="127.0.0.1", port=port, reload=True, reload_dirs=["app"], log_config=None)
