"""Tests for app/download_job.py: selection filtering, per-book error
resilience, cancellation, and progress-state bookkeeping. The job runs on
session.py's real background executor (submitted via session.submit), so
these tests wait for it to finish rather than calling _run() directly --
that also exercises the real threading path, not just the loop body."""
from __future__ import annotations

import time

from app import download_job
from tests.fakes import FakeLitresClient


def _book(id, title, files=None):
    return {"id": id, "title": title}, files or []


def _make_client(*books_and_files):
    library = []
    files_by_id = {}
    for art, files in books_and_files:
        library.append(art)
        files_by_id[art["id"]] = files
    return FakeLitresClient(library=library, files_by_id=files_by_id)


def wait_until_finished(timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if download_job.snapshot()["status"] != "running":
            return download_job.snapshot()
        time.sleep(0.005)
    raise AssertionError(f"job did not finish within {timeout}s: {download_job.snapshot()}")


TEXT_FILES = [{"id": 100, "extension": "epub", "is_additional": False, "size": 1_000_000}]


def test_start_downloads_everything_when_no_selection():
    client = _make_client(
        _book(1, "Book One", TEXT_FILES),
        _book(2, "Book Two", TEXT_FILES),
    )
    assert download_job.start(client) is True
    result = wait_until_finished()
    assert result["status"] == "done"
    assert result["done"] == 2
    assert sorted(client.download_calls) == [1, 2]


def test_start_downloads_only_the_selected_ids():
    client = _make_client(
        _book(1, "Book One", TEXT_FILES),
        _book(2, "Book Two", TEXT_FILES),
        _book(3, "Book Three", TEXT_FILES),
    )
    download_job.start(client, art_ids={1, 3})
    result = wait_until_finished()
    assert result["status"] == "done"
    assert result["done"] == 2
    assert sorted(client.download_calls) == [1, 3]


def test_start_with_empty_selection_downloads_nothing():
    """Regression test: an explicitly empty selection must not be treated
    the same as "no filter" (which would silently download the whole
    library instead of doing nothing)."""
    client = _make_client(
        _book(1, "Book One", TEXT_FILES),
        _book(2, "Book Two", TEXT_FILES),
    )
    download_job.start(client, art_ids=set())
    result = wait_until_finished()
    assert result["done"] == 0
    assert client.download_calls == []


def test_start_returns_false_if_already_running():
    client = _make_client(_book(1, "Book One", TEXT_FILES))
    assert download_job.start(client) is True
    assert download_job.start(client) is False  # second call is a no-op
    wait_until_finished()


def test_book_with_no_downloadable_file_is_skipped_not_fatal():
    client = _make_client(
        _book(1, "Has files", TEXT_FILES),
        _book(2, "No files at all", []),
    )
    download_job.start(client)
    result = wait_until_finished()
    assert result["status"] == "done"
    assert result["done"] == 1
    skipped = [e for e in result["log"] if e["status"] == "skipped"]
    assert [e["title"] for e in skipped] == ["No files at all"]


def test_one_books_download_failure_does_not_abort_the_rest():
    client = _make_client(
        _book(1, "Will fail", TEXT_FILES),
        _book(2, "Will succeed", TEXT_FILES),
    )
    client.fail_downloads = {1}
    download_job.start(client)
    result = wait_until_finished()
    assert result["status"] == "done"
    assert result["done"] == 1
    errors = [e for e in result["log"] if e["status"] == "error"]
    assert [e["title"] for e in errors] == ["Will fail"]
    assert "Will succeed" in [e["title"] for e in result["log"] if e["status"] == "done"]


def test_job_level_failure_marks_status_error():
    client = FakeLitresClient()

    def broken_iter_library(limit=100):
        raise RuntimeError("session expired")
        yield  # pragma: no cover -- makes this a generator

    client.iter_library = broken_iter_library
    download_job.start(client)
    result = wait_until_finished()
    assert result["status"] == "error"
    assert "session expired" in result["error"]


def test_cancel_stops_the_queue_before_the_next_book():
    client = _make_client(
        _book(1, "First", TEXT_FILES),
        _book(2, "Second", TEXT_FILES),
        _book(3, "Third", TEXT_FILES),
    )
    original_download = client.download_file

    def download_and_cancel_after_first(art_id, release_file_id, filename, dest, subscr=False):
        result = original_download(art_id, release_file_id, filename, dest, subscr)
        if art_id == 1:
            download_job.cancel()
        return result

    client.download_file = download_and_cancel_after_first
    download_job.start(client)
    result = wait_until_finished()

    assert result["status"] == "cancelled"
    assert result["done"] == 1
    assert client.download_calls == [1]  # never reached book 2 or 3


def test_cancel_returns_false_when_nothing_running():
    assert download_job.cancel() is False


def test_total_reflects_selection_size_not_full_library():
    client = _make_client(
        _book(1, "Book One", TEXT_FILES),
        _book(2, "Book Two", TEXT_FILES),
        _book(3, "Book Three", TEXT_FILES),
    )
    download_job.start(client, art_ids={1, 2})
    assert download_job.snapshot()["total"] == 2
    wait_until_finished()


def test_preferred_format_is_passed_through_to_pick_best_file():
    files = [
        {"id": 10, "extension": "epub", "is_additional": False, "size": 1},
        {"id": 11, "extension": "a4.pdf", "is_additional": False, "size": 1},
    ]
    client = _make_client(_book(1, "Multi-format book", files))
    download_job.start(client, preferred_ext="a4.pdf")
    wait_until_finished()
    assert client.download_calls == [1]
    # The chosen file's id (11, the pdf) is only reachable if pick_best_file
    # honored preferred_ext -- assert via the log's recorded extension.
    assert download_job.snapshot()["log"][0]["ext"] == "a4.pdf"


def test_title_falls_back_to_art_id_when_missing():
    client = _make_client(({"id": 42}, TEXT_FILES))
    download_job.start(client)
    result = wait_until_finished()
    assert result["log"][0]["title"] == "42"


def test_snapshot_log_is_a_copy_not_the_live_list():
    client = _make_client(_book(1, "Book One", TEXT_FILES))
    download_job.start(client)
    wait_until_finished()
    snap = download_job.snapshot()
    snap["log"].append({"title": "injected", "status": "done"})
    assert len(download_job.snapshot()["log"]) == 1  # mutation didn't leak back
