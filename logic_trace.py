"""Logic hops from one-shot CoT. Not tool spans."""

from __future__ import annotations

import json
import re
from pathlib import Path

_NUM = re.compile(r"^\s*(?:\d+[\.\)]\s+|[-*]\s+)")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z`])")


def hops_from_reasoning(text: str) -> list[dict]:
    blob = (text or "").replace("\r\n", "\n").strip()
    if not blob:
        return []
    parts: list[str] = []
    for para in re.split(r"\n\s*\n+", blob):
        para = para.strip()
        if not para:
            continue
        lines = para.splitlines()
        numbered = [i for i, line in enumerate(lines) if _NUM.match(line)]
        if len(numbered) >= 2:
            cuts = numbered + [len(lines)]
            if numbered[0] > 0:
                head = "\n".join(lines[: numbered[0]]).strip()
                if head:
                    parts.append(head)
            for a, b in zip(cuts, cuts[1:]):
                chunk = "\n".join(lines[a:b]).strip()
                if chunk:
                    parts.append(chunk)
        else:
            parts.append(para)
    if len(parts) == 1 and len(parts[0]) > 400:
        sentences = [s.strip() for s in _SENT.split(parts[0]) if s.strip()]
        if len(sentences) >= 3:
            grouped: list[str] = []
            buf: list[str] = []
            for sent in sentences:
                buf.append(sent)
                if len(buf) >= 2:
                    grouped.append(" ".join(buf))
                    buf = []
            if buf:
                grouped.append(" ".join(buf))
            parts = grouped
    return [{"i": i, "chars": len(part), "text": part} for i, part in enumerate(parts)]


def attach_throughput(row: dict) -> dict:
    lat = row.get("latency_s")
    try:
        latency = float(lat) if lat is not None else 0.0
    except (TypeError, ValueError):
        latency = 0.0
    if latency > 0:
        completion = row.get("completion_tokens")
        prompt = row.get("prompt_tokens")
        reason = row.get("reasoning_tokens")
        total = row.get("total_tokens")
        if total is None and isinstance(prompt, (int, float)) and isinstance(completion, (int, float)):
            total = prompt + completion
        if isinstance(completion, (int, float)):
            row["tps_out"] = round(completion / latency, 3)
        if isinstance(total, (int, float)):
            row["tps_total"] = round(total / latency, 3)
        if isinstance(reason, (int, float)):
            row["tps_reason"] = round(reason / latency, 3)
        think = row.get("think_s")
        try:
            think_s = float(think) if think is not None else 0.0
        except (TypeError, ValueError):
            think_s = 0.0
        if think_s > 0 and isinstance(reason, (int, float)):
            row["tps_think"] = round(reason / think_s, 3)
    if row.get("hop_count") is None:
        hops = row.get("hops")
        if isinstance(hops, list):
            row["hop_count"] = len(hops)
    return row


def hop_size_stats(
    hops: list[dict],
    *,
    reasoning_tokens: float | None = None,
    think_s: float | None = None,
    latency_s: float | None = None,
) -> dict:
    n = len(hops)
    chars = 0
    for hop in hops:
        if isinstance(hop.get("chars"), int):
            chars += hop["chars"]
        else:
            chars += len(str(hop.get("text") or ""))
    chars_per_hop = (chars / n) if n else None
    tokens_per_hop = (
        reasoning_tokens / n if n and isinstance(reasoning_tokens, (int, float)) else None
    )
    tokens_per_think_s = None
    if isinstance(think_s, (int, float)) and think_s > 0 and isinstance(reasoning_tokens, (int, float)):
        tokens_per_think_s = reasoning_tokens / think_s
    return {
        "hop_count": n,
        "chars_total": chars,
        "chars_per_hop": chars_per_hop,
        "reasoning_tokens": reasoning_tokens if isinstance(reasoning_tokens, (int, float)) else None,
        "tokens_per_hop": tokens_per_hop,
        "think_s": think_s if isinstance(think_s, (int, float)) else None,
        "tokens_per_think_s": tokens_per_think_s,
        "latency_s": latency_s if isinstance(latency_s, (int, float)) else None,
    }


def load_hops_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    hops = data.get("hops") if isinstance(data, dict) else data
    return hops if isinstance(hops, list) else []


def trial_hop_stats(row: dict, hops: list[dict] | None = None) -> dict:
    if hops is None:
        hops = row.get("hops") if isinstance(row.get("hops"), list) else []
        hop_path = row.get("hops_path")
        if hop_path and Path(str(hop_path)).is_file():
            hops = load_hops_file(Path(str(hop_path)))
    rt = row.get("reasoning_tokens")
    think = row.get("think_s")
    lat = row.get("latency_s")
    stats = hop_size_stats(
        hops,
        reasoning_tokens=rt if isinstance(rt, (int, float)) else None,
        think_s=think if isinstance(think, (int, float)) else None,
        latency_s=lat if isinstance(lat, (int, float)) else None,
    )
    stats["pass"] = bool(row.get("pass"))
    stats["quality"] = row.get("quality")
    stats["fail_mode"] = cot_fail_mode(
        passed=bool(row.get("pass")),
        quality=None if row.get("quality") is None else str(row.get("quality")),
        hops=hops or [],
    )
    stats["restated"] = restated_diagnosis(hops or [])
    return stats


def _mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


OVERTHINK_HOPS = 8


def restated_diagnosis(hops: list[dict]) -> bool:
    stems: list[tuple[str, ...]] = []
    for hop in hops:
        words = [w.lower() for w in str(hop.get("text") or "").split()[:8]]
        if len(words) >= 4:
            stems.append(tuple(words[:6]))
    if len(stems) < 3:
        return False
    counts: dict[tuple[str, ...], int] = {}
    for stem in stems:
        counts[stem] = counts.get(stem, 0) + 1
    return max(counts.values()) >= 3


def cot_fail_mode(*, passed: bool, quality: str | None, hops: list[dict]) -> str:
    q = str(quality or "")
    if passed:
        return "pass"
    if q.startswith("patch_did_not") or q.startswith("invalid_patch"):
        return "apply_fail"
    if len(hops) >= OVERTHINK_HOPS or restated_diagnosis(hops):
        return "overthink"
    return "short_wrong"


def host_hop_rollup(rows: list[dict]) -> list[dict]:
    order: list[str] = []
    by: dict[str, list[dict]] = {}
    for row in rows:
        provider = str(row.get("provider") or "")
        if not provider:
            continue
        if provider not in by:
            by[provider] = []
            order.append(provider)
        by[provider].append(trial_hop_stats(row))
    out: list[dict] = []
    for provider in order:
        trials = by[provider]
        def col(key: str) -> list[float]:
            return [float(t[key]) for t in trials if isinstance(t.get(key), (int, float))]
        fail_modes: dict[str, int] = {}
        for t in trials:
            mode = str(t.get("fail_mode") or "")
            fail_modes[mode] = fail_modes.get(mode, 0) + 1
        out.append(
            {
                "provider": provider,
                "n": len(trials),
                "n_pass": sum(1 for t in trials if t.get("pass")),
                "mean_hops": _mean(col("hop_count")),
                "mean_chars_total": _mean(col("chars_total")),
                "mean_chars_per_hop": _mean(col("chars_per_hop")),
                "mean_reasoning_tokens": _mean(col("reasoning_tokens")),
                "mean_tokens_per_hop": _mean(col("tokens_per_hop")),
                "mean_think_s": _mean(col("think_s")),
                "mean_tokens_per_think_s": _mean(col("tokens_per_think_s")),
                "mean_latency_s": _mean(col("latency_s")),
                "fail_modes": fail_modes,
            }
        )
    return out


def task_hop_rollup(rows: list[dict], *, difficulty_of: dict[str, str] | None = None) -> list[dict]:
    difficulty_of = difficulty_of or {}
    order: list[str] = []
    by: dict[str, list[tuple[dict, dict]]] = {}
    for row in rows:
        task = str(row.get("task") or "")
        if not task:
            continue
        if task not in by:
            by[task] = []
            order.append(task)
        by[task].append((row, trial_hop_stats(row)))
    out: list[dict] = []
    for task in order:
        pairs = by[task]
        trials = [s for _, s in pairs]
        n = len(trials)
        n_pass = sum(1 for t in trials if t.get("pass"))
        qualities: dict[str, int] = {}
        for t in trials:
            q = str(t.get("quality") or "")
            qualities[q] = qualities.get(q, 0) + 1
        pass_h = [float(t["hop_count"]) for t in trials if t.get("pass")]
        fail_h = [float(t["hop_count"]) for t in trials if not t.get("pass")]
        pass_th = [float(t["think_s"]) for t in trials if t.get("pass") and isinstance(t.get("think_s"), (int, float))]
        fail_th = [float(t["think_s"]) for t in trials if not t.get("pass") and isinstance(t.get("think_s"), (int, float))]
        rate = n_pass / n if n else 0.0
        if rate >= 0.9:
            band = "solved"
        elif rate == 0:
            band = "trip"
        else:
            band = "mixed"
        apply_fail = sum(1 for t in trials if t.get("fail_mode") == "apply_fail")
        fail_modes: dict[str, int] = {}
        for t in trials:
            mode = str(t.get("fail_mode") or "")
            fail_modes[mode] = fail_modes.get(mode, 0) + 1
        host_pass: dict[str, list[int]] = {}
        for row, stats in pairs:
            p = str(row.get("provider") or "")
            host_pass.setdefault(p, [0, 0])
            host_pass[p][1] += 1
            if stats.get("pass"):
                host_pass[p][0] += 1
        out.append(
            {
                "task": task,
                "estimated_difficulty": difficulty_of.get(task, ""),
                "n": n,
                "n_pass": n_pass,
                "rate": rate,
                "band": band,
                "qualities": qualities,
                "apply_fail": apply_fail,
                "fail_modes": fail_modes,
                "mean_hops": _mean([float(t["hop_count"]) for t in trials]),
                "mean_hops_pass": _mean(pass_h),
                "mean_hops_fail": _mean(fail_h),
                "mean_think_s": _mean(
                    [float(t["think_s"]) for t in trials if isinstance(t.get("think_s"), (int, float))]
                ),
                "mean_think_s_pass": _mean(pass_th),
                "mean_think_s_fail": _mean(fail_th),
                "host_pass": {h: f"{v[0]}/{v[1]}" for h, v in host_pass.items()},
            }
        )
    return out
