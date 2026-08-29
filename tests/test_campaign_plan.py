from __future__ import annotations

import json
from pathlib import Path

import pytest

from campaign_plan import (
    ORDER_RULE,
    CampaignError,
    expand,
    load_campaign,
    manifest_hash,
    trial_id,
)

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "tests" / "fixtures" / "campaigns" / "mini.json"


def _load_mini_dict() -> dict:
    return json.loads(MINI.read_text())


def _write_campaign(tmp_path: Path, **changes) -> Path:
    data = _load_mini_dict()
    data.update(changes)
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def test_mini_fixture_expands_deterministically():
    campaign = load_campaign(MINI)
    first = expand(campaign)
    second = expand(load_campaign(MINI))
    assert first == second
    assert [row.trial_id for row in first] == [row.trial_id for row in second]
    assert [row.prompt_hash for row in first] == [row.prompt_hash for row in second]
    assert [row.seed for row in first] == [row.seed for row in second]
    assert [row.requested_provider for row in first] == [
        row.requested_provider for row in second
    ]
    assert [row.order_position for row in first] == [row.order_position for row in second]
    assert len(first) == 8
    assert campaign.require_parameters is True
    assert campaign.retry_policy.completion == 0
    assert campaign.order_rule == ORDER_RULE
    assert campaign.manifest.campaign_id == "mini"
    assert campaign.replicates == campaign.manifest.repetitions == 2
    assert campaign.jobs == campaign.manifest.concurrency == 1


def test_one_prompt_and_seed_are_paired_across_providers():
    specs = expand(load_campaign(MINI))
    grouped: dict[tuple[str, int], list] = {}
    for row in specs:
        grouped.setdefault((row.task_id, row.replicate), []).append(row)
    for pair in grouped.values():
        assert {row.requested_provider for row in pair} == {"z-ai", "novita"}
        assert len({row.seed for row in pair}) == 1
        assert len({row.prompt_hash for row in pair}) == 1
        assert len({row.trial_id for row in pair}) == 2


def test_starting_provider_rotates_by_catalog_index_plus_replicate():
    specs = expand(load_campaign(MINI))
    by_id = {(row.task_id, row.replicate, row.order_position): row for row in specs}
    infer_r0 = [row for row in specs if row.task_id == "schema_infer" and row.replicate == 0]
    infer_r1 = [row for row in specs if row.task_id == "schema_infer" and row.replicate == 1]
    lookback_r0 = [row for row in specs if row.task_id == "utc_lookback" and row.replicate == 0]
    lookback_r1 = [row for row in specs if row.task_id == "utc_lookback" and row.replicate == 1]
    assert [row.requested_provider for row in infer_r0] == ["z-ai", "novita"]
    assert [row.requested_provider for row in infer_r1] == ["novita", "z-ai"]
    assert [row.requested_provider for row in lookback_r0] == ["z-ai", "novita"]
    assert [row.requested_provider for row in lookback_r1] == ["novita", "z-ai"]
    assert infer_r0[0].seed == 1 and infer_r1[0].seed == 2
    assert lookback_r0[0].suite == "calibration"
    assert infer_r0[0].suite == "default"
    assert infer_r0[0].order_position == 0
    assert by_id["schema_infer", 0, 0].trial_id == trial_id(
        campaign_id="mini", task_id="schema_infer", replicate=0, provider="z-ai"
    )


def test_rotation_uses_catalog_index_not_manifest_order(tmp_path: Path):
    path = _write_campaign(
        tmp_path,
        task_ids=["utc_lookback", "schema_infer"],
        prompt_hashes=[
            [
                "utc_lookback",
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ],
            [
                "schema_infer",
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ],
        ],
    )
    specs = expand(load_campaign(path))
    infer_r0 = [row for row in specs if row.task_id == "schema_infer" and row.replicate == 0]
    infer_r1 = [row for row in specs if row.task_id == "schema_infer" and row.replicate == 1]
    lookback_r0 = [row for row in specs if row.task_id == "utc_lookback" and row.replicate == 0]
    assert lookback_r0[0].order_position == 0
    assert infer_r0[0].order_position == 4
    assert [row.requested_provider for row in infer_r0] == ["z-ai", "novita"]
    assert [row.requested_provider for row in infer_r1] == ["novita", "z-ai"]
    assert lookback_r0[0].requested_provider == "z-ai"


def test_three_providers_rotate_from_catalog_index(tmp_path: Path):
    path = _write_campaign(
        tmp_path,
        requested_providers=["z-ai", "novita", "together"],
        task_ids=["schema_infer", "unique_probe"],
        calibration_task_ids=[],
        prompt_hashes=[
            [
                "schema_infer",
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ],
            [
                "unique_probe",
                "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            ],
        ],
        replicates=1,
        paired_seeds=[7],
    )
    specs = expand(load_campaign(path))
    infer = [row for row in specs if row.task_id == "schema_infer"]
    probe = [row for row in specs if row.task_id == "unique_probe"]
    assert [row.requested_provider for row in infer] == ["z-ai", "novita", "together"]
    assert [row.requested_provider for row in probe] == ["novita", "together", "z-ai"]
    assert {row.seed for row in specs} == {7}
    assert {row.prompt_hash for row in infer} == {
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }


def test_manifest_hash_is_stable_and_copied_onto_every_spec():
    campaign = load_campaign(MINI)
    digest = manifest_hash(campaign)
    assert len(digest) == 64
    assert digest == manifest_hash(load_campaign(MINI))
    specs = expand(campaign)
    assert {row.manifest_hash for row in specs} == {digest}


def test_rejects_unknown_task(tmp_path: Path):
    path = _write_campaign(
        tmp_path,
        task_ids=["not_a_task"],
        calibration_task_ids=[],
        prompt_hashes=[
            ["not_a_task", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]
        ],
    )
    with pytest.raises(CampaignError, match="unknown task"):
        load_campaign(path)


def test_rejects_calibration_mismatch(tmp_path: Path):
    path = _write_campaign(tmp_path, calibration_task_ids=[])
    with pytest.raises(CampaignError, match="calibration_task_ids"):
        load_campaign(path)


def test_rejects_paired_seed_length_mismatch(tmp_path: Path):
    path = _write_campaign(tmp_path, paired_seeds=[1])
    with pytest.raises(CampaignError, match="paired_seeds"):
        load_campaign(path)


def test_rejects_duplicate_seeds(tmp_path: Path):
    path = _write_campaign(tmp_path, paired_seeds=[1, 1])
    with pytest.raises(CampaignError, match="unique"):
        load_campaign(path)


def test_rejects_require_parameters_false(tmp_path: Path):
    path = _write_campaign(tmp_path, require_parameters=False)
    with pytest.raises(CampaignError, match="require_parameters"):
        load_campaign(path)


def test_rejects_completion_retries(tmp_path: Path):
    path = _write_campaign(tmp_path, retry_policy={"completion": 1})
    with pytest.raises(CampaignError, match="completion"):
        load_campaign(path)


def test_rejects_unknown_order_rule(tmp_path: Path):
    path = _write_campaign(tmp_path, order_rule="round_robin")
    with pytest.raises(CampaignError, match="order_rule"):
        load_campaign(path)


def test_rejects_unknown_and_missing_fields(tmp_path: Path):
    extra = _write_campaign(tmp_path, sneaky=True)
    with pytest.raises(CampaignError, match="unknown fields"):
        load_campaign(extra)
    data = _load_mini_dict()
    del data["analysis_seed"]
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(data) + "\n")
    with pytest.raises(CampaignError, match="missing fields"):
        load_campaign(path)


def test_comparable_manifest_rejects_dirty_sha(tmp_path: Path):
    path = _write_campaign(
        tmp_path,
        benchmark_repo_sha=("a" * 40) + "-dirty",
        comparable=True,
    )
    with pytest.raises(CampaignError, match="clean SHA"):
        load_campaign(path)
