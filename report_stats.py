"""Standard-library campaign statistics. No ranking. Every rate has a denominator."""

from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence

PASS = "pass"
PAIR_KEYS = ("task_id", "prompt_hash", "replicate", "seed")


def _outcome(row: Mapping[str, Any]) -> str:
    out = row.get("outcome") or {}
    if isinstance(out, Mapping):
        return str(out.get("kind") or "")
    return str(out)


def _prompt_hash(row: Mapping[str, Any]) -> str:
    return str(row.get("prompt_hash") or row.get("prompt_sha256") or "")


def end_to_end_rate(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    n = len(rows)
    wins = sum(1 for row in rows if _outcome(row) == PASS)
    return {"numerator": wins, "denominator": n, "rate": wins / n if n else 0.0, "excluded": 0}


def conditional_repair_rate(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    eligible = [
        row
        for row in rows
        if row.get("patch_status") == "applied"
        and _outcome(row) in {PASS, "test_failure"}
    ]
    wins = sum(1 for row in eligible if _outcome(row) == PASS)
    n = len(eligible)
    return {
        "numerator": wins,
        "denominator": n,
        "rate": wins / n if n else 0.0,
        "excluded": len(rows) - n,
    }


def failure_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        kind = _outcome(row) or "missing"
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo)


def quartiles(values: Sequence[float | None]) -> dict[str, float | None]:
    nums = sorted(v for v in values if v is not None)
    missing = len(values) - len(nums)
    if not nums:
        return {"median": None, "q1": None, "q3": None, "n": 0, "missing": missing}
    return {
        "median": _percentile(nums, 0.5),
        "q1": _percentile(nums, 0.25),
        "q3": _percentile(nums, 0.75),
        "n": len(nums),
        "missing": missing,
    }


def bootstrap_task_rate(
    rows: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    samples: int = 10000,
) -> tuple[float, float]:
    by_task: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_task.setdefault(str(row["task_id"]), []).append(row)
    task_ids = sorted(by_task)
    if not task_ids:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    rates: list[float] = []
    for _ in range(samples):
        chosen = [task_ids[rng.randrange(len(task_ids))] for _ in task_ids]
        bundle = [row for task in chosen for row in by_task[task]]
        rates.append(float(end_to_end_rate(bundle)["rate"]))
    rates.sort()
    lo_i = int(0.025 * (len(rates) - 1))
    hi_i = int(0.975 * (len(rates) - 1))
    return rates[lo_i], rates[hi_i]


def task_rates(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_task: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_task.setdefault(str(row["task_id"]), []).append(row)
    out = []
    for task_id in sorted(by_task):
        subset = by_task[task_id]
        e2e = end_to_end_rate(subset)
        suite = subset[0].get("suite")
        out.append(
            {
                "task_id": task_id,
                "suite": suite,
                "end_to_end": e2e,
                "difficulty": 1.0 - float(e2e["rate"]),
            }
        )
    return out


def _pair_key(row: Mapping[str, Any]) -> tuple[str, str, int, str]:
    return (
        str(row["task_id"]),
        _prompt_hash(row),
        int(row["replicate"]),
        str(row.get("seed")),
    )


def paired_end_to_end(
    rows: Sequence[Mapping[str, Any]], provider_a: str, provider_b: str
) -> dict[str, Any]:
    by_key: dict[tuple, dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        by_key.setdefault(_pair_key(row), {})[str(row.get("requested_provider"))] = row
    complete = 0
    missing = 0
    wins_a = 0
    wins_b = 0
    discord = 0
    for group in by_key.values():
        left = group.get(provider_a)
        right = group.get(provider_b)
        if left is None or right is None:
            missing += 1
            continue
        complete += 1
        a_pass = _outcome(left) == PASS
        b_pass = _outcome(right) == PASS
        wins_a += int(a_pass)
        wins_b += int(b_pass)
        if a_pass != b_pass:
            discord += 1
    diff = (wins_a - wins_b) / complete if complete else 0.0
    return {
        "providers": [provider_a, provider_b],
        "metric": "end_to_end",
        "complete_pairs": complete,
        "missing_pairs": missing,
        "estimate": diff,
        "discordance": discord,
        "inconclusive": abs(diff) == 0.0,
    }


def minimum_detectable_effect(
    *,
    n_tasks: int,
    seed: int,
    samples: int = 10000,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, float | int]:
    """Paired task-cluster sign test. Reports the smallest |delta| hitting power."""
    rng = random.Random(seed)
    if n_tasks <= 0:
        return {"mde": float("nan"), "n_tasks": 0, "samples": samples, "alpha": alpha, "power": power}
    for step in range(1, 21):
        delta = step / 20
        hits = 0
        for _ in range(samples):
            discord = 0
            a_only = 0
            for _task in range(n_tasks):
                draw = rng.random()
                if draw < delta:
                    discord += 1
                    a_only += 1
            if discord == 0:
                continue
            p = 0.0
            # two-sided binomial sign test on a_only given discord
            n = discord
            k = a_only
            # exact two-sided p via equal-tail count
            from_lo = min(k, n - k)
            p = sum(
                math.comb(n, i) for i in range(0, from_lo + 1)
            ) / (2 ** n) * 2
            if p > 1:
                p = 1.0
            if p <= alpha:
                hits += 1
        if hits / samples >= power:
            return {
                "mde": delta,
                "n_tasks": n_tasks,
                "samples": samples,
                "alpha": alpha,
                "power": power,
            }
    return {"mde": 1.0, "n_tasks": n_tasks, "samples": samples, "alpha": alpha, "power": power}


def summarize_provider(rows: Sequence[Mapping[str, Any]], provider: str) -> dict[str, Any]:
    subset = [row for row in rows if row.get("requested_provider") == provider]
    served: dict[str, int] = {}
    for row in subset:
        name = str(row.get("served_provider") or "missing")
        served[name] = served.get(name, 0) + 1
    return {
        "requested_provider": provider,
        "served_provider_counts": dict(sorted(served.items())),
        "end_to_end": end_to_end_rate(subset),
        "conditional_repair": conditional_repair_rate(subset),
        "failures": failure_counts(subset),
        "latency": quartiles(
            [None if row.get("latency_s") is None else float(row["latency_s"]) for row in subset]
        ),
        "cost": quartiles(
            [None if row.get("cost") is None else float(row["cost"]) for row in subset]
        ),
    }
