from __future__ import annotations

import json
from pathlib import Path

from harness.catalog import all_ids
from harness.contracts import (
    SCHEMA_VERSION,
    CampaignManifest,
    GradeReport,
    TrialOutcome,
    TrialRecord,
    decode_manifest,
    decode_trial,
    encode_json,
    environment_digest,
    git_revision,
)

ROOT = Path(__file__).resolve().parents[1]


def test_campaign_fixture_copies_revision_into_every_row(tmp_path: Path):
    sha, dirty = git_revision(ROOT)
    env = environment_digest(ROOT)
    published = sha if not dirty else f"{sha}-dirty"
    ids = all_ids()
    hashes = tuple((task_id, "a" * 64) for task_id in ids)
    manifest = CampaignManifest(
        schema_version=SCHEMA_VERSION,
        campaign_id="fixture",
        created_at="2026-08-29T00:00:00Z",
        task_ids=ids,
        repetitions=1,
        concurrency=1,
        model="z-ai/glm-5.3-flash",
        requested_providers=("z-ai",),
        temperature=0.0,
        max_tokens=128,
        benchmark_repo_sha=published,
        environment_sha256=env,
        prompt_hashes=hashes,
        comparable=not dirty,
    )
    rows = []
    for task_id in ids:
        grade = GradeReport(
            schema_version=SCHEMA_VERSION,
            trial_id=f"{task_id}-1",
            task_id=task_id,
            benchmark_repo_sha=published,
            command=("pytest", "-q"),
            exit_code=1,
            tests_collected=1,
            tests_failed=1,
            duration_s=0.01,
            output_sha256="b" * 64,
            patch_sha256="c" * 64,
            grader_source_sha=published if len(published) >= 40 else sha,
            grader_image_digest="sha256:" + ("d" * 64),
            sandbox_reason=None,
        )
        rows.append(
            TrialRecord(
                schema_version=SCHEMA_VERSION,
                campaign_id=manifest.campaign_id,
                trial_id=grade.trial_id,
                task_id=task_id,
                model=manifest.model,
                requested_provider="z-ai",
                temperature=0.0,
                max_tokens=128,
                prompt_sha256="a" * 64,
                benchmark_repo_sha=published,
                environment_sha256=env,
                latency_s=None,
                prompt_tokens=None,
                completion_tokens=None,
                cost=None,
                outcome=TrialOutcome(kind="test_failure", reason="fixture"),
                artifact_paths=(),
                grade=grade,
            )
        )
    path = tmp_path / "trials.jsonl"
    path.write_text("".join(encode_json(r) + "\n" for r in rows))
    decoded = [decode_trial(json.loads(line)) for line in path.read_text().splitlines()]
    assert decode_manifest(json.loads(encode_json(manifest))).campaign_id == "fixture"
    assert {row.benchmark_repo_sha for row in decoded} == {published}
    assert {row.environment_sha256 for row in decoded} == {env}
    assert len(decoded) == 15
