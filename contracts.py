"""Versioned public benchmark records. Paths keep repository and checkout domains apart."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "1"

_SHA_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_DENIED_CHECKOUT = (
    "tests/",
    "tests_held/",
    "tests_adjudication/",
    "solutions/",
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    "logs/",
    "results/",
)

OUTCOME_KINDS = frozenset(
    {
        "pass",
        "test_failure",
        "provider_failure",
        "empty_response",
        "malformed_output",
        "patch_rejection",
        "sandbox_failure",
        "timeout",
        "budget_stop",
        "interrupted_spend",
    }
)


class ContractError(ValueError):
    pass


def _posix_rel(value: str, *, kind: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{kind} path must be a nonempty string")
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise ContractError(f"{kind} path must be a relative POSIX path")
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ContractError(f"{kind} path rejects empty, dot, and parent segments")
    return value


@dataclass(frozen=True)
class RepoPath:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _posix_rel(self.value, kind="repo"))


@dataclass(frozen=True)
class CheckoutPath:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _posix_rel(self.value, kind="checkout"))
        lowered = self.value.replace("\\", "/")
        for prefix in _DENIED_CHECKOUT:
            if lowered == prefix.rstrip("/") or lowered.startswith(prefix):
                raise ContractError(f"checkout path denies {prefix}")


def _require_sha(name: str, value: str, *, allow_dirty: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} is required")
    raw = value[:-6] if allow_dirty and value.endswith("-dirty") else value
    if not _SHA_RE.fullmatch(raw):
        raise ContractError(f"{name} must be a full git SHA")
    return value


def _require_hex64(name: str, value: str) -> str:
    if not isinstance(value, str) or not _HEX64_RE.fullmatch(value):
        raise ContractError(f"{name} must be a 64-char hex digest")
    return value


@dataclass(frozen=True)
class TaskSpec:
    id: str
    category: str
    estimated_difficulty: str
    suite: str
    one_liner: str
    prompt_repo_path: RepoPath
    fault_repo_path: RepoPath
    practice_tests_repo_path: RepoPath
    adjudication_tests_repo_path: RepoPath
    gold_repo_path: RepoPath
    explanation_repo_path: RepoPath
    mutant_repo_dir: RepoPath
    context_checkout_paths: tuple[CheckoutPath, ...]
    editable_checkout_paths: tuple[CheckoutPath, ...]
    entrypoint: str

    def __post_init__(self) -> None:
        if not self.id or "/" in self.id:
            raise ContractError("task id must be a nonempty directory name")
        if not self.one_liner:
            raise ContractError("one_liner is required")
        if not self.entrypoint or "." not in self.entrypoint:
            raise ContractError("entrypoint must be a dotted import path")
        if not self.context_checkout_paths:
            raise ContractError("context_checkout_paths must be nonempty")
        if not self.editable_checkout_paths:
            raise ContractError("editable_checkout_paths must be nonempty")
        edit = {p.value for p in self.editable_checkout_paths}
        ctx = {p.value for p in self.context_checkout_paths}
        if not edit <= ctx:
            raise ContractError("editable paths must appear in context")


@dataclass(frozen=True)
class TaskCheckout:
    task_id: str
    benchmark_repo_sha: str
    files: tuple[tuple[str, bytes], ...]
    ordered_hashes: tuple[tuple[str, str], ...]
    checkout_digest: str

    def __post_init__(self) -> None:
        _require_sha("benchmark_repo_sha", self.benchmark_repo_sha, allow_dirty=True)
        _require_hex64("checkout_digest", self.checkout_digest)
        if tuple(p for p, _ in self.ordered_hashes) != tuple(p for p, _ in self.files):
            raise ContractError("ordered_hashes must follow files")

    def file_map(self) -> dict[str, bytes]:
        return dict(self.files)


@dataclass(frozen=True)
class TrialOutcome:
    kind: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in OUTCOME_KINDS:
            raise ContractError(f"unknown outcome kind {self.kind}")
        if self.kind == "pass" and self.reason:
            raise ContractError("pass cannot carry a reason")
        if self.kind != "pass" and not self.reason:
            raise ContractError(f"{self.kind} requires a reason")


@dataclass(frozen=True)
class GradeReport:
    schema_version: str
    trial_id: str
    task_id: str
    benchmark_repo_sha: str
    command: tuple[str, ...]
    exit_code: int
    tests_collected: int
    tests_failed: int
    duration_s: float
    output_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractError("unknown schema_version")
        _require_sha("benchmark_repo_sha", self.benchmark_repo_sha, allow_dirty=True)
        _require_hex64("output_sha256", self.output_sha256)
        if self.tests_collected < 0 or self.tests_failed < 0:
            raise ContractError("test counts cannot be negative")
        if self.tests_failed > self.tests_collected:
            raise ContractError("failed tests exceed collected tests")


@dataclass(frozen=True)
class TrialRecord:
    schema_version: str
    campaign_id: str
    trial_id: str
    task_id: str
    model: str
    requested_provider: str
    temperature: float
    max_tokens: int
    prompt_sha256: str
    benchmark_repo_sha: str
    environment_sha256: str
    latency_s: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost: float | None
    outcome: TrialOutcome
    artifact_paths: tuple[str, ...]
    grade: GradeReport | None = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractError("unknown schema_version")
        _require_hex64("prompt_sha256", self.prompt_sha256)
        _require_sha("benchmark_repo_sha", self.benchmark_repo_sha, allow_dirty=True)
        _require_hex64("environment_sha256", self.environment_sha256)
        if self.grade and self.grade.trial_id != self.trial_id:
            raise ContractError("grade trial_id mismatch")
        if self.grade and self.grade.benchmark_repo_sha != self.benchmark_repo_sha:
            raise ContractError("grade SHA mismatch")
        if self.outcome.kind == "pass" and self.grade is None:
            raise ContractError("pass requires a grade report")


@dataclass(frozen=True)
class CampaignManifest:
    schema_version: str
    campaign_id: str
    created_at: str
    task_ids: tuple[str, ...]
    repetitions: int
    concurrency: int
    model: str
    requested_providers: tuple[str, ...]
    temperature: float
    max_tokens: int
    benchmark_repo_sha: str
    environment_sha256: str
    prompt_hashes: tuple[tuple[str, str], ...]
    comparable: bool

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractError("unknown schema_version")
        if not self.task_ids or not self.requested_providers:
            raise ContractError("campaign needs tasks and providers")
        if self.repetitions < 1 or self.concurrency < 1:
            raise ContractError("repetitions and concurrency must be >= 1")
        _require_sha("benchmark_repo_sha", self.benchmark_repo_sha, allow_dirty=True)
        _require_hex64("environment_sha256", self.environment_sha256)
        if self.comparable and self.benchmark_repo_sha.endswith("-dirty"):
            raise ContractError("comparable campaigns require a clean SHA")
        ids = [t for t, _ in self.prompt_hashes]
        if ids != list(self.task_ids):
            raise ContractError("prompt_hashes must follow task_ids")
        for _, digest in self.prompt_hashes:
            _require_hex64("prompt hash", digest)


def git_revision(root: Path) -> tuple[str, bool]:
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    porcelain = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    )
    dirty = bool(porcelain.strip())
    return sha, dirty


def environment_digest(root: Path) -> str:
    py = (root / ".python-version").read_bytes()
    lock = (root / "requirements.lock").read_bytes()
    blob = b".python-version\n" + py + b"\nrequirements.lock\n" + lock
    return hashlib.sha256(blob).hexdigest()


def python_version_pin(root: Path) -> tuple[int, int, int]:
    text = (root / ".python-version").read_text().strip()
    parts = text.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ContractError(".python-version must be major.minor.patch")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, (RepoPath, CheckoutPath)):
        return obj.value
    if isinstance(obj, TrialOutcome):
        return {"kind": obj.kind, "reason": obj.reason}
    if is_dataclass(obj) and not isinstance(obj, type):
        out = {}
        for f in fields(obj):
            out[f.name] = _to_jsonable(getattr(obj, f.name))
        return out
    if isinstance(obj, tuple):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, bytes):
        raise ContractError("bytes cannot cross the JSON boundary")
    return obj


def encode_json(obj: Any) -> str:
    return json.dumps(_to_jsonable(obj), separators=(",", ":"), sort_keys=True)


def _reject_extra(data: Mapping[str, Any], cls: type) -> None:
    allowed = {f.name for f in fields(cls)}
    extra = set(data) - allowed
    if extra:
        raise ContractError(f"unknown fields {sorted(extra)}")
    missing = allowed - set(data)
    if missing:
        raise ContractError(f"missing fields {sorted(missing)}")


def decode_outcome(data: Mapping[str, Any]) -> TrialOutcome:
    if set(data) - {"kind", "reason"}:
        raise ContractError("unknown outcome fields")
    return TrialOutcome(kind=str(data["kind"]), reason=data.get("reason"))


def decode_grade(data: Mapping[str, Any]) -> GradeReport:
    _reject_extra(data, GradeReport)
    return GradeReport(
        schema_version=str(data["schema_version"]),
        trial_id=str(data["trial_id"]),
        task_id=str(data["task_id"]),
        benchmark_repo_sha=str(data["benchmark_repo_sha"]),
        command=tuple(data["command"]),
        exit_code=int(data["exit_code"]),
        tests_collected=int(data["tests_collected"]),
        tests_failed=int(data["tests_failed"]),
        duration_s=float(data["duration_s"]),
        output_sha256=str(data["output_sha256"]),
    )


def decode_trial(data: Mapping[str, Any]) -> TrialRecord:
    _reject_extra(data, TrialRecord)
    grade = data["grade"]
    return TrialRecord(
        schema_version=str(data["schema_version"]),
        campaign_id=str(data["campaign_id"]),
        trial_id=str(data["trial_id"]),
        task_id=str(data["task_id"]),
        model=str(data["model"]),
        requested_provider=str(data["requested_provider"]),
        temperature=float(data["temperature"]),
        max_tokens=int(data["max_tokens"]),
        prompt_sha256=str(data["prompt_sha256"]),
        benchmark_repo_sha=str(data["benchmark_repo_sha"]),
        environment_sha256=str(data["environment_sha256"]),
        latency_s=None if data["latency_s"] is None else float(data["latency_s"]),
        prompt_tokens=None if data["prompt_tokens"] is None else int(data["prompt_tokens"]),
        completion_tokens=(
            None if data["completion_tokens"] is None else int(data["completion_tokens"])
        ),
        cost=None if data["cost"] is None else float(data["cost"]),
        outcome=decode_outcome(data["outcome"]),
        artifact_paths=tuple(data["artifact_paths"]),
        grade=None if grade is None else decode_grade(grade),
    )


def decode_manifest(data: Mapping[str, Any]) -> CampaignManifest:
    _reject_extra(data, CampaignManifest)
    hashes = tuple((str(k), str(v)) for k, v in data["prompt_hashes"])
    return CampaignManifest(
        schema_version=str(data["schema_version"]),
        campaign_id=str(data["campaign_id"]),
        created_at=str(data["created_at"]),
        task_ids=tuple(data["task_ids"]),
        repetitions=int(data["repetitions"]),
        concurrency=int(data["concurrency"]),
        model=str(data["model"]),
        requested_providers=tuple(data["requested_providers"]),
        temperature=float(data["temperature"]),
        max_tokens=int(data["max_tokens"]),
        benchmark_repo_sha=str(data["benchmark_repo_sha"]),
        environment_sha256=str(data["environment_sha256"]),
        prompt_hashes=hashes,
        comparable=bool(data["comparable"]),
    )
