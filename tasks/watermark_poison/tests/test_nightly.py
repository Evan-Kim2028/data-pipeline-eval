from __future__ import annotations

from warehouse.checkpoints.nightly import drain
from warehouse.checkpoints.store import WatermarkStore


def test_happy_path_watermarks_last_window() -> None:
    store = WatermarkStore("")
    done: list[str] = []
    drain(
        ["2026-05-01", "2026-05-02", "2026-05-03"],
        store=store,
        commit=done.append,
    )
    assert done == ["2026-05-01", "2026-05-02", "2026-05-03"]
    assert store.get() == "2026-05-03"


def test_failed_commit_does_not_skip_the_window() -> None:
    store = WatermarkStore("2026-05-01")
    done: list[str] = []

    def commit(w: str) -> None:
        if w == "2026-05-03":
            raise RuntimeError("writer died")
        done.append(w)

    try:
        drain(
            ["2026-05-01", "2026-05-02", "2026-05-03"],
            store=store,
            commit=commit,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("commit failure must surface")
    assert done == ["2026-05-02"]
    assert store.get() == "2026-05-02"


def test_second_run_resumes_at_failed_window() -> None:
    store = WatermarkStore("2026-05-01")
    done: list[str] = []

    def commit(w: str) -> None:
        if w == "2026-05-03" and done.count("2026-05-02") == 1:
            raise RuntimeError("writer died")
        done.append(w)

    try:
        drain(["2026-05-01", "2026-05-02", "2026-05-03"], store=store, commit=commit)
    except RuntimeError:
        pass
    drain(["2026-05-01", "2026-05-02", "2026-05-03"], store=store, commit=done.append)
    assert done == ["2026-05-02", "2026-05-03"]
    assert store.get() == "2026-05-03"
