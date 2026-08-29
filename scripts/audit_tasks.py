#!/usr/bin/env python3
"""Deterministic public audit: fault red, gold green, mutants rejected."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from catalog import all_ids, spec
from checkouts import materialize, write_checkout
from grader import collect_node_ids, run_pytest
from patches import apply_patch, gold_unified_diff
from prompt_bundle import bundle_for


def _seed(task_id: str) -> Path:
    dest = Path(tempfile.mkdtemp()) / "wh"
    write_checkout(materialize(spec(task_id), ROOT), dest)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(
        ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "seed"],
        cwd=dest,
        check=True,
    )
    return dest


def _collect(tree: Path, tests: Path) -> tuple[int, tuple[str, ...]]:
    return collect_node_ids(tree, tests)


def _mutants(task_id: str) -> tuple[Path, ...]:
    folder = ROOT / spec(task_id).mutant_repo_dir.value
    if not folder.is_dir():
        return ()
    return tuple(sorted(p for p in folder.iterdir() if p.suffix == ".diff"))


def audit_task(task_id: str) -> dict:
    task = spec(task_id)
    errors: list[str] = []
    expl = ROOT / task.explanation_repo_path.value
    if not expl.is_file():
        errors.append("missing explanation")
    else:
        text = expl.read_text()
        if "Also green" in text or "solutions/" in text:
            errors.append("explanation still names solutions/ or Also green")
    if (ROOT / "solutions").exists():
        errors.append("solutions/ tree exists")
    practice = ROOT / task.practice_tests_repo_path.value
    adj = ROOT / task.adjudication_tests_repo_path.value
    fault = _seed(task_id)
    shown_collect, shown_nodes = _collect(fault, practice)
    held_collect, held_nodes = _collect(fault, adj)
    shown_again, shown_nodes_2 = _collect(fault, practice)
    held_again, held_nodes_2 = _collect(fault, adj)
    if shown_nodes != shown_nodes_2 or held_nodes != held_nodes_2:
        errors.append("collection drift")
    shown_rc, _, _, _ = run_pytest(fault, practice)
    held_rc, _, _, _ = run_pytest(fault, adj)
    if shown_collect != 0 or held_collect != 0:
        errors.append("collection error")
    if shown_rc != 1:
        errors.append(f"fault practice exit {shown_rc}")
    if held_rc != 1:
        errors.append(f"fault adjudication exit {held_rc}")
    if not shown_nodes or not held_nodes:
        errors.append("empty collection")
    gold_tree = _seed(task_id)
    gold_diff = gold_unified_diff(ROOT, task)
    gold = apply_patch(gold_tree, task, gold_diff)
    gold_apply = gold.status
    if gold.failure is not None:
        errors.append(f"gold apply {gold.failure.code}")
        gold_shown = gold_held = None
    else:
        gold_shown, _, _, _ = run_pytest(gold_tree, practice)
        gold_held, _, _, _ = run_pytest(gold_tree, adj)
        if gold_shown != 0 or gold_held != 0:
            errors.append(f"gold pytest shown={gold_shown} held={gold_held}")
    mutant_rows = []
    for path in _mutants(task_id):
        tree = _seed(task_id)
        report = apply_patch(tree, task, path.read_bytes())
        row = {"id": path.name, "apply": report.status, "pytest": None}
        if report.failure is not None:
            errors.append(f"mutant {path.name} {report.failure.code}")
            row["apply"] = report.failure.code
        else:
            rc, _, _, _ = run_pytest(tree, practice)
            row["pytest"] = rc
            if rc != 1:
                errors.append(f"mutant {path.name} pytest exit {rc}")
        mutant_rows.append(row)
        shutil.rmtree(tree.parent, ignore_errors=True)
    if not mutant_rows:
        errors.append("no mutants")
    rendered = bundle_for(task_id, ROOT)
    blob = rendered.content
    for needle in (b"tests/", b"tests_adjudication/", b"docs/solutions/", b"mutants/", b"solutions/"):
        if needle in blob:
            errors.append(f"prompt leaked {needle.decode()}")
    shutil.rmtree(fault.parent, ignore_errors=True)
    shutil.rmtree(gold_tree.parent, ignore_errors=True)
    return {
        "task_id": task_id,
        "practice_nodes": list(shown_nodes),
        "adjudication_nodes": list(held_nodes),
        "fault_practice_exit": shown_rc,
        "fault_adjudication_exit": held_rc,
        "gold_apply": gold_apply,
        "gold_practice_exit": gold_shown if gold.failure is None else None,
        "gold_adjudication_exit": gold_held if gold.failure is None else None,
        "mutants": mutant_rows,
        "errors": errors,
        "ok": not errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task")
    ap.add_argument("--show-gold-diff", action="store_true")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args()
    ids = (args.task,) if args.task else all_ids()
    if args.show_gold_diff:
        if len(ids) != 1:
            raise SystemExit("--show-gold-diff requires --task")
        sys.stdout.write(gold_unified_diff(ROOT, spec(ids[0])).decode())
        return 0
    rows = [audit_task(task_id) for task_id in ids]
    if args.format == "json":
        sys.stdout.write(json.dumps(rows, separators=(",", ":"), sort_keys=True) + "\n")
    else:
        for row in rows:
            mark = "ok  " if row["ok"] else "FAIL"
            extra = "" if row["ok"] else " " + "; ".join(row["errors"])
            print(f"{mark} {row['task_id']}{extra}")
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
