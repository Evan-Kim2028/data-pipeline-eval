from __future__ import annotations

from warehouse.incremental.basis import merge_incoming


def test_second_chunk_against_accumulated_rows_does_unique() -> None:
    calls: list[int] = []

    def unique_fn(rows):
        calls.append(len(rows))
        seen: set[str] = set()
        out = []
        for row in rows:
            if row["event_id"] in seen:
                continue
            seen.add(row["event_id"])
            out.append(row)
        return out

    first = merge_incoming([], [{"event_id": "a"}], unique_fn)
    assert calls == []
    second = merge_incoming(first, [{"event_id": "b"}], unique_fn)
    assert calls == [2]
    assert [r["event_id"] for r in second] == ["a", "b"]
