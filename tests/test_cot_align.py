from __future__ import annotations

from harness.cot_align import (
    hop0_score,
    hunk_score,
    is_meta_hop,
    mechanism_hops,
    score_trial,
)


def test_meta_hops_are_instruction_echo():
    hops = [
        {"text": "The bug: next_chunk clears staging."},
        {"text": "Provide reasoning claims and unified diff."},
        {"text": "Diff:"},
        {"text": "```\n--- a/x\n+return last_ok\n```"},
    ]
    assert is_meta_hop(hops[1])
    assert is_meta_hop(hops[2])
    assert is_meta_hop(hops[3])
    assert not is_meta_hop(hops[0])
    assert [h["text"] for h in mechanism_hops(hops)] == [hops[0]["text"]]


def test_hop0_names_symptom_before_trap():
    spec = {
        "symptom": ("processing_at", "event_at", "late"),
        "gold": ("event_at", "start", "end"),
        "trap": ("lateness", "in_processing_window"),
        "edit": ("processing_at", "event_at"),
        "must_hunk": ("lateness",),
    }
    row = hop0_score(
        "Late facts drop because ingest gates on processing_at instead of event_at.",
        spec,
    )
    assert row["hop0_label"] == "gold_named"
    assert "processing_at" in row["hop0_symptom"]
    assert row["hop0_trap"] == []


def test_rebuild_hunk_implements_incomplete_claim():
    spec = {
        "symptom": ("clear", "staging", "restart"),
        "gold": ("last_ok", "persist"),
        "trap": ("restart",),
        "edit": ("last_ok",),
        "must_hunk": ("last_ok + 1",),
    }
    claim = "next_chunk should return last_ok or 0 and must not clear staging."
    diff = (
        "diff --git a/warehouse/incremental/rebuild.py b/warehouse/incremental/rebuild.py\n"
        "--- a/warehouse/incremental/rebuild.py\n"
        "+++ b/warehouse/incremental/rebuild.py\n"
        "@@\n"
        "-    staging.clear()\n"
        "-    return 0\n"
        "+    return last_ok if last_ok is not None else 0\n"
    )
    row = hunk_score(claim, diff, spec)
    assert "last_ok" in row["hunk_edit"]
    assert "last_ok + 1" not in row["hunk_edit"]
    assert row["hunk_align"] == "implements_claim"
    assert row["vs_gold_edit"] == "trap_absent"


def test_score_trial_skips_unknown_task():
    assert score_trial(task="timestamptz_cutoff", hops=[], diff="") is None
