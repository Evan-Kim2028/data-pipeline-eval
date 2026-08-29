#!/usr/bin/env python3
"""Deterministic campaign report. Standard library only. No ranking."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import report_stats


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"missing trials file {path}")
    rows = []
    seen = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            raise SystemExit("truncated trials stream")
        row = json.loads(line)
        tid = row.get("trial_id")
        if tid in seen:
            raise SystemExit(f"duplicate trial_id {tid}")
        seen.add(tid)
        rows.append(row)
    return rows


def _checksums(paths: list[Path]) -> str:
    lines = []
    for path in sorted(paths, key=lambda p: p.name):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    return "\n".join(lines) + "\n"


def generate(manifest: dict, rows: list[dict], *, seed: int) -> dict:
    providers = list(manifest["requested_providers"])
    if any(row.get("requested_provider") not in providers for row in rows):
        raise SystemExit("trial requested_provider is not in the manifest")
    e2e = report_stats.end_to_end_rate(rows)
    lo, hi = report_stats.bootstrap_task_rate(rows, seed=seed)
    e2e = dict(e2e)
    e2e["interval"] = [lo, hi]
    pairs = []
    for i, left in enumerate(providers):
        for right in providers[i + 1 :]:
            pairs.append(report_stats.paired_end_to_end(rows, left, right))
    tasks = report_stats.task_rates(rows)
    n_tasks = len({row["task_id"] for row in rows})
    return {
        "campaign_id": manifest["campaign_id"],
        "n_rows": len(rows),
        "end_to_end": e2e,
        "conditional_repair": report_stats.conditional_repair_rate(rows),
        "failures": report_stats.failure_counts(rows),
        "providers": [report_stats.summarize_provider(rows, p) for p in providers],
        "pairs": pairs,
        "tasks": tasks,
        "mde": report_stats.minimum_detectable_effect(n_tasks=n_tasks, seed=seed),
        "analysis_seed": seed,
        "bootstrap_samples": 10000,
        "interval_note": (
            "Task-clustered 95% percentile interval over this campaign's task ids, "
            "not over every possible repair task."
        ),
    }


def _markdown(report: dict) -> str:
    e2e = report["end_to_end"]
    lines = [
        f"# {report['campaign_id']}",
        "",
        f"End-to-end: {e2e['numerator']}/{e2e['denominator']} = {e2e['rate']:.3f}",
        f"Interval: {e2e['interval'][0]:.3f} to {e2e['interval'][1]:.3f}",
        "",
        "No ranking. Provider order follows the manifest.",
        "",
    ]
    for item in report["providers"]:
        lines.append(
            f"- {item['requested_provider']}: "
            f"{item['end_to_end']['numerator']}/{item['end_to_end']['denominator']}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--trials", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
    except FileNotFoundError:
        print(f"missing manifest {args.manifest}", file=sys.stderr)
        return 2
    try:
        rows = _load_jsonl(args.trials)
        report = generate(manifest, rows, seed=args.seed)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out = args.out
    blob = json.dumps(report, sort_keys=True, indent=2) + "\n"
    md = _markdown(report)
    json_path = out / "report.json"
    md_path = out / "report.md"
    difficulty = json.dumps(
        {
            "campaign_id": manifest["campaign_id"],
            "method": "one minus end-to-end success rate by task",
            "tasks": report["tasks"],
        },
        sort_keys=True,
        indent=2,
    ) + "\n"
    if args.check:
        if not json_path.is_file() or json_path.read_text() != blob:
            print("report artifacts drifted", file=sys.stderr)
            return 1
        if md_path.read_text() != md:
            print("report artifacts drifted", file=sys.stderr)
            return 1
        print("ok")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    json_path.write_text(blob)
    md_path.write_text(md)
    (out / "difficulty.json").write_text(difficulty)
    (out / "checksums.txt").write_text(
        _checksums([json_path, md_path, out / "difficulty.json"])
    )
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
