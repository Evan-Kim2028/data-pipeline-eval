from __future__ import annotations

from report_stats import (
    conditional_repair_rate,
    end_to_end_rate,
    failure_counts,
    paired_end_to_end,
    quartiles,
    task_rates,
)


def _row(
    task: str,
    provider: str,
    replicate: int,
    kind: str,
    *,
    patch: str = "applied",
    latency: float | None = 1.0,
    cost: float | None = 0.1,
) -> dict:
    return {
        "trial_id": f"mini:{task}:r{replicate}:{provider}",
        "task_id": task,
        "suite": "calibration" if task == "utc_lookback" else "default",
        "replicate": replicate,
        "seed": replicate + 1,
        "prompt_hash": "aa" * 32 if task == "schema_infer" else "bb" * 32,
        "requested_provider": provider,
        "served_provider": provider,
        "patch_status": patch,
        "outcome": {"kind": kind, "reason": None if kind == "pass" else kind},
        "latency_s": latency,
        "cost": cost,
    }


ROWS = [
    _row("schema_infer", "z-ai", 0, "pass"),
    _row("schema_infer", "novita", 0, "test_failure"),
    _row("schema_infer", "z-ai", 1, "pass"),
    _row("schema_infer", "novita", 1, "provider_failure", patch="rejected", cost=None),
    _row("utc_lookback", "z-ai", 0, "pass"),
    _row("utc_lookback", "novita", 0, "pass"),
    _row("utc_lookback", "z-ai", 1, "test_failure"),
    _row("utc_lookback", "novita", 1, "pass"),
]


def test_end_to_end_uses_all_planned_rows():
    summary = end_to_end_rate(ROWS)
    assert summary == {"numerator": 5, "denominator": 8, "rate": 5 / 8, "excluded": 0}


def test_conditional_excludes_provider_failures():
    summary = conditional_repair_rate(ROWS)
    assert summary["denominator"] == 7
    assert summary["numerator"] == 5
    assert summary["excluded"] == 1


def test_failure_decomposition_and_quartiles():
    counts = failure_counts(ROWS)
    assert counts["pass"] == 5
    assert counts["test_failure"] == 2
    assert counts["provider_failure"] == 1
    latency = quartiles([row["latency_s"] for row in ROWS])
    assert latency["n"] == 8
    assert latency["missing"] == 0
    cost = quartiles([row["cost"] for row in ROWS])
    assert cost["n"] == 7
    assert cost["missing"] == 1


def test_paired_end_to_end_and_task_difficulty():
    paired = paired_end_to_end(ROWS, "z-ai", "novita")
    assert paired["complete_pairs"] == 4
    assert paired["missing_pairs"] == 0
    assert paired["discordance"] == 3
    tasks = {row["task_id"]: row for row in task_rates(ROWS)}
    assert tasks["schema_infer"]["end_to_end"]["numerator"] == 2
    assert tasks["schema_infer"]["difficulty"] == 0.5
