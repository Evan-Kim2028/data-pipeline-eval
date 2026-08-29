from __future__ import annotations

from warehouse.checkpoints.nightly import drain
from warehouse.checkpoints.store import WatermarkStore


def test_fail_on_first_window_keeps_prior_watermark() -> None:
    store = WatermarkStore("2026-04-30")

    def commit(w: str) -> None:
        raise RuntimeError("writer died")

    try:
        drain(["2026-05-01"], store=store, commit=commit)
    except RuntimeError:
        pass
    else:
        raise AssertionError("commit failure must surface")
    assert store.get() == "2026-04-30"
