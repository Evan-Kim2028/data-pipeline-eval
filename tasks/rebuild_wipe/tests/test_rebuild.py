from __future__ import annotations

from warehouse.jobs.rebuild import resume


def test_retry_continues_after_last_ok() -> None:
    staging = {"last_ok": 3, "scratch": 1}
    nxt = resume(staging, last_ok=3)
    assert nxt == 4
    assert staging["last_ok"] == 3
    assert "scratch" in staging


def test_fresh_rebuild_starts_at_zero() -> None:
    staging: dict[str, int] = {}
    assert resume(staging, last_ok=None) == 0


def test_retry_persists_last_ok_when_missing() -> None:
    staging = {"scratch": 1}
    nxt = resume(staging, last_ok=3)
    assert nxt == 4
    assert staging["last_ok"] == 3
    assert staging["scratch"] == 1
    staging = {"last_ok": 3, "scratch": 1}
    assert resume(staging, last_ok=3) == 4
    assert resume(staging, last_ok=3) == 4
    assert staging == {"last_ok": 3, "scratch": 1}
