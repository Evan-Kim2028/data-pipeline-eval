#!/usr/bin/env python3
"""Build markdown + disk-openable HTML from a bake-off jsonl.

  python scripts/write_findings.py logs/runs/<run_id>.jsonl --out docs/findings
"""

from __future__ import annotations

import argparse
import html
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _num(row: dict, key: str) -> float | None:
    val = row.get(key)
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _mean(vals: list[float]) -> float | None:
    return statistics.mean(vals) if vals else None


def summarize(rows: list[dict]) -> dict:
    providers: list[str] = []
    for row in rows:
        p = str(row.get("provider") or "")
        if p and p not in providers:
            providers.append(p)
    tasks: list[str] = []
    for row in rows:
        t = str(row.get("task") or "")
        if t and t not in tasks:
            tasks.append(t)
    by_host: dict[str, list[dict]] = {p: [] for p in providers}
    for row in rows:
        by_host[str(row.get("provider") or "")].append(row)
    hosts = []
    for p in providers:
        subset = by_host[p]
        n = len(subset)
        n_pass = sum(1 for r in subset if r.get("pass"))
        qualities = Counter(str(r.get("quality") or "") for r in subset)
        costs = [_num(r, "cost") for r in subset]
        reasons = [_num(r, "reasoning_tokens") for r in subset]
        comps = [_num(r, "completion_tokens") for r in subset]
        cached = [_num(r, "cached_tokens") for r in subset]
        lats = [_num(r, "latency_s") for r in subset]
        cost_ok = [v for v in costs if v is not None]
        reason_ok = [v for v in reasons if v is not None]
        comp_ok = [v for v in comps if v is not None]
        cache_ok = [v for v in cached if v is not None]
        lat_ok = [v for v in lats if v is not None]
        ratios = []
        for r in subset:
            rt = _num(r, "reasoning_tokens")
            ct = _num(r, "completion_tokens")
            if rt is not None and ct and ct > 0:
                ratios.append(rt / ct)
        format_fail = sum(
            1
            for r in subset
            if str(r.get("quality") or "").startswith("invalid_patch")
            or "no file hunks" in str(r.get("error") or "")
        )
        hosts.append(
            {
                "provider": p,
                "n": n,
                "n_pass": n_pass,
                "rate": n_pass / n if n else 0.0,
                "qualities": dict(qualities),
                "format_fail": format_fail,
                "cost_sum": sum(cost_ok) if cost_ok else 0.0,
                "cost_mean": _mean(cost_ok),
                "reason_mean": _mean(reason_ok),
                "completion_mean": _mean(comp_ok),
                "reason_share_mean": _mean(ratios),
                "cached_mean": _mean(cache_ok),
                "cached_nonzero": sum(1 for v in cache_ok if v and v > 0),
                "latency_mean": _mean(lat_ok),
            }
        )
    grid = []
    for task in tasks:
        for trial in sorted({int(r.get("trial") or 1) for r in rows}):
            cells = {}
            for p in providers:
                match = [
                    r
                    for r in rows
                    if r.get("task") == task
                    and str(r.get("provider") or "") == p
                    and int(r.get("trial") or 1) == trial
                ]
                cells[p] = match[0] if match else None
            grid.append({"task": task, "trial": trial, "cells": cells})
    meta = rows[0] if rows else {}
    return {
        "run_id": meta.get("run_id"),
        "model": meta.get("model"),
        "k": meta.get("k"),
        "comparable": meta.get("comparable"),
        "sha": meta.get("benchmark_repo_sha"),
        "n": len(rows),
        "providers": providers,
        "tasks": tasks,
        "hosts": hosts,
        "grid": grid,
        "spend": sum(_num(r, "cost") or 0.0 for r in rows),
    }


def _fmt(val: float | None, digits: int = 4) -> str:
    if val is None:
        return ""
    return f"{val:.{digits}f}"


def markdown(summary: dict) -> str:
    hosts = summary["hosts"]
    lines = [
        f"# Provider variance {summary['run_id']}",
        "",
        f"Model `{summary['model']}`  k=`{summary['k']}`  comparable=`{summary['comparable']}`  "
        f"sha `{summary['sha']}`  n=`{summary['n']}`  spend~${_fmt(summary['spend'], 4)}.",
        "",
        "This eval is one-shot. The model returns one unified diff. There are no tool calls, "
        "no agent loop, and no hop-span traces. Reasoning efficiency here is "
        "`reasoning_tokens` vs `completion_tokens`, plus applied-diff identity, not search hops.",
        "",
        "Do not read a winner rank out of these rates. k is small. Several tasks stay red on both hosts.",
        "",
        "## Host totals",
        "",
        "| provider | pass | rate | gold | equivalent | broken | format | cost sum | mean reason_tok | mean completion | reason/completion | mean cached | cached>0 | mean latency_s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for h in hosts:
        q = h["qualities"]
        lines.append(
            f"| {h['provider']} | {h['n_pass']}/{h['n']} | {_fmt(h['rate'], 3)} | "
            f"{q.get('gold', 0)} | {q.get('equivalent', 0)} | {q.get('broken', 0)} | "
            f"{h['format_fail']} | {_fmt(h['cost_sum'], 4)} | {_fmt(h['reason_mean'], 1)} | "
            f"{_fmt(h['completion_mean'], 1)} | {_fmt(h['reason_share_mean'], 3)} | "
            f"{_fmt(h['cached_mean'], 1)} | {h['cached_nonzero']} | {_fmt(h['latency_mean'], 1)} |"
        )
    lines += [
        "",
        "## Per task / trial",
        "",
        "| task | trial | "
        + " | ".join(summary["providers"])
        + " |",
        "|" + "|".join(["---"] * (2 + len(summary["providers"]))) + "|",
    ]
    for row in summary["grid"]:
        cells = []
        for p in summary["providers"]:
            r = row["cells"].get(p)
            if r is None:
                cells.append("")
                continue
            mark = "PASS" if r.get("pass") else "FAIL"
            q = r.get("quality") or ""
            cells.append(f"{mark}/{q}")
        lines.append(f"| {row['task']} | {row['trial']} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Cost, tokens, cache",
        "",
        "Prefix cache can hit on k>1 even when k=1 unique pairs were meant to be uncached. "
        "A nonzero `cached_tokens` count is reported, not treated as contamination unless `comparable` is false.",
        "",
        "| task | provider | trial | pass | quality | cost | prompt | completion | reason_tok | cached | latency_s |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["grid"]:
        for p in summary["providers"]:
            r = row["cells"].get(p)
            if r is None:
                continue
            lines.append(
                f"| {row['task']} | {p} | {row['trial']} | {r.get('pass')} | {r.get('quality') or ''} | "
                f"{r.get('cost') or ''} | {r.get('prompt_tokens') or ''} | {r.get('completion_tokens') or ''} | "
                f"{r.get('reasoning_tokens') or ''} | {r.get('cached_tokens') or ''} | {r.get('latency_s') or ''} |"
            )
    lines += [
        "",
        "## What this can and cannot say",
        "",
        "Same applied sha across hosts on a PASS means they emitted the same repair, not that they thought the same. "
        "CoT is one concatenated stream on disk (`logs/raw-*.json`). Format-fail is a host outcome when the candidate "
        "had no usable hunk after unwrap.",
        "",
    ]
    return "\n".join(lines)


def _html_page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>\nbody{font:16px/1.45 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#111;}"
        "table{border-collapse:collapse;width:100%;font-size:13px;margin:1rem 0;}"
        "th,td{border:1px solid #ccc;padding:4px 6px;text-align:left;vertical-align:top;}"
        "th{background:#f3f3f3;} .pass{color:#0a5;} .fail{color:#a20;} code{font-size:13px;}"
        "h1{font-size:1.4rem;} h2{font-size:1.15rem;margin-top:2rem;}"
        "</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def html_doc(summary: dict) -> str:
    hosts = summary["hosts"]
    host_rows = []
    for h in hosts:
        q = h["qualities"]
        host_rows.append(
            "<tr>"
            + "".join(
                f"<td>{html.escape(str(x))}</td>"
                for x in [
                    h["provider"],
                    f"{h['n_pass']}/{h['n']}",
                    _fmt(h["rate"], 3),
                    q.get("gold", 0),
                    q.get("equivalent", 0),
                    q.get("broken", 0),
                    h["format_fail"],
                    _fmt(h["cost_sum"], 4),
                    _fmt(h["reason_mean"], 1),
                    _fmt(h["completion_mean"], 1),
                    _fmt(h["reason_share_mean"], 3),
                    _fmt(h["cached_mean"], 1),
                    h["cached_nonzero"],
                    _fmt(h["latency_mean"], 1),
                ]
            )
            + "</tr>"
        )
    grid_rows = []
    for row in summary["grid"]:
        tds = [html.escape(row["task"]), str(row["trial"])]
        for p in summary["providers"]:
            r = row["cells"].get(p)
            if r is None:
                tds.append("")
                continue
            mark = "PASS" if r.get("pass") else "FAIL"
            cls = "pass" if r.get("pass") else "fail"
            tds.append(f'<span class="{cls}">{mark}/{html.escape(str(r.get("quality") or ""))}</span>')
        grid_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in tds) + "</tr>")
    detail_rows = []
    for row in summary["grid"]:
        for p in summary["providers"]:
            r = row["cells"].get(p)
            if r is None:
                continue
            cls = "pass" if r.get("pass") else "fail"
            detail_rows.append(
                "<tr>"
                + "".join(
                    f"<td>{html.escape(str(x))}</td>"
                    for x in [
                        row["task"],
                        p,
                        row["trial"],
                        r.get("pass"),
                        r.get("quality") or "",
                        r.get("cost") or "",
                        r.get("prompt_tokens") or "",
                        r.get("completion_tokens") or "",
                        r.get("reasoning_tokens") or "",
                        r.get("cached_tokens") or "",
                        r.get("latency_s") or "",
                    ]
                )
                + "</tr>"
            )
    body = f"""
<h1>Provider variance {html.escape(str(summary['run_id']))}</h1>
<p>Model <code>{html.escape(str(summary['model']))}</code>
k=<code>{html.escape(str(summary['k']))}</code>
comparable=<code>{html.escape(str(summary['comparable']))}</code>
sha <code>{html.escape(str(summary['sha']))}</code>
n=<code>{html.escape(str(summary['n']))}</code>
spend~${html.escape(_fmt(summary['spend'], 4))}.</p>
<p>This eval is one-shot. The model returns one unified diff. There are no tool calls,
no agent loop, and no hop-span traces. Reasoning efficiency here is
<code>reasoning_tokens</code> vs <code>completion_tokens</code>, plus applied-diff identity, not search hops.</p>
<p>Do not read a winner rank out of these rates. k is small. Several tasks stay red on both hosts.</p>
<h2>Host totals</h2>
<table>
<tr><th>provider</th><th>pass</th><th>rate</th><th>gold</th><th>equivalent</th><th>broken</th><th>format</th><th>cost sum</th><th>mean reason_tok</th><th>mean completion</th><th>reason/completion</th><th>mean cached</th><th>cached&gt;0</th><th>mean latency_s</th></tr>
{''.join(host_rows)}
</table>
<h2>Per task / trial</h2>
<table>
<tr><th>task</th><th>trial</th>{''.join(f'<th>{html.escape(p)}</th>' for p in summary['providers'])}</tr>
{''.join(grid_rows)}
</table>
<h2>Cost, tokens, cache</h2>
<p>Prefix cache can hit on k&gt;1. Nonzero <code>cached_tokens</code> is reported, not treated as contamination unless <code>comparable</code> is false.</p>
<table>
<tr><th>task</th><th>provider</th><th>trial</th><th>pass</th><th>quality</th><th>cost</th><th>prompt</th><th>completion</th><th>reason_tok</th><th>cached</th><th>latency_s</th></tr>
{''.join(detail_rows)}
</table>
<h2>What this can and cannot say</h2>
<p>Same applied sha across hosts on a PASS means they emitted the same repair, not that they thought the same.
CoT is one concatenated stream on disk. Format-fail is a host outcome when the candidate had no usable hunk after unwrap.</p>
"""
    return _html_page(f"Provider variance {summary['run_id']}", body)


def write_findings(jsonl: Path, out_dir: Path) -> tuple[Path, Path]:
    rows = load_rows(jsonl)
    summary = summarize(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "FINDINGS.md"
    html_path = out_dir / "FINDINGS.html"
    md_path.write_text(markdown(summary))
    html_path.write_text(html_doc(summary))
    return md_path, html_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    md_path, html_path = write_findings(args.jsonl, args.out)
    print(md_path)
    print(html_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
