from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from harness.campaign_plan import TrialSpec, expand, load_campaign, manifest_hash
from harness.trial_store import SpendEvent, TrialStore, TrialStoreError

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "tests" / "fixtures" / "campaigns" / "mini.json"
STAMP = "2026-08-29T16:00:00Z"


def _specs() -> tuple[TrialSpec, ...]:
    return expand(load_campaign(MINI))


def _store(tmp_path: Path) -> TrialStore:
    return TrialStore(tmp_path / "results")


def _walk(store: TrialStore, spec: TrialSpec, states: tuple[str, ...]) -> None:
    for state in states:
        store.append_trial(spec, state)


def _spend(
    spec: TrialSpec,
    *,
    kind: str,
    amount: float,
    event_id: str,
    generation: str | None = None,
) -> SpendEvent:
    return SpendEvent(
        event_id=event_id,
        trial_id=spec.trial_id,
        kind=kind,
        amount=amount,
        currency="USD",
        provider_generation_id=generation,
        timestamp=STAMP,
        manifest_hash=spec.manifest_hash,
    )


def test_plan_is_append_only_and_fsynced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[int] = []
    real_fsync = os.fsync

    def spy(fd: int) -> None:
        calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy)
    specs = _specs()
    store = _store(tmp_path)
    store.plan(specs)
    assert calls
    path = store.directory / "trials.jsonl"
    lines = path.read_text().splitlines()
    assert len(lines) == len(specs)
    assert all(json.loads(line)["state"] == "planned" for line in lines)
    reopened = TrialStore(store.directory)
    assert reopened.state_of(specs[0].trial_id) == "planned"
    assert json.loads((store.directory / "manifest.lock.json").read_text())[
        "manifest_hash"
    ] == manifest_hash(load_campaign(MINI))


def test_happy_path_transitions_and_pending_resume(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan(specs)
    first, second = specs[0], specs[1]
    _walk(store, first, ("reserved", "dispatched", "response_saved", "graded", "terminal"))
    store.append_trial(second, "reserved")
    store.plan(specs)
    assert store.state_of(first.trial_id) == "terminal"
    assert store.state_of(second.trial_id) == "reserved"
    pending = store.pending(specs)
    assert first not in pending
    assert second in pending
    assert len(pending) == len(specs) - 1
    reopened = TrialStore(store.directory)
    assert reopened.terminal_ids() == frozenset({first.trial_id})
    assert reopened.state_of(second.trial_id) == "reserved"
    lines = (store.directory / "trials.jsonl").read_text().splitlines()
    assert [json.loads(line)["state"] for line in lines if json.loads(line)["trial_id"] == first.trial_id] == [
        "planned",
        "reserved",
        "dispatched",
        "response_saved",
        "graded",
        "terminal",
    ]


def test_illegal_transition_is_rejected(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan((specs[0],))
    with pytest.raises(TrialStoreError, match="illegal transition planned -> dispatched"):
        store.append_trial(specs[0], "dispatched")
    assert store.state_of(specs[0].trial_id) == "planned"


def test_duplicate_terminal_trial_id_is_rejected(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan((specs[0],))
    _walk(store, specs[0], ("reserved", "terminal"))
    with pytest.raises(TrialStoreError, match="duplicate terminal"):
        store.append_trial(specs[0], "terminal")


def test_first_row_must_be_planned(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.freeze(specs[0].manifest_hash)
    with pytest.raises(TrialStoreError, match="first row must be planned"):
        store.append_trial(specs[0], "reserved")


def test_mixed_manifest_hashes_are_rejected(tmp_path: Path):
    specs = _specs()
    other = TrialSpec(
        trial_id=specs[1].trial_id,
        campaign_id=specs[1].campaign_id,
        task_id=specs[1].task_id,
        suite=specs[1].suite,
        replicate=specs[1].replicate,
        seed=specs[1].seed,
        prompt_hash=specs[1].prompt_hash,
        requested_provider=specs[1].requested_provider,
        order_position=specs[1].order_position,
        manifest_hash="e" * 64,
    )
    store = _store(tmp_path)
    store.plan((specs[0],))
    with pytest.raises(TrialStoreError, match="mixed manifest hashes"):
        store.append_trial(other, "planned")


def test_truncated_rows_are_rejected(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan((specs[0],))
    path = store.directory / "trials.jsonl"
    path.write_bytes(path.read_bytes() + b'{"state":"reserved"')
    with pytest.raises(TrialStoreError, match="truncated"):
        TrialStore(store.directory)
    path.write_bytes(path.read_bytes().rstrip(b"\n") + b'{"oops"')
    with pytest.raises(TrialStoreError, match="truncated"):
        TrialStore(store.directory)


def test_frozen_manifest_edits_are_rejected(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan((specs[0],))
    with pytest.raises(TrialStoreError, match="frozen manifest"):
        store.freeze("f" * 64)
    lock = store.directory / "manifest.lock.json"
    lock.write_text(json.dumps({"manifest_hash": "f" * 64}) + "\n")
    with pytest.raises(TrialStoreError, match="mixed manifest hashes|frozen manifest"):
        TrialStore(store.directory)


def test_spec_mismatch_is_rejected(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan((specs[0],))
    mutated = TrialSpec(
        trial_id=specs[0].trial_id,
        campaign_id=specs[0].campaign_id,
        task_id=specs[0].task_id,
        suite=specs[0].suite,
        replicate=specs[0].replicate,
        seed=99,
        prompt_hash=specs[0].prompt_hash,
        requested_provider=specs[0].requested_provider,
        order_position=specs[0].order_position,
        manifest_hash=specs[0].manifest_hash,
    )
    with pytest.raises(TrialStoreError, match="trial spec mismatch"):
        store.append_trial(mutated, "reserved")


def test_spend_events_are_durable_and_reconcile(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan((specs[0], specs[1]))
    store.append_trial(specs[0], "reserved")
    store.append_spend(_spend(specs[0], kind="reserve", amount=0.05, event_id="e1"))
    store.append_trial(specs[0], "dispatched")
    store.append_trial(specs[0], "response_saved")
    store.append_spend(
        _spend(specs[0], kind="settle", amount=0.012, event_id="e2", generation="gen-1")
    )
    store.append_trial(specs[1], "reserved")
    store.append_spend(_spend(specs[1], kind="reserve", amount=0.05, event_id="e3"))
    store.append_spend(_spend(specs[1], kind="unknown", amount=0.05, event_id="e4"))
    totals = store.spend_totals()
    assert totals["settled"] == pytest.approx(0.012)
    assert totals["unknown"] == pytest.approx(0.05)
    assert totals["open_reserved"] == pytest.approx(0.05)
    assert totals["exposure"] == pytest.approx(0.112)
    reopened = TrialStore(store.directory)
    assert reopened.spend_totals() == totals
    with pytest.raises(TrialStoreError, match="duplicate spend"):
        reopened.append_spend(_spend(specs[0], kind="settle", amount=0.01, event_id="e2"))


def test_reserved_and_dispatched_may_go_terminal_without_a_response(tmp_path: Path):
    specs = _specs()
    store = _store(tmp_path)
    store.plan((specs[0], specs[1]))
    store.append_trial(specs[0], "reserved")
    store.append_trial(specs[0], "terminal")
    store.append_trial(specs[1], "reserved")
    store.append_trial(specs[1], "dispatched")
    store.append_trial(specs[1], "terminal")
    assert store.terminal_ids() == frozenset({specs[0].trial_id, specs[1].trial_id})
    assert store.pending(specs[:2]) == ()
