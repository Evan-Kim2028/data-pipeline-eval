"""Offline CoT alignment: hop-0 vs gold mechanism, last claim vs applied hunk.

Gold and trap lexemes come from docs/solutions/*.md. They are never sent
to a model. Hops that only restate the shared instructions are dropped
before scoring.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness.logic_trace import load_hops_file

# Offline only. Keys are folded; multi-word keys match as phrases.
CLAIMS: dict[str, dict[str, tuple[str, ...]]] = {
    "late_event_close": {
        "symptom": ("processing_at", "event_at", "late"),
        "gold": ("event_at", "start", "end"),
        "trap": ("lateness", "in_processing_window"),
        "edit": ("processing_at", "event_at"),
        "must_hunk": ("lateness",),
    },
    "frozen_basis": {
        "symptom": ("empty", "unique"),
        "gold": ("existing", "incoming", "unique_fn"),
        "trap": ("firstloadstate", "absorb", "seen"),
        "edit": ("incoming", "existing"),
        "must_hunk": ("absorb",),
    },
    "rebuild_wipe": {
        "symptom": ("clear", "staging", "restart"),
        "gold": ("last_ok", "persist"),
        "trap": ("restart",),
        "edit": ("last_ok",),
        "must_hunk": ("last_ok + 1",),
    },
}

_META = (
    "provide unified diff",
    "provide reasoning",
    "provide claims",
    "edit only",
    "editable path",
    "editable:",
    "unified diff",
    "produce the diff",
    "keep response",
    "per instructions",
    "that's it",
)
_WORD = re.compile(r"[a-z0-9_+]+")


def _fold(text: str) -> str:
    return " ".join(_WORD.findall((text or "").lower().replace("+", " + ")))


def _has(folded: str, key: str) -> bool:
    needle = _fold(key)
    if not needle:
        return False
    return f" {needle} " in f" {folded} "


def hits(text: str, keys: tuple[str, ...]) -> list[str]:
    folded = _fold(text)
    return [key for key in keys if _has(folded, key)]


def is_meta_hop(hop: dict) -> bool:
    text = str(hop.get("text") or "").strip()
    if not text:
        return True
    if text in {"Diff:", "```"} or text.startswith("```"):
        return True
    folded = _fold(text)
    if len(folded.split()) <= 4 and any(_has(folded, token) for token in ("diff", "claims")):
        return True
    return any(_has(folded, token) for token in _META) and len(folded.split()) <= 16


def mechanism_hops(hops: list[dict]) -> list[dict]:
    return [hop for hop in hops if not is_meta_hop(hop)]


def hunk_text(diff: str) -> str:
    lines = []
    for line in (diff or "").splitlines():
        if line.startswith(("+++", "---", "diff ", "index ", "@@")):
            continue
        if line.startswith(("+", "-")):
            lines.append(line[1:])
    return "\n".join(lines)


def _share(found: list[str], keys: tuple[str, ...]) -> float | None:
    if not keys:
        return None
    return len(found) / len(keys)


def hop0_score(text: str, spec: dict[str, tuple[str, ...]]) -> dict:
    symptom = hits(text, spec["symptom"])
    gold = hits(text, spec["gold"])
    trap = hits(text, spec["trap"])
    if trap:
        label = "trap_named"
    elif gold:
        label = "gold_named"
    elif symptom:
        label = "symptom_only"
    else:
        label = "miss"
    return {
        "hop0_label": label,
        "hop0_symptom": symptom,
        "hop0_gold": gold,
        "hop0_trap": trap,
        "hop0_symptom_share": _share(symptom, spec["symptom"]),
        "hop0_gold_share": _share(gold, spec["gold"]),
        "hop0_trap_share": _share(trap, spec["trap"]),
    }


def hunk_score(claim: str, diff: str, spec: dict[str, tuple[str, ...]]) -> dict:
    claim_hits = hits(claim, spec["edit"])
    hunk_hits = hits(hunk_text(diff), spec["edit"])
    if not spec["edit"]:
        align = "n/a"
    elif claim_hits and set(claim_hits) <= set(hunk_hits):
        align = "implements_claim"
    elif hunk_hits and not claim_hits:
        align = "unclaimed"
    elif claim_hits and not hunk_hits:
        align = "weaker_than_claim"
    elif claim_hits and hunk_hits:
        align = "partial_hunk"
    else:
        align = "no_edit_claim"
    gold_hits = hits(hunk_text(diff), spec["edit"] + spec["trap"])
    must = spec.get("must_hunk") or ()
    must_hits = hits(hunk_text(diff), must)
    if must and not must_hits:
        vs_gold = "trap_absent"
    elif must and must_hits:
        vs_gold = "mentions_trap"
    elif hunk_hits and len(hunk_hits) < len(spec["edit"]):
        vs_gold = "incomplete"
    elif hunk_hits:
        vs_gold = "complete_or_close"
    else:
        vs_gold = "other"
    return {
        "claim_edit": claim_hits,
        "hunk_edit": hunk_hits,
        "hunk_align": align,
        "vs_gold_edit": vs_gold,
        "hunk_goldish": gold_hits,
    }


def score_trial(
    *,
    task: str,
    hops: list[dict],
    diff: str,
    pass_: bool | None = None,
    fail_mode: str | None = None,
    quality: str | None = None,
) -> dict | None:
    spec = CLAIMS.get(task)
    if spec is None:
        return None
    mech = mechanism_hops(hops)
    hop0 = str((mech[0] if mech else hops[0] if hops else {}).get("text") or "")
    last = str((mech[-1] if mech else {}).get("text") or "")
    row = {
        "task": task,
        "pass": pass_,
        "quality": quality,
        "fail_mode": fail_mode,
        "hop_count": len(hops),
        "mechanism_hops": len(mech),
        "meta_hops": len(hops) - len(mech),
        "hop0_text": hop0[:400],
        "last_claim": last[:400],
        **hop0_score(hop0, spec),
        **hunk_score(last, diff, spec),
    }
    return row


def load_diff(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def score_run_row(row: dict, hops_dir: Path | None = None, patches_dir: Path | None = None) -> dict | None:
    task = str(row.get("task") or "")
    if task not in CLAIMS:
        return None
    hops: list[dict] = []
    hop_path = row.get("hops_path")
    if hop_path and Path(str(hop_path)).is_file():
        hops = load_hops_file(Path(str(hop_path)))
    elif hops_dir is not None:
        name = f"{task}__{row.get('provider')}__t{row.get('trial')}.json"
        candidate = hops_dir / name
        if candidate.is_file():
            hops = load_hops_file(candidate)
    diff = ""
    diff_path = row.get("applied_diff_path")
    if diff_path and Path(str(diff_path)).is_file():
        diff = load_diff(Path(str(diff_path)))
    elif patches_dir is not None:
        name = f"{task}__{row.get('provider')}__t{row.get('trial')}.diff"
        candidate = patches_dir / name
        if candidate.is_file():
            diff = load_diff(candidate)
    scored = score_trial(
        task=task,
        hops=hops,
        diff=diff,
        pass_=row.get("pass") if isinstance(row.get("pass"), bool) else None,
        fail_mode=None if row.get("fail_mode") is None else str(row.get("fail_mode")),
        quality=None if row.get("quality") is None else str(row.get("quality")),
    )
    if scored is None:
        return None
    scored["run_id"] = row.get("run_id")
    scored["provider"] = row.get("provider")
    scored["trial"] = row.get("trial")
    scored["cached_tokens"] = row.get("cached_tokens")
    return scored
