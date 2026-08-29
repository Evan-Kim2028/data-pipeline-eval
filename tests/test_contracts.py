from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from contracts import (
    SCHEMA_VERSION,
    CampaignManifest,
    CheckoutPath,
    ContractError,
    GradeReport,
    RepoPath,
    TrialOutcome,
    TrialRecord,
    decode_manifest,
    decode_trial,
    encode_json,
    environment_digest,
    git_revision,
)


def _grade(**kwargs) -> GradeReport:
    base = dict(
        schema_version=SCHEMA_VERSION,
        trial_id="t1",
        task_id="schema_infer",
        benchmark_repo_sha="a" * 40,
        command=("pytest", "-q"),
        exit_code=0,
        tests_collected=2,
        tests_failed=0,
        duration_s=0.1,
        output_sha256="b" * 64,
        patch_sha256="c" * 64,
        grader_source_sha="a" * 40,
        grader_image_digest="sha256:" + ("d" * 64),
        sandbox_reason=None,
    )
    base.update(kwargs)
    return GradeReport(**base)


def _trial(**kwargs) -> TrialRecord:
    base = dict(
        schema_version=SCHEMA_VERSION,
        campaign_id="c1",
        trial_id="t1",
        task_id="schema_infer",
        model="z-ai/glm-5.3-flash",
        requested_provider="z-ai",
        temperature=0.0,
        max_tokens=128,
        prompt_sha256="c" * 64,
        benchmark_repo_sha="a" * 40,
        environment_sha256="d" * 64,
        latency_s=1.0,
        prompt_tokens=10,
        completion_tokens=10,
        cost=0.01,
        outcome=TrialOutcome(kind="pass"),
        artifact_paths=("results/t1.json",),
        grade=_grade(),
    )
    base.update(kwargs)
    return TrialRecord(**base)


def test_repo_and_checkout_paths_are_distinct_types():
    repo = RepoPath("tasks/schema_infer/prompt.txt")
    checkout = CheckoutPath("warehouse/silver/schema.py")
    assert repo.value != checkout.value
    with pytest.raises(ContractError):
        RepoPath("/abs/path")
    with pytest.raises(ContractError):
        CheckoutPath("../escape")
    with pytest.raises(ContractError):
        CheckoutPath("tests/test_load.py")


def test_trial_round_trip_preserves_comparison_fields():
    row = _trial()
    encoded = encode_json(row)
    decoded = decode_trial(json.loads(encoded))
    assert decoded == row
    assert decoded.benchmark_repo_sha == "a" * 40
    assert decoded.environment_sha256 == "d" * 64


def test_decode_rejects_unknown_schema_and_extra_fields():
    data = json.loads(encode_json(_trial()))
    data["schema_version"] = "999"
    with pytest.raises(ContractError):
        decode_trial(data)
    data = json.loads(encode_json(_trial()))
    data["sneaky"] = True
    with pytest.raises(ContractError):
        decode_trial(data)


def test_pass_requires_grade_and_failure_requires_reason():
    with pytest.raises(ContractError):
        _trial(outcome=TrialOutcome(kind="pass"), grade=None)
    with pytest.raises(ContractError):
        TrialOutcome(kind="test_failure")
    failed = _trial(
        outcome=TrialOutcome(kind="test_failure", reason="assert ids"),
        grade=_grade(exit_code=1, tests_failed=1),
    )
    assert decode_trial(json.loads(encode_json(failed))).outcome.kind == "test_failure"


def test_comparable_manifest_rejects_dirty_sha():
    kwargs = dict(
        schema_version=SCHEMA_VERSION,
        campaign_id="official-v1",
        created_at="2026-08-29T00:00:00Z",
        task_ids=("schema_infer",),
        repetitions=1,
        concurrency=1,
        model="z-ai/glm-5.3-flash",
        requested_providers=("z-ai",),
        temperature=0.0,
        max_tokens=128,
        environment_sha256="e" * 64,
        prompt_hashes=(("schema_infer", "f" * 64),),
    )
    with pytest.raises(ContractError):
        CampaignManifest(
            benchmark_repo_sha=("a" * 40) + "-dirty",
            comparable=True,
            **kwargs,
        )
    dirty = CampaignManifest(
        benchmark_repo_sha=("a" * 40) + "-dirty",
        comparable=False,
        **kwargs,
    )
    assert decode_manifest(json.loads(encode_json(dirty))).comparable is False


def test_git_revision_reports_clean_and_dirty(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "eval@local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "eval"], cwd=repo, check=True)
    (repo / "f.txt").write_text("one\n")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    sha, dirty = git_revision(repo)
    assert len(sha) == 40 and dirty is False
    (repo / "f.txt").write_text("two\n")
    sha2, dirty2 = git_revision(repo)
    assert sha2 == sha and dirty2 is True
