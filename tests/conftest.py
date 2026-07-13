"""Shared fixtures. The two autouse ones are safety nets that apply to
every test in the suite: never touch the real OS keychain, never leak the
real .env credentials or a prior test's session/job/cache state into the
next test."""
from __future__ import annotations

import pytest

from app import cache, credentials, download_job, session
from tests.fakes import FakeKeyring


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    """No test should ever touch the real macOS Keychain."""
    fake = FakeKeyring()
    monkeypatch.setattr(credentials, "keyring", fake)
    return fake


@pytest.fixture(autouse=True)
def isolated_module_state(tmp_path, monkeypatch):
    """Reset the module-level singletons in session.py/download_job.py/
    cache.py before and after every test, and keep the real .env's
    credentials (if any) out of the test environment entirely."""
    monkeypatch.delenv("LITRES_LOGIN", raising=False)
    monkeypatch.delenv("LITRES_PASSWORD", raising=False)
    monkeypatch.setattr(session, "SESSION_STATE_PATH", tmp_path / ".litres_session.json")
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / ".litres_cache.json")

    def _reset():
        session._state["client"] = None
        session._state["login"] = None
        download_job._cancel_event.clear()
        download_job._state.update(
            status="idle",
            current_title=None,
            done=0,
            total=None,
            log=[],
            error=None,
            zip_path=None,
        )
        cache._state = None

    _reset()
    yield
    _reset()
