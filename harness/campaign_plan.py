"""Load frozen campaign manifests and expand deterministic TrialSpec values."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .catalog import all_ids, spec
from .contracts import CampaignManifest, ContractError, encode_json

ORDER_RULE = "catalog_index_plus_replicate"
_SHA_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = frozenset(
    {
        "schema_version",
        "campaign_id",
        "created_at",
        "repository_url",
        "benchmark_repo_sha",
        "grader_source_sha",
        "grader_image_digest",
        "environment_sha256",
        "task_ids",
        "calibration_task_ids",
        "model",
        "temperature",
        "max_tokens",
        "requested_providers",
        "require_parameters",
        "replicates",
        "paired_seeds",
        "order_rule",
        "jobs",
        "retry_policy",
        "spend_cap",
        "analysis_seed",
        "prompt_hashes",
        "comparable",
    }
)


class CampaignError(ValueError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    completion: int

    def __post_init__(self) -> None:
        if self.completion != 0:
            raise CampaignError("retry_policy.completion must be 0")


@dataclass(frozen=True)
class Campaign:
    """Phase 7 fields wrapped around contracts.CampaignManifest."""

    manifest: CampaignManifest
    repository_url: str
    grader_source_sha: str
    grader_image_digest: str
    calibration_task_ids: tuple[str, ...]
    require_parameters: bool
    paired_seeds: tuple[int, ...]
    order_rule: str
    retry_policy: RetryPolicy
    spend_cap: float
    analysis_seed: int

    @property
    def replicates(self) -> int:
        return self.manifest.repetitions

    @property
    def jobs(self) -> int:
        return self.manifest.concurrency


@dataclass(frozen=True)
class TrialSpec:
    trial_id: str
    campaign_id: str
    task_id: str
    suite: str
    replicate: int
    seed: int
    prompt_hash: str
    requested_provider: str
    order_position: int
    manifest_hash: str

    def __post_init__(self) -> None:
        if self.replicate < 0 or self.order_position < 0:
            raise CampaignError("replicate and order_position must be >= 0")
        if not _HEX64_RE.fullmatch(self.prompt_hash):
            raise CampaignError("prompt_hash must be a 64-char hex digest")
        if not _HEX64_RE.fullmatch(self.manifest_hash):
            raise CampaignError("manifest_hash must be a 64-char hex digest")
        if not self.trial_id or not self.campaign_id or not self.task_id:
            raise CampaignError("trial identity fields are required")
        if not self.requested_provider:
            raise CampaignError("requested_provider is required")
        if self.suite not in {"default", "calibration"}:
            raise CampaignError(f"unknown suite {self.suite}")


def _require_sha(name: str, value: object) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise CampaignError(f"{name} must be a full git SHA")
    return value


def _require_digest(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise CampaignError(f"{name} must be an immutable sha256 digest")
    if not _HEX64_RE.fullmatch(value[7:]):
        raise CampaignError(f"{name} must be an immutable sha256 digest")
    return value


def _pairs(value: object, *, name: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list) or not value:
        raise CampaignError(f"{name} must be a nonempty list of pairs")
    out: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise CampaignError(f"{name} must be a nonempty list of pairs")
        out.append((str(item[0]), str(item[1])))
    return tuple(out)


def _strings(value: object, *, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise CampaignError(f"{name} must be a nonempty list of strings")
    if any(not isinstance(x, str) or not x for x in value):
        raise CampaignError(f"{name} must be a nonempty list of strings")
    return tuple(value)


def _seeds(value: object, replicates: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != replicates:
        raise CampaignError("paired_seeds length must equal replicates")
    seeds: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise CampaignError("paired_seeds must be integers")
        seeds.append(item)
    if len(set(seeds)) != len(seeds):
        raise CampaignError("paired_seeds must be unique")
    return tuple(seeds)


def _retry_policy(value: object) -> RetryPolicy:
    if not isinstance(value, dict) or set(value) != {"completion"}:
        raise CampaignError("retry_policy must be {\"completion\": 0}")
    completion = value["completion"]
    if isinstance(completion, bool) or not isinstance(completion, int):
        raise CampaignError("retry_policy.completion must be 0")
    return RetryPolicy(completion=completion)


def load_campaign(path: Path) -> Campaign:
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise CampaignError("manifest is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise CampaignError("manifest must be a JSON object")
    extra = set(raw) - _FIELDS
    if extra:
        raise CampaignError(f"unknown fields {sorted(extra)}")
    missing = _FIELDS - set(raw)
    if missing:
        raise CampaignError(f"missing fields {sorted(missing)}")
    return campaign_from_mapping(raw)


def campaign_from_mapping(raw: Mapping[str, Any]) -> Campaign:
    extra = set(raw) - _FIELDS
    if extra:
        raise CampaignError(f"unknown fields {sorted(extra)}")
    missing = _FIELDS - set(raw)
    if missing:
        raise CampaignError(f"missing fields {sorted(missing)}")
    if raw["require_parameters"] is not True:
        raise CampaignError("require_parameters must be true")
    if raw["order_rule"] != ORDER_RULE:
        raise CampaignError(f"order_rule must be {ORDER_RULE}")
    if not isinstance(raw["repository_url"], str) or not raw["repository_url"]:
        raise CampaignError("repository_url is required")
    if not isinstance(raw["spend_cap"], (int, float)) or isinstance(raw["spend_cap"], bool):
        raise CampaignError("spend_cap must be a number")
    if float(raw["spend_cap"]) < 0:
        raise CampaignError("spend_cap must be >= 0")
    if isinstance(raw["analysis_seed"], bool) or not isinstance(raw["analysis_seed"], int):
        raise CampaignError("analysis_seed must be an integer")
    if isinstance(raw["replicates"], bool) or not isinstance(raw["replicates"], int):
        raise CampaignError("replicates must be an integer")
    if isinstance(raw["jobs"], bool) or not isinstance(raw["jobs"], int):
        raise CampaignError("jobs must be an integer")
    task_ids = _strings(raw["task_ids"], name="task_ids")
    calibration = tuple(raw["calibration_task_ids"])
    if not isinstance(raw["calibration_task_ids"], list) or any(
        not isinstance(x, str) or not x for x in calibration
    ):
        raise CampaignError("calibration_task_ids must be a list of strings")
    if len(set(calibration)) != len(calibration):
        raise CampaignError("calibration_task_ids must be unique")
    expected_cal = []
    for task_id in task_ids:
        try:
            task = spec(task_id)
        except ContractError as exc:
            raise CampaignError(f"unknown task {task_id}") from exc
        if task.suite == "calibration":
            expected_cal.append(task_id)
    if tuple(expected_cal) != calibration:
        raise CampaignError("calibration_task_ids must match catalog calibration tasks in task_ids")
    if any(task_id not in task_ids for task_id in calibration):
        raise CampaignError("calibration_task_ids must be a subset of task_ids")
    hashes = _pairs(raw["prompt_hashes"], name="prompt_hashes")
    retry = _retry_policy(raw["retry_policy"])
    seeds = _seeds(raw["paired_seeds"], int(raw["replicates"]))
    try:
        manifest = CampaignManifest(
            schema_version=str(raw["schema_version"]),
            campaign_id=str(raw["campaign_id"]),
            created_at=str(raw["created_at"]),
            task_ids=task_ids,
            repetitions=int(raw["replicates"]),
            concurrency=int(raw["jobs"]),
            model=str(raw["model"]),
            requested_providers=_strings(
                raw["requested_providers"], name="requested_providers"
            ),
            temperature=float(raw["temperature"]),
            max_tokens=int(raw["max_tokens"]),
            benchmark_repo_sha=str(raw["benchmark_repo_sha"]),
            environment_sha256=str(raw["environment_sha256"]),
            prompt_hashes=hashes,
            comparable=bool(raw["comparable"]),
        )
    except ContractError as exc:
        raise CampaignError(str(exc)) from exc
    campaign = Campaign(
        manifest=manifest,
        repository_url=str(raw["repository_url"]),
        grader_source_sha=_require_sha("grader_source_sha", raw["grader_source_sha"]),
        grader_image_digest=_require_digest(
            "grader_image_digest", raw["grader_image_digest"]
        ),
        calibration_task_ids=calibration,
        require_parameters=True,
        paired_seeds=seeds,
        order_rule=str(raw["order_rule"]),
        retry_policy=retry,
        spend_cap=float(raw["spend_cap"]),
        analysis_seed=int(raw["analysis_seed"]),
    )
    if len(campaign.paired_seeds) != campaign.replicates:
        raise CampaignError("paired_seeds length must equal replicates")
    return campaign


def _canonical(campaign: Campaign) -> dict[str, Any]:
    data = json.loads(encode_json(campaign.manifest))
    data["repository_url"] = campaign.repository_url
    data["grader_source_sha"] = campaign.grader_source_sha
    data["grader_image_digest"] = campaign.grader_image_digest
    data["calibration_task_ids"] = list(campaign.calibration_task_ids)
    data["require_parameters"] = campaign.require_parameters
    data["replicates"] = campaign.replicates
    data["paired_seeds"] = list(campaign.paired_seeds)
    data["order_rule"] = campaign.order_rule
    data["jobs"] = campaign.jobs
    data["retry_policy"] = {"completion": campaign.retry_policy.completion}
    data["spend_cap"] = campaign.spend_cap
    data["analysis_seed"] = campaign.analysis_seed
    return data


def manifest_hash(campaign: Campaign) -> str:
    blob = json.dumps(_canonical(campaign), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def trial_id(*, campaign_id: str, task_id: str, replicate: int, provider: str) -> str:
    return f"{campaign_id}:{task_id}:r{replicate}:{provider}"


def expand(campaign: Campaign) -> tuple[TrialSpec, ...]:
    catalog_order = all_ids()
    providers = campaign.manifest.requested_providers
    n = len(providers)
    hashes = dict(campaign.manifest.prompt_hashes)
    digest = manifest_hash(campaign)
    specs: list[TrialSpec] = []
    position = 0
    for task_id in campaign.manifest.task_ids:
        catalog_idx = catalog_order.index(task_id)
        suite = spec(task_id).suite
        prompt_hash = hashes[task_id]
        for replicate in range(campaign.replicates):
            seed = campaign.paired_seeds[replicate]
            start = (catalog_idx + replicate) % n
            rotated = providers[start:] + providers[:start]
            for provider in rotated:
                specs.append(
                    TrialSpec(
                        trial_id=trial_id(
                            campaign_id=campaign.manifest.campaign_id,
                            task_id=task_id,
                            replicate=replicate,
                            provider=provider,
                        ),
                        campaign_id=campaign.manifest.campaign_id,
                        task_id=task_id,
                        suite=suite,
                        replicate=replicate,
                        seed=seed,
                        prompt_hash=prompt_hash,
                        requested_provider=provider,
                        order_position=position,
                        manifest_hash=digest,
                    )
                )
                position += 1
    return tuple(specs)
