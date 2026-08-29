"""In-image grader: unpack archive, apply patch, run public tests, emit JSON."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

from catalog import spec as load_spec
from patches import apply_patch

IN = Path("/in")
WORK = Path("/work")
MAX_OUTPUT = 200_000


def run_pytest(tree: Path, tests: Path) -> tuple[int, str, int, int]:
    if not tests.is_dir() or not any(tests.glob("test_*.py")):
        return 0, "", 0, 0
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tree)
    env["HOME"] = env.get("HOME", "/tmp")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("OPENROUTER_API_KEY", None)
    collect = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only", str(tests)],
        cwd=tree,
        env=env,
        capture_output=True,
        text=True,
    )
    collected = 0
    for line in collect.stdout.splitlines():
        if "::" in line:
            collected += 1
        elif line.strip().endswith("tests collected") or " tests collected in " in line:
            head = line.strip().split()[0]
            if head.isdigit():
                collected = int(head)
    if collect.returncode != 0:
        blob = (collect.stdout + collect.stderr)[-MAX_OUTPUT:]
        return collect.returncode, blob, collected, collected or 1
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(tests)],
        cwd=tree,
        env=env,
        capture_output=True,
        text=True,
    )
    blob = (proc.stdout + proc.stderr)[-MAX_OUTPUT:]
    failed = 0
    for line in reversed(proc.stdout.splitlines()):
        if "failed" in line:
            parts = line.replace(",", "").split()
            for i, tok in enumerate(parts):
                if tok == "failed" and i and parts[i - 1].isdigit():
                    failed = int(parts[i - 1])
            break
    if proc.returncode == 0:
        failed = 0
    elif failed == 0:
        failed = collected or 1
    if failed > collected:
        collected = failed
    return proc.returncode, blob, collected, failed


def grade_tree(*, tree: Path, practice: Path, adjudication: Path, task, candidate: bytes) -> dict:
    report = apply_patch(tree, task, candidate)
    shown_rc, shown_out, shown_n, shown_fail = run_pytest(tree, practice)
    held_rc, held_out, held_n, held_fail = run_pytest(tree, adjudication)
    output = (shown_out + "\n" + held_out)[-MAX_OUTPUT:]
    return {
        "task_id": task.id,
        "patch_status": report.status,
        "patch_sha256": report.response_sha256,
        "changed_paths": list(report.changed_paths),
        "patch_failure": None
        if report.failure is None
        else {
            "cls": report.failure.cls,
            "code": report.failure.code,
            "diagnostic": report.failure.diagnostic,
        },
        "shown_exit": shown_rc,
        "held_exit": held_rc,
        "tests_collected": shown_n + held_n,
        "tests_failed": shown_fail + held_fail,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "output": output[-800:],
    }


def main() -> int:
    archive = IN / "task.tar"
    response = json.loads((IN / "response.json").read_text())
    dest = WORK / "bundle"
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:") as tar:
        tar.extractall(dest, filter="data")
    policy = json.loads((dest / "policy.json").read_text())
    tree = dest / "checkout"
    subprocess.run(["git", "init", "-q"], cwd=tree, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tree, check=True)
    subprocess.run(
        ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "seed"],
        cwd=tree,
        check=True,
    )
    task = load_spec(policy["task_id"])
    raw = response["candidate_text"].encode("utf-8")
    payload = grade_tree(
        tree=tree,
        practice=dest / "tests",
        adjudication=dest / "tests_held",
        task=task,
        candidate=raw,
    )
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    if payload["patch_failure"] is not None:
        return 2
    if payload["shown_exit"] != 0 or payload["held_exit"] != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
