from __future__ import annotations

from warehouse.checkpoints.windows import upcoming


def drain(windows: list[str], *, store, commit) -> None:
    for w in upcoming(windows, store.get()):
        store.set(w)
        commit(w)
