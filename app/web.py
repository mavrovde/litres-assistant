"""Minimal local, single-user web app: log in once, click a button, get your
whole litres.ru library as a zip.

Intentionally bound to 127.0.0.1 only (see run.py) -- this is a personal
tool for the account owner, not a multi-user service.
"""
from __future__ import annotations

import os
import tempfile
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from fastapi import FastAPI, Form
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import credentials
from .client import LitresAuthError, LitresClient

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

SESSION_STATE_PATH = Path(__file__).parent.parent / ".litres_session.json"

_state = {"client": None, "login": None}


def _restore_session() -> None:
    # Reuse a previously saved browser session (cookies incl. the
    # DataDome-style challenge cookies) first, so we don't drive a fresh
    # login on every restart.
    if SESSION_STATE_PATH.exists():
        client = LitresClient(storage_state_path=SESSION_STATE_PATH)
        if client.is_logged_in():
            saved = credentials.load_last()
            _state["client"] = client
            _state["login"] = saved[0] if saved else None
            return
        client.close()

    saved = credentials.load_last()
    if not saved:
        env_login, env_password = os.environ.get("LITRES_LOGIN"), os.environ.get("LITRES_PASSWORD")
        if not (env_login and env_password):
            return
        saved = (env_login, env_password)
    login, password = saved
    client = LitresClient()
    try:
        client.login(login, password)
    except LitresAuthError:
        client.close()
        return
    client.save_state(SESSION_STATE_PATH)
    _state["client"], _state["login"] = client, login


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sync Playwright refuses to run inside an asyncio loop, and FastAPI's
    # lifespan runs directly on the event loop thread -- push it to a
    # worker thread, same as Starlette does for sync route handlers.
    await anyio.to_thread.run_sync(_restore_session)
    yield
    if _state["client"] is not None:
        await anyio.to_thread.run_sync(_state["client"].close)


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"logged_in": _state["client"] is not None, "login": _state["login"], "error": None},
    )


@app.post("/login")
def do_login(request: Request, login: str = Form(...), password: str = Form(...)):
    client = LitresClient()
    try:
        client.login(login, password)
    except LitresAuthError as exc:
        client.close()
        return templates.TemplateResponse(
            request,
            "index.html",
            {"logged_in": False, "login": None, "error": str(exc)},
            status_code=401,
        )
    if _state["client"] is not None:
        _state["client"].close()
    client.save_state(SESSION_STATE_PATH)
    credentials.save(login, password)
    _state["client"], _state["login"] = client, login
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def do_logout():
    if _state["login"]:
        credentials.forget(_state["login"])
    if _state["client"] is not None:
        _state["client"].close()
    SESSION_STATE_PATH.unlink(missing_ok=True)
    _state["client"], _state["login"] = None, None
    return RedirectResponse("/", status_code=303)


@app.get("/download")
def download_library():
    client: LitresClient = _state["client"]
    if client is None:
        return RedirectResponse("/", status_code=303)

    workdir = Path(tempfile.mkdtemp(prefix="litres-"))
    zip_path = workdir / "litres-library.zip"

    # Audiobook bundles/text formats are already compressed -- STORED avoids
    # burning CPU re-deflating gigabytes of mp3/epub for no size benefit.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for art in client.iter_library():
            art_id = art.get("id")
            title = art.get("title") or str(art_id)
            files = client.get_files(art_id)
            best = client.pick_best_file(files)
            if best is None:
                print(f"skip (no downloadable file): {title}")
                continue
            release_file_id = best["id"]
            ext = client.file_extension(best)
            safe_title = "".join(c for c in title if c.isalnum() or c in " ._-")[:150]
            dest = workdir / f"{safe_title}.{ext}"
            print(f"downloading: {title} ({ext}, {best.get('size', 0) / 1e6:.1f} MB)")
            client.download_file(art_id, release_file_id, dest.name, dest)
            zf.write(dest, arcname=dest.name)
            dest.unlink()

    return FileResponse(zip_path, filename="litres-library.zip", media_type="application/zip")
