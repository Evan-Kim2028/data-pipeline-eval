#!/usr/bin/env python3
"""Clean-clone release checks. Does not call providers or create tags."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.catalog import all_ids  # noqa: E402
from harness.prompt_bundle import all_bundles  # noqa: E402


def _stdlib_only(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    allowed = {"harness", "report_stats"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in allowed and top not in sys.stdlib_module_names:
                    return False
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top not in allowed and top not in sys.stdlib_module_names:
                return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=ROOT / "campaigns" / "official-v1.json")
    ap.add_argument("--report", type=Path, default=ROOT / "reports" / "official-v1")
    ap.add_argument("--tag", default="benchmark-v1.0.0")
    args = ap.parse_args()
    errors: list[str] = []
    if (ROOT / "solutions").exists():
        errors.append("solutions/ must not exist")
    ids = all_ids()
    if len(ids) != 15:
        errors.append(f"catalog has {len(ids)} tasks")
    lock = json.loads((ROOT / "docker" / "grader-image.json").read_text())
    if not str(lock.get("digest", "")).startswith("sha256:"):
        errors.append("grader image digest is not immutable")
    for task_id, bundle in all_bundles(ROOT).items():
        text = bundle.content.decode("utf-8")
        if "tests_adjudication" in text or "def test_" in text:
            errors.append(f"prompt leak in {task_id}")
    if not _stdlib_only(ROOT / "scripts" / "report.py"):
        errors.append("scripts/report.py is not standard-library-only")
    if not _stdlib_only(ROOT / "harness" / "report_stats.py"):
        errors.append("harness/report_stats.py is not standard-library-only")
    if args.manifest.is_file():
        man = json.loads(args.manifest.read_text())
        if list(man.get("task_ids") or []) != list(ids):
            errors.append("official manifest task_ids must follow catalog.all_ids()")
        if man.get("grader_image_digest") != lock.get("digest"):
            errors.append("official manifest image digest mismatch")
    compile_rc = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(ROOT / "scripts" / "grade.py"), str(ROOT / "scripts" / "report.py")],
        cwd=ROOT,
    ).returncode
    if compile_rc != 0:
        errors.append("compileall failed")
    if args.report.is_dir() and (args.report / "checksums.txt").is_file():
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "report.py"),
                "--manifest",
                str(args.manifest),
                "--trials",
                str(args.manifest.parent.parent / "results" / "official-v1" / "trials.jsonl"),
                "--out",
                str(args.report),
                "--check",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append("report --check failed")
    if errors:
        for err in errors:
            print(f"FAIL {err}")
        return 1
    print(f"ok release checks ({args.tag})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
