"""MCP server exposing the LitRes library as tools for MCP clients (e.g.
Claude Desktop), reusing the same session/login logic as the web UI.

Run standalone over stdio:
    .venv/bin/python -m app.mcp_server

All tools are `async def` and offload their actual work via
`anyio.to_thread.run_sync` -- FastMCP calls tool functions directly on its
own asyncio event loop thread (unlike Starlette, which offloads plain `def`
routes to a worker thread automatically), and sync Playwright refuses to
run on a thread that has an active event loop.
"""
from __future__ import annotations

from pathlib import Path

import anyio
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from . import session
from .client import LitresAuthError

load_dotenv()

mcp = FastMCP("litres-downloader")

DOWNLOAD_DIR = Path.home() / "Downloads" / "litres-library"


def _client():
    client = session.current_client()
    if client is None:
        session.restore_session()
        client = session.current_client()
    if client is None:
        raise RuntimeError(
            "Not logged in to litres.ru. Call login_to_litres(login, password) "
            "first, or set LITRES_LOGIN/LITRES_PASSWORD in .env."
        )
    return client


@mcp.tool()
async def login_status() -> dict:
    """Report whether there's an active, working litres.ru session."""

    def _sync():
        client = session.current_client()
        if client is None:
            session.restore_session()
            client = session.current_client()
        return {"logged_in": client is not None, "login": session.current_login()}

    return await anyio.to_thread.run_sync(_sync)


@mcp.tool()
async def login_to_litres(login: str, password: str) -> dict:
    """Log into litres.ru and persist the session (cookies + keychain) for future calls."""

    def _sync():
        try:
            session.login(login, password)
        except LitresAuthError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "login": login}

    return await anyio.to_thread.run_sync(_sync)


@mcp.tool()
async def list_library(limit: int = 50) -> list:
    """List up to `limit` items from the logged-in user's purchased litres.ru library."""

    def _sync():
        client = _client()
        items = []
        for art in client.iter_library(limit=limit):
            items.append({"id": art.get("id"), "title": art.get("title")})
            if len(items) >= limit:
                break
        return items

    return await anyio.to_thread.run_sync(_sync)


@mcp.tool()
async def download_book(art_id: int) -> dict:
    """Download one purchased book/audiobook by its art id to a local
    folder (~/Downloads/litres-library), returning the saved file path."""

    def _sync():
        client = _client()
        files = client.get_files(art_id)
        best = client.pick_best_file(files)
        if best is None:
            return {"ok": False, "error": f"No downloadable file for art {art_id}"}
        ext = client.file_extension(best)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        dest = DOWNLOAD_DIR / f"{art_id}.{ext}"
        client.download_file(art_id, best["id"], dest.name, dest)
        return {"ok": True, "path": str(dest), "size_bytes": dest.stat().st_size}

    return await anyio.to_thread.run_sync(_sync)


if __name__ == "__main__":
    mcp.run()
