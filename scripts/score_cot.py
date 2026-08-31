#!/usr/bin/env python3
"""Score hop-0 vs gold and last claim vs applied hunk.

    python scripts/score_cot.py logs/runs/<id>.jsonl
    python scripts/score_cot.py logs/runs/<id>.jsonl --out /tmp/cot
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.cot_align import CLAIMS, score_run_row  # noqa: E402


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def score_jsonl(path: Path) -> list[dict]:
    rows = load_rows(path)
    hops_dir = path.parent / "hops"
    patches_dir = path.parent / "patches"
    out = []
    for row in rows:
        scored = score_run_row(row, hops_dir=hops_dir, patches_dir=patches_dir)
        if scored is not None:
            out.append(scored)
    return out


def _read(scores: list[dict]) -> str:
    if not scores:
        return "No scored trials (only late_event_close, frozen_basis, rebuild_wipe)."
    bits = []
    labels = Counter(str(s.get("hop0_label")) for s in scores)
    bits.append(
        "Hop-0 labels: "
        + ", ".join(f"{k} {v}" for k, v in sorted(labels.items()))
        + "."
    )
    fails = [s for s in scores if s.get("pass") is False]
    if fails:
        trap_miss = [s for s in fails if s.get("hop0_label") != "trap_named"]
        impl = [s for s in fails if s.get("hunk_align") == "implements_claim"]
        bits.append(
            f"{len(fails)} scored fails. "
            f"{len(trap_miss)} never name the trap in hop 0. "
            f"{len(impl)} then implement that incomplete claim in the hunk."
        )
    return " ".join(bits)


def markdown(run_id: str, scores: list[dict]) -> str:
    lines = [
        "# CoT alignment",
        "",
        f"Run `{run_id}`. Offline only. Gold/trap lexemes come from `docs/solutions`.",
        "Hop-0 is the first non-instruction hop. Last claim is the last mechanism hop.",
        "",
        _read(scores),
        "",
        "| task | pass | fail_mode | hop0 | trap in hop0 | last-claim→hunk | vs gold edit | mech hops | cached |",
        "|---|---|---|---|---|---|---|---:|---:|",
    ]
    for s in scores:
        trap = ",".join(s.get("hop0_trap") or []) or "—"
        lines.append(
            f"| `{s['task']}` | {s.get('pass')} | {s.get('fail_mode') or ''} | "
            f"{s.get('hop0_label')} | {trap} | {s.get('hunk_align')} | "
            f"{s.get('vs_gold_edit')} | {s.get('mechanism_hops')} | "
            f"{s.get('cached_tokens') if s.get('cached_tokens') is not None else ''} |"
        )
    lines += ["", "## Hop-0 and last claim", ""]
    for s in scores:
        lines += [
            f"### `{s['task']}` t{s.get('trial')} ({s.get('run_id')})",
            "",
            f"- hop0 ({s.get('hop0_label')}): {s.get('hop0_text')}",
            f"- last claim → hunk `{s.get('hunk_align')}` / `{s.get('vs_gold_edit')}`: {s.get('last_claim')}",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path, nargs="+")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    all_scores: list[dict] = []
    for path in args.jsonl:
        scores = score_jsonl(path)
        all_scores.extend(scores)
        run_id = str((scores[0].get("run_id") if scores else None) or path.stem)
        text = markdown(run_id, scores)
        print(text)
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / f"{path.stem}.md").write_text(text)
            (args.out / f"{path.stem}.json").write_text(json.dumps(scores, indent=2) + "\n")
    if args.out and len(args.jsonl) > 1:
        (args.out / "combined.json").write_text(json.dumps(all_scores, indent=2) + "\n")
        (args.out / "combined.md").write_text(markdown("combined", all_scores))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
