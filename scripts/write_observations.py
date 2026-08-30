#!/usr/bin/env python3
"""Host hop observations from a bake-off jsonl + hop sidecars.

  python scripts/write_observations.py logs/runs/<run_id>.jsonl --out /tmp/observations
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from catalog import by_id
from logic_trace import host_hop_rollup, task_hop_rollup

STANDOUT_REL = 0.20
GLOSSARY = (
    "Labels match the jsonl tokens. "
    "pass: the patch applied and both the shown tests and the hidden tests succeeded. "
    "apply-fail (apply_fail): the model returned a unified diff that git apply rejected, so the warehouse was never graded. "
    "overthink: the trial failed, and the chain of thought ran long (8 or more hops) or restated the same opening diagnosis three times. These hops are cuts of one-shot reasoning, not tool calls. "
    "short-wrong (short_wrong): the trial failed with a short chain of thought that still got the edit wrong. "
    "no-reply (no_response): the host never returned a usable answer (HTTP 429 or a dropped stream). That is not short-wrong."
)


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _fmt(val: float | None, digits: int = 2) -> str:
    if val is None:
        return ""
    return f"{val:.{digits}f}"


def _rel(a: float, b: float) -> float:
    lo, hi = min(a, b), max(a, b)
    if hi == 0:
        return 0.0
    if lo == 0:
        return 1.0
    return (hi - lo) / lo


def _standout_read(hosts: list[dict]) -> str:
    if not hosts:
        return "No hosts in this jsonl."
    bits: list[str] = []
    zeros = [h for h in hosts if (h.get("n_cached") or 0) == 0]
    hits = [h for h in hosts if (h.get("n_cached") or 0) > 0]
    if zeros and hits:
        bits.append(
            "Prefix cache is a split, not a small gap: "
            + ", ".join(h["provider"] for h in zeros)
            + " recorded zero cached trials. "
            + "; ".join(
                f"{h['provider']} cache hits {h.get('n_cached')}/{h.get('n')}"
                for h in hits
            )
            + "."
        )
    ot_shares: list[tuple[str, float, int, int]] = []
    for h in hosts:
        n = int(h.get("n") or 0)
        ot = int((h.get("fail_modes") or {}).get("overthink") or 0)
        ot_shares.append((str(h["provider"]), (ot / n) if n else 0.0, ot, n))
    if ot_shares:
        lo = min(ot_shares, key=lambda x: x[1])
        hi = max(ot_shares, key=lambda x: x[1])
        if hi[1] != lo[1] and _rel(lo[1], hi[1]) >= STANDOUT_REL:
            bits.append(
                f"Overthink share differs by at least 20% relative: "
                f"{hi[0]} {hi[2]}/{hi[3]} vs {lo[0]} {lo[2]}/{lo[3]}."
            )
    tps = [
        (str(h["provider"]), float(h["mean_tokens_per_think_s"]))
        for h in hosts
        if isinstance(h.get("mean_tokens_per_think_s"), (int, float))
    ]
    if tps:
        lo = min(tps, key=lambda x: x[1])
        hi = max(tps, key=lambda x: x[1])
        if _rel(lo[1], hi[1]) >= STANDOUT_REL:
            bits.append(
                f"Think tokens per second differ by at least 20% relative: "
                f"{hi[0]} {_fmt(hi[1], 1)} vs {lo[0]} {_fmt(lo[1], 1)}."
            )
        else:
            bits.append(
                "Think tokens per second stay within 20% across hosts; that is not a standout."
            )
    nr = [
        (str(h["provider"]), int((h.get("fail_modes") or {}).get("no_response") or 0), int(h.get("n") or 0))
        for h in hosts
    ]
    if any(c for _, c, _ in nr):
        bits.append(
            "No-reply trials: "
            + ", ".join(f"{p} {c}/{n}" for p, c, n in nr if c)
            + "."
        )
    if not bits:
        bits.append("No host trait cleared the 20% relative or qualitative-split bar on this jsonl.")
    return " ".join(bits)


def _task_read(tasks: list[dict], one_liners: dict[str, str]) -> str:
    solved = [t for t in tasks if t.get("band") == "solved"]
    mixed = [t for t in tasks if t.get("band") == "mixed"]
    trip = [t for t in tasks if t.get("band") == "trip"]
    bits = [
        f"Catalog marks every variance task `very_hard`. Empirical pass rate on this run splits them. "
        f"Solved ({len(solved)}): "
        + (", ".join(f"`{t['task']}` {_fmt(t.get('rate'), 2)}" for t in solved) or "none")
        + f". Mixed ({len(mixed)}): "
        + (", ".join(f"`{t['task']}` {_fmt(t.get('rate'), 2)}" for t in mixed) or "none")
        + f". Trip ({len(trip)}): "
        + (", ".join(f"`{t['task']}` {_fmt(t.get('rate'), 2)}" for t in trip) or "none")
        + ".",
    ]
    if solved:
        hops = _fmt(_mean([t.get("mean_hops") for t in solved]), 1)
        think = _fmt(_mean([t.get("mean_think_s") for t in solved]), 1)
        bits.append(
            f"Where they do well, CoT stays short (mean hops {hops}, think {think}s). "
            "They name the bug and emit a small diff."
        )
    if trip:
        apply_n = sum(int(t.get("apply_fail") or 0) for t in trip)
        explode = [t for t in trip if (t.get("mean_hops") or 0) >= 10]
        apply_trip = [t for t in trip if int(t.get("apply_fail") or 0) >= (t.get("n") or 1) / 2]
        if explode:
            names = ", ".join(f"`{t['task']}` hops {_fmt(t.get('mean_hops'), 1)} think {_fmt(t.get('mean_think_s'), 1)}s" for t in explode)
            bits.append(
                f"Where they trip by overthinking: {names}. "
                "Fail mode `overthink` is hop_count ≥ 8 or restated diagnosis, not extra tool hops."
            )
            worst = max(explode, key=lambda t: t.get("mean_think_s") or 0)
            bits.append(
                f"The longest think pile-up is `{worst['task']}` "
                f"({_fmt(worst.get('mean_think_s'), 1)}s, hops {_fmt(worst.get('mean_hops'), 1)})."
            )
        if apply_trip:
            names = ", ".join(f"`{t['task']}`" for t in apply_trip)
            bits.append(
                f"Where they trip with a short CoT: {names} is mostly `patch_did_not_apply`. "
                "They describe the right mechanism, then the unified diff does not apply."
            )
        if apply_n and not apply_trip and not explode:
            bits.append(f"{apply_n} apply-format fails sit on trip tasks.")
    apply_mixed = [
        t for t in mixed if int(t.get("apply_fail") or 0) >= (t.get("n") or 1) / 2
    ]
    if apply_mixed:
        names = ", ".join(
            f"`{t['task']}` {t.get('apply_fail')}/{t.get('n')} apply-fail, hops {_fmt(t.get('mean_hops'), 1)}"
            for t in apply_mixed
        )
        bits.append(
            f"Mixed but mostly apply-fail: {names}. Diagnosis is short. The patch does not land."
        )
    return " ".join(bits)


def _mean(vals: list) -> float | None:
    nums = [float(v) for v in vals if isinstance(v, (int, float))]
    return sum(nums) / len(nums) if nums else None


def _mode_s(modes: dict | None) -> str:
    return ", ".join(f"{k}:{v}" for k, v in sorted((modes or {}).items()) if v)


def _fail_mode_read(hosts: list[dict], tasks: list[dict]) -> str:
    totals: dict[str, int] = {}
    for t in tasks:
        for k, v in (t.get("fail_modes") or {}).items():
            totals[k] = totals.get(k, 0) + int(v)
    n = sum(totals.values())
    host_bits = []
    for h in hosts:
        modes = h.get("fail_modes") or {}
        over = int(modes.get("overthink") or 0)
        apply_n = int(modes.get("apply_fail") or 0)
        short = int(modes.get("short_wrong") or 0)
        none = int(modes.get("no_response") or 0)
        extra = f" no-reply {none}" if none else ""
        host_bits.append(
            f"{h['provider']} overthink {over} apply-fail {apply_n} short-wrong {short}{extra}"
        )
    return (
        GLOSSARY
        + " Gold solution text is not a classifier input. "
        f"Across {n} trials: "
        + ", ".join(f"{k} {v}" for k, v in sorted(totals.items()) if v)
        + ". "
        + "; ".join(host_bits)
        + "."
    )


def markdown(run_id: str, hosts: list[dict], tasks: list[dict], one_liners: dict[str, str]) -> str:
    lines = [
        "# Observations: host standouts",
        "",
        f"Run `{run_id}`. One-shot CoT. Hops are paragraph/claim cuts of the reasoning blob, "
        "not tool-call spans and not an agent loop. No winner rank. "
        "This spend uses the shared one-claim-then-diff instructions (scaffold campaign), "
        "so it is not comparable to Findings 2.",
        "",
        _standout_read(hosts),
        "",
        _fail_mode_read(hosts, tasks),
        "",
        "## Host hop size",
        "",
        "| provider | n | pass | cache hits | mean hops | mean chars/hop | mean reason_tok | mean think_s | fail modes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for h in hosts:
        lines.append(
            f"| {h['provider']} | {h['n']} | {h['n_pass']}/{h['n']} | "
            f"{h.get('n_cached', 0)}/{h['n']} | "
            f"{_fmt(h.get('mean_hops'), 1)} | {_fmt(h.get('mean_chars_per_hop'), 0)} | "
            f"{_fmt(h.get('mean_reasoning_tokens'), 0)} | {_fmt(h.get('mean_think_s'), 1)} | "
            f"{_mode_s(h.get('fail_modes'))} |"
        )
    lines += [
        "",
        "## Task complexity",
        "",
        _task_read(tasks, one_liners),
        "",
        "| task | catalog | empirical | band | pass | mean hops | hops on pass | hops on fail | mean think_s | fail modes | mechanism |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for t in tasks:
        lines.append(
            f"| `{t['task']}` | {t.get('estimated_difficulty') or ''} | {_fmt(t.get('rate'), 2)} | "
            f"{t.get('band')} | {t['n_pass']}/{t['n']} | {_fmt(t.get('mean_hops'), 1)} | "
            f"{_fmt(t.get('mean_hops_pass'), 1)} | {_fmt(t.get('mean_hops_fail'), 1)} | "
            f"{_fmt(t.get('mean_think_s'), 1)} | {_mode_s(t.get('fail_modes'))} | "
            f"{one_liners.get(t['task'], '')} |"
        )
    lines += [
        "",
        "## How to read this",
        "",
        "More hops means the CoT broke into more claim/paragraph units. Longer hops means each unit is bigger. "
        "Tokens per hop is `reasoning_tokens / hop_count`. Think_s is stream time spent in the reasoning phase. "
        "A host can think longer by writing bigger hops, more hops, or by emitting more tokens inside similar hop counts. "
        "Catalog `very_hard` does not predict hop load. Failures split by mode, not by host rank.",
        "",
        "Standout means a qualitative split (zero cache vs cache hits) or a consistent gap of about 20% relative. "
        "Gaps near 10% in think tokens per second are not a host story. "
        "See [Findings 2](../2/FINDINGS.html) for the earlier pre-scaffold k=3 mix.",
        "",
    ]
    return "\n".join(lines)


def html_doc(run_id: str, hosts: list[dict], tasks: list[dict], one_liners: dict[str, str]) -> str:
    rows = []
    for h in hosts:
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{html.escape(str(x))}</td>"
                for x in [
                    h["provider"],
                    h["n"],
                    f"{h['n_pass']}/{h['n']}",
                    f"{h.get('n_cached', 0)}/{h['n']}",
                    _fmt(h.get("mean_hops"), 1),
                    _fmt(h.get("mean_chars_per_hop"), 0),
                    _fmt(h.get("mean_reasoning_tokens"), 0),
                    _fmt(h.get("mean_think_s"), 1),
                    _mode_s(h.get("fail_modes")),
                ]
            )
            + "</tr>"
        )
    body = f"""
<h1>Observations: host standouts</h1>
<p>Run <code>{html.escape(run_id)}</code>. One-shot CoT. Hops are paragraph/claim cuts of the reasoning blob,
not tool-call spans and not an agent loop. No winner rank.
This spend uses the shared one-claim-then-diff instructions (scaffold campaign),
so it is not comparable to Findings 2.</p>
<p>{html.escape(_standout_read(hosts))}</p>
<p>{html.escape(_fail_mode_read(hosts, tasks))}</p>
<h2>Host hop size</h2>
<table>
<tr><th>provider</th><th>n</th><th>pass</th><th>cache hits</th><th>mean hops</th><th>mean chars/hop</th><th>mean reason_tok</th><th>mean think_s</th><th>fail modes</th></tr>
{''.join(rows)}
</table>
<h2>Task complexity</h2>
<p>{html.escape(_task_read(tasks, one_liners))}</p>
<table>
<tr><th>task</th><th>catalog</th><th>empirical</th><th>band</th><th>pass</th><th>mean hops</th><th>hops on pass</th><th>hops on fail</th><th>mean think_s</th><th>fail modes</th><th>mechanism</th></tr>
{''.join(
    "<tr>" + "".join(
        f"<td>{html.escape(str(x))}</td>"
        for x in [
            t["task"],
            t.get("estimated_difficulty") or "",
            _fmt(t.get("rate"), 2),
            t.get("band"),
            f"{t['n_pass']}/{t['n']}",
            _fmt(t.get("mean_hops"), 1),
            _fmt(t.get("mean_hops_pass"), 1),
            _fmt(t.get("mean_hops_fail"), 1),
            _fmt(t.get("mean_think_s"), 1),
            _mode_s(t.get("fail_modes")),
            one_liners.get(t["task"], ""),
        ]
    ) + "</tr>"
    for t in tasks
)}
</table>
<h2>How to read this</h2>
<p>More hops means the CoT broke into more claim/paragraph units. Longer hops means each unit is bigger.
Tokens per hop is reasoning_tokens / hop_count. Think_s is stream time spent in the reasoning phase.
Catalog very_hard does not predict hop load. Failures split by mode, not by host rank.</p>
<p>Standout means a qualitative split (zero cache vs cache hits) or a consistent gap of about 20% relative.
Gaps near 10% in think tokens per second are not a host story.
See <a href="../2/FINDINGS.html">Findings 2</a> for the earlier pre-scaffold k=3 mix.</p>
"""
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>Observations: host standouts</title>\n"
        "<style>\nbody{font:16px/1.45 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#111;}"
        "table{border-collapse:collapse;width:100%;font-size:13px;margin:1rem 0;}"
        "th,td{border:1px solid #ccc;padding:4px 6px;text-align:left;}"
        "th{background:#f3f3f3;}</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def write_observations(jsonl: Path, out_dir: Path) -> tuple[Path, Path, list[dict]]:
    rows = load_rows(jsonl)
    hosts = host_hop_rollup(rows)
    specs = by_id()
    difficulty_of = {i: t.estimated_difficulty for i, t in specs.items()}
    one_liners = {i: t.one_liner for i, t in specs.items()}
    tasks = task_hop_rollup(rows, difficulty_of=difficulty_of)
    run_id = str(rows[0].get("run_id") or jsonl.stem) if rows else jsonl.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "OBSERVATIONS.md"
    html_path = out_dir / "OBSERVATIONS.html"
    md_path.write_text(markdown(run_id, hosts, tasks, one_liners))
    html_path.write_text(html_doc(run_id, hosts, tasks, one_liners))
    return md_path, html_path, hosts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    md_path, html_path, hosts = write_observations(args.jsonl, args.out)
    print(md_path)
    print(html_path)
    print(json.dumps(hosts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
