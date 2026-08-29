"""Append-only campaign trial rows and spend events. One writer, fsync per transition."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from campaign_plan import TrialSpec
from contracts import SCHEMA_VERSION, encode_json

STATES = (
    "planned",
    "reserved",
    "dispatched",
    "response_saved",
    "graded",
    "terminal",
)
SPEND_KINDS = frozenset({"reserve", "settle", "release", "unknown"})
LEGAL = {
    "planned": frozenset({"reserved", "terminal"}),
    "reserved": frozenset({"dispatched", "terminal"}),
    "dispatched": frozenset({"response_saved", "terminal"}),
    "response_saved": frozenset({"graded"}),
    "graded": frozenset({"terminal"}),
    "terminal": frozenset(),
}


class TrialStoreError(ValueError):
    pass


@dataclass(frozen=True)
class TrialRow:
    schema_version: str
    state: str
    spec: TrialSpec

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise TrialStoreError("unknown schema_version")
        if self.state not in STATES:
            raise TrialStoreError(f"unknown state {self.state}")


@dataclass(frozen=True)
class SpendEvent:
    event_id: str
    trial_id: str
    kind: str
    amount: float
    currency: str
    provider_generation_id: str | None
    timestamp: str
    manifest_hash: str

    def __post_init__(self) -> None:
        if self.kind not in SPEND_KINDS:
            raise TrialStoreError(f"unknown spend kind {self.kind}")
        if self.amount < 0:
            raise TrialStoreError("spend amount cannot be negative")
        if not self.event_id or not self.trial_id or not self.timestamp:
            raise TrialStoreError("spend event identity fields are required")
        if self.currency != "USD":
            raise TrialStoreError("currency must be USD")
        if len(self.manifest_hash) != 64:
            raise TrialStoreError("manifest_hash must be a 64-char hex digest")


def _row_payload(row: TrialRow) -> dict[str, Any]:
    spec = json.loads(encode_json(row.spec))
    spec["schema_version"] = row.schema_version
    spec["state"] = row.state
    return spec


def _spec_from_mapping(data: Mapping[str, Any]) -> TrialSpec:
    return TrialSpec(
        trial_id=str(data["trial_id"]),
        campaign_id=str(data["campaign_id"]),
        task_id=str(data["task_id"]),
        suite=str(data["suite"]),
        replicate=int(data["replicate"]),
        seed=int(data["seed"]),
        prompt_hash=str(data["prompt_hash"]),
        requested_provider=str(data["requested_provider"]),
        order_position=int(data["order_position"]),
        manifest_hash=str(data["manifest_hash"]),
    )


def _row_from_mapping(data: Mapping[str, Any]) -> TrialRow:
    required = {
        "schema_version",
        "state",
        "trial_id",
        "campaign_id",
        "task_id",
        "suite",
        "replicate",
        "seed",
        "prompt_hash",
        "requested_provider",
        "order_position",
        "manifest_hash",
    }
    extra = set(data) - required
    if extra:
        raise TrialStoreError(f"unknown trial fields {sorted(extra)}")
    missing = required - set(data)
    if missing:
        raise TrialStoreError(f"missing trial fields {sorted(missing)}")
    return TrialRow(
        schema_version=str(data["schema_version"]),
        state=str(data["state"]),
        spec=_spec_from_mapping(data),
    )


def _spend_from_mapping(data: Mapping[str, Any]) -> SpendEvent:
    required = {
        "event_id",
        "trial_id",
        "kind",
        "amount",
        "currency",
        "provider_generation_id",
        "timestamp",
        "manifest_hash",
    }
    extra = set(data) - required
    if extra:
        raise TrialStoreError(f"unknown spend fields {sorted(extra)}")
    missing = required - set(data)
    if missing:
        raise TrialStoreError(f"missing spend fields {sorted(missing)}")
    gen = data["provider_generation_id"]
    return SpendEvent(
        event_id=str(data["event_id"]),
        trial_id=str(data["trial_id"]),
        kind=str(data["kind"]),
        amount=float(data["amount"]),
        currency=str(data["currency"]),
        provider_generation_id=None if gen is None else str(gen),
        timestamp=str(data["timestamp"]),
        manifest_hash=str(data["manifest_hash"]),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    blob = path.read_bytes()
    if not blob:
        return []
    if not blob.endswith(b"\n"):
        raise TrialStoreError(f"truncated {path.name}")
    rows: list[dict[str, Any]] = []
    for line in blob.splitlines():
        if not line.strip():
            raise TrialStoreError(f"truncated {path.name}")
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TrialStoreError(f"truncated {path.name}") from exc
        if not isinstance(parsed, dict):
            raise TrialStoreError(f"truncated {path.name}")
        rows.append(parsed)
    return rows


def _append_jsonl(path: Path, obj: Any) -> None:
    line = encode_json(obj) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_replace(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


class TrialStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock_path = directory / "manifest.lock.json"
        self._trials_path = directory / "trials.jsonl"
        self._spend_path = directory / "spend.jsonl"
        self._states: dict[str, str] = {}
        self._specs: dict[str, TrialSpec] = {}
        self._rows: list[TrialRow] = []
        self._events: list[SpendEvent] = []
        self._event_ids: set[str] = set()
        self._manifest_hash: str | None = None
        self._load()

    def _load(self) -> None:
        if self._lock_path.is_file():
            try:
                locked = json.loads(self._lock_path.read_text())
            except json.JSONDecodeError as exc:
                raise TrialStoreError("truncated manifest.lock.json") from exc
            if not isinstance(locked, dict) or set(locked) != {"manifest_hash"}:
                raise TrialStoreError("invalid manifest.lock.json")
            digest = str(locked["manifest_hash"])
            if len(digest) != 64:
                raise TrialStoreError("frozen manifest mismatch")
            self._manifest_hash = digest
        for data in _read_jsonl(self._trials_path):
            row = _row_from_mapping(data)
            self._apply_row(row, persist=False)
        for data in _read_jsonl(self._spend_path):
            event = _spend_from_mapping(data)
            self._apply_spend(event, persist=False)

    def _apply_row(self, row: TrialRow, *, persist: bool) -> None:
        spec = row.spec
        if self._manifest_hash is None:
            self._manifest_hash = spec.manifest_hash
        elif spec.manifest_hash != self._manifest_hash:
            raise TrialStoreError("mixed manifest hashes")
        current = self._states.get(spec.trial_id)
        if current is None:
            if row.state != "planned":
                raise TrialStoreError("first row must be planned")
        elif current == "terminal":
            raise TrialStoreError(f"duplicate terminal trial id {spec.trial_id}")
        elif row.state not in LEGAL[current]:
            raise TrialStoreError(f"illegal transition {current} -> {row.state}")
        existing = self._specs.get(spec.trial_id)
        if existing is not None and existing != spec:
            raise TrialStoreError("trial spec mismatch")
        if persist:
            _append_jsonl(self._trials_path, _row_payload(row))
        self._states[spec.trial_id] = row.state
        self._specs[spec.trial_id] = spec
        self._rows.append(row)

    def _apply_spend(self, event: SpendEvent, *, persist: bool) -> None:
        if event.trial_id not in self._specs:
            raise TrialStoreError(f"unknown trial {event.trial_id}")
        if self._manifest_hash is None:
            self._manifest_hash = event.manifest_hash
        elif event.manifest_hash != self._manifest_hash:
            raise TrialStoreError("mixed manifest hashes")
        if event.event_id in self._event_ids:
            raise TrialStoreError(f"duplicate spend event {event.event_id}")
        if persist:
            _append_jsonl(self._spend_path, event)
        self._event_ids.add(event.event_id)
        self._events.append(event)

    def freeze(self, manifest_hash: str) -> None:
        if self._manifest_hash is not None and self._manifest_hash != manifest_hash:
            raise TrialStoreError("frozen manifest mismatch")
        payload = json.dumps(
            {"manifest_hash": manifest_hash}, separators=(",", ":"), sort_keys=True
        )
        if self._lock_path.is_file():
            locked = json.loads(self._lock_path.read_text())
            if locked.get("manifest_hash") != manifest_hash:
                raise TrialStoreError("frozen manifest mismatch")
            self._manifest_hash = manifest_hash
            return
        _fsync_replace(self._lock_path, payload + "\n")
        self._manifest_hash = manifest_hash

    def plan(self, specs: tuple[TrialSpec, ...]) -> None:
        if not specs:
            raise TrialStoreError("empty plan")
        hashes = {item.manifest_hash for item in specs}
        if len(hashes) != 1:
            raise TrialStoreError("mixed manifest hashes")
        self.freeze(next(iter(hashes)))
        for spec in specs:
            current = self._states.get(spec.trial_id)
            if current is None:
                self.append_trial(spec, "planned")
                continue
            if self._specs[spec.trial_id] != spec:
                raise TrialStoreError("trial spec mismatch")

    def append_trial(self, spec: TrialSpec, state: str) -> TrialRow:
        row = TrialRow(schema_version=SCHEMA_VERSION, state=state, spec=spec)
        self._apply_row(row, persist=True)
        return row

    def append_spend(self, event: SpendEvent) -> SpendEvent:
        self._apply_spend(event, persist=True)
        return event

    def state_of(self, trial_id: str) -> str | None:
        return self._states.get(trial_id)

    def spec_of(self, trial_id: str) -> TrialSpec | None:
        return self._specs.get(trial_id)

    def terminal_ids(self) -> frozenset[str]:
        return frozenset(tid for tid, state in self._states.items() if state == "terminal")

    def pending(self, specs: tuple[TrialSpec, ...]) -> tuple[TrialSpec, ...]:
        done = self.terminal_ids()
        return tuple(item for item in specs if item.trial_id not in done)

    def spend_totals(self) -> dict[str, float]:
        open_reserved: dict[str, float] = {}
        settled = 0.0
        released = 0.0
        unknown = 0.0
        reserved = 0.0
        for event in self._events:
            if event.kind == "reserve":
                reserved += event.amount
                open_reserved[event.trial_id] = (
                    open_reserved.get(event.trial_id, 0.0) + event.amount
                )
            elif event.kind == "release":
                released += event.amount
                open_reserved[event.trial_id] = (
                    open_reserved.get(event.trial_id, 0.0) - event.amount
                )
            elif event.kind == "settle":
                settled += event.amount
                open_reserved[event.trial_id] = 0.0
            elif event.kind == "unknown":
                unknown += event.amount
        open_sum = sum(open_reserved.values())
        return {
            "reserved": reserved,
            "settled": settled,
            "released": released,
            "unknown": unknown,
            "open_reserved": open_sum,
            "exposure": settled + unknown + open_sum,
        }
