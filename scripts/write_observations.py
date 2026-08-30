#!/usr/bin/env python3
"""Host hop observations from a bake-off jsonl + hop sidecars.

  python scripts/write_observations.py logs/runs/<run_id>.jsonl --out docs/findings/observations
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

from logic_trace import host_hop_rollup


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _fmt(val: float | None, digits: int = 2) -> str:
    if val is None:
        return ""
    return f"{val:.{digits}f}"


def _gmi_read(hosts: list[dict]) -> str:
    by = {h["provider"]: h for h in hosts}
    gmi = by.get("gmicloud")
    if gmi is None:
        return "gmicloud is not in this jsonl."
    others = [h for h in hosts if h["provider"] != "gmicloud"]
    hop_rank = sorted(hosts, key=lambda h: h.get("mean_hops") or 0, reverse=True)
    char_rank = sorted(hosts, key=lambda h: h.get("mean_chars_per_hop") or 0, reverse=True)
    tok_rank = sorted(hosts, key=lambda h: h.get("mean_reasoning_tokens") or 0, reverse=True)
    think_rank = sorted(hosts, key=lambda h: h.get("mean_think_s") or 0, reverse=True)
    tph_rank = sorted(hosts, key=lambda h: h.get("mean_tokens_per_hop") or 0, reverse=True)
    lines = [
        f"GMI Cloud mean think_s is {_fmt(gmi.get('mean_think_s'), 1)}s "
        f"(rank {think_rank.index(gmi)+1} of {len(hosts)}). "
        f"Mean hops {_fmt(gmi.get('mean_hops'), 1)} "
        f"(rank {hop_rank.index(gmi)+1}). "
        f"Mean chars/hop {_fmt(gmi.get('mean_chars_per_hop'), 0)} "
        f"(rank {char_rank.index(gmi)+1}). "
        f"Mean reasoning_tokens {_fmt(gmi.get('mean_reasoning_tokens'), 0)} "
        f"(rank {tok_rank.index(gmi)+1}). "
        f"Mean tokens/hop {_fmt(gmi.get('mean_tokens_per_hop'), 0)} "
        f"(rank {tph_rank.index(gmi)+1}).",
    ]
    if others:
        max_hops = max(others, key=lambda h: h.get("mean_hops") or 0)
        max_chars = max(others, key=lambda h: h.get("mean_chars_per_hop") or 0)
        if (gmi.get("mean_hops") or 0) < (max_hops.get("mean_hops") or 0):
            lines.append(
                f"Longer think is not more hops. {max_hops['provider']} has more mean hops "
                f"({_fmt(max_hops.get('mean_hops'), 1)} vs {_fmt(gmi.get('mean_hops'), 1)})."
            )
        if (gmi.get("mean_chars_per_hop") or 0) >= (max_chars.get("mean_chars_per_hop") or 0):
            lines.append("GMI hops are the longest on average (chars per hop).")
        elif (gmi.get("mean_tokens_per_hop") or 0) >= max(
            (h.get("mean_tokens_per_hop") or 0) for h in others
        ):
            lines.append("GMI spends more reasoning tokens per hop than the other hosts.")
        else:
            lines.append(
                "GMI’s extra wall time lines up with think_s and reasoning_tokens, "
                "not with a uniquely high hop count."
            )
    return " ".join(lines)


def markdown(run_id: str, hosts: list[dict]) -> str:
    lines = [
        "# Observations: GMI Cloud think time vs hop traces",
        "",
        f"Run `{run_id}`. One-shot CoT. Hops are paragraph/claim cuts of the reasoning blob, "
        "not tool-call spans and not an agent loop. No winner rank.",
        "",
        _gmi_read(hosts),
        "",
        "## Host hop size",
        "",
        "| provider | n | pass | mean hops | mean chars/hop | mean chars | mean reason_tok | mean tokens/hop | mean think_s | reason tok / think_s | mean latency_s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for h in hosts:
        lines.append(
            f"| {h['provider']} | {h['n']} | {h['n_pass']}/{h['n']} | "
            f"{_fmt(h.get('mean_hops'), 1)} | {_fmt(h.get('mean_chars_per_hop'), 0)} | "
            f"{_fmt(h.get('mean_chars_total'), 0)} | {_fmt(h.get('mean_reasoning_tokens'), 0)} | "
            f"{_fmt(h.get('mean_tokens_per_hop'), 0)} | {_fmt(h.get('mean_think_s'), 1)} | "
            f"{_fmt(h.get('mean_tokens_per_think_s'), 1)} | {_fmt(h.get('mean_latency_s'), 1)} |"
        )
    lines += [
        "",
        "## How to read this",
        "",
        "More hops means the CoT broke into more claim/paragraph units. Longer hops means each unit is bigger. "
        "Tokens per hop is `reasoning_tokens / hop_count`. Think_s is stream time spent in the reasoning phase. "
        "A host can think longer by writing bigger hops, more hops, or by emitting more tokens inside similar hop counts.",
        "",
        "See [Findings 2](../2/FINDINGS.html) for pass/quality and TPS on the same rows. "
        "Findings 1 (an earlier four-host mix) had GMI mean latency 58.7s and mean reason_tok 2033. "
        "This hop-traced run does not repeat that gap. GMI still has the highest latency here, "
        "but mean think_s sits next to deepinfra.",
        "",
    ]
    return "\n".join(lines)


def html_doc(run_id: str, hosts: list[dict]) -> str:
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
                    _fmt(h.get("mean_hops"), 1),
                    _fmt(h.get("mean_chars_per_hop"), 0),
                    _fmt(h.get("mean_chars_total"), 0),
                    _fmt(h.get("mean_reasoning_tokens"), 0),
                    _fmt(h.get("mean_tokens_per_hop"), 0),
                    _fmt(h.get("mean_think_s"), 1),
                    _fmt(h.get("mean_tokens_per_think_s"), 1),
                    _fmt(h.get("mean_latency_s"), 1),
                ]
            )
            + "</tr>"
        )
    body = f"""
<h1>Observations: GMI Cloud think time vs hop traces</h1>
<p>Run <code>{html.escape(run_id)}</code>. One-shot CoT. Hops are paragraph/claim cuts of the reasoning blob,
not tool-call spans and not an agent loop. No winner rank.</p>
<p>{html.escape(_gmi_read(hosts))}</p>
<h2>Host hop size</h2>
<table>
<tr><th>provider</th><th>n</th><th>pass</th><th>mean hops</th><th>mean chars/hop</th><th>mean chars</th><th>mean reason_tok</th><th>mean tokens/hop</th><th>mean think_s</th><th>reason tok / think_s</th><th>mean latency_s</th></tr>
{''.join(rows)}
</table>
<h2>How to read this</h2>
<p>More hops means the CoT broke into more claim/paragraph units. Longer hops means each unit is bigger.
Tokens per hop is reasoning_tokens / hop_count. Think_s is stream time spent in the reasoning phase.</p>
<p>See <a href="../2/FINDINGS.html">Findings 2</a> for pass/quality and TPS on the same rows.
Findings 1 had GMI mean latency 58.7s and mean reason_tok 2033. This hop-traced run does not repeat that gap.
GMI still has the highest latency here, but mean think_s sits next to deepinfra.</p>
"""
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>Observations: GMI Cloud think time</title>\n"
        "<style>\nbody{font:16px/1.45 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#111;}"
        "table{border-collapse:collapse;width:100%;font-size:13px;margin:1rem 0;}"
        "th,td{border:1px solid #ccc;padding:4px 6px;text-align:left;}"
        "th{background:#f3f3f3;}</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def write_observations(jsonl: Path, out_dir: Path) -> tuple[Path, Path, list[dict]]:
    rows = load_rows(jsonl)
    hosts = host_hop_rollup(rows)
    run_id = str(rows[0].get("run_id") or jsonl.stem) if rows else jsonl.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "OBSERVATIONS.md"
    html_path = out_dir / "OBSERVATIONS.html"
    md_path.write_text(markdown(run_id, hosts))
    html_path.write_text(html_doc(run_id, hosts))
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
