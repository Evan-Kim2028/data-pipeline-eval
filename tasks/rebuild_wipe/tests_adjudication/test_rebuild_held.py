from __future__ import annotations

from warehouse.jobs.rebuild import resume


def test_zero_is_a_real_checkpoint() -> None:
    staging = {"last_ok": 0, "scratch": 9}
    assert resume(staging, last_ok=0) == 1
    assert staging["last_ok"] == 0
    assert staging["scratch"] == 9
