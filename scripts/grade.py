#!/usr/bin/env python3
"""Offline public grader. No provider credentials. No network inside the container."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
import tempfile
import time
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.catalog import spec
from harness.checkouts import materialize, write_checkout
from harness.contracts import (
    SCHEMA_VERSION,
    GradeReport,
    encode_json,
    environment_digest,
)
from harness.sandbox import image_lock, run_container

_PROXY = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "OPENROUTER_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "SSH_AUTH_SOCK",
)


def _tar_bytes(checkout_dir: Path, task_id: str) -> bytes:
    task = spec(task_id)
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:

        def add(path: Path, arc: str) -> None:
            tar.add(path, arcname=arc, recursive=True, filter=_safe)

        add(checkout_dir, "checkout")
        add(ROOT / task.practice_tests_repo_path.value, "tests")
        held = ROOT / task.adjudication_tests_repo_path.value
        if held.is_dir():
            add(held, "tests_adjudication")
        policy = json.dumps(
            {
                "task_id": task_id,
                "editable": [p.value for p in task.editable_checkout_paths],
            }
        ).encode()
        info = tarfile.TarInfo("policy.json")
        info.size = len(policy)
        tar.addfile(info, BytesIO(policy))
    return buf.getvalue()


def _safe(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    name = tarinfo.name
    if "__pycache__" in name or name.endswith(".pyc") or ".git" in name.split("/"):
        return None
    return tarinfo


def load_artifact(path: Path) -> dict:
    data = json.loads(path.read_text())
    for key in (
        "task_id",
        "candidate_text",
        "candidate_sha256",
        "benchmark_repo_sha",
        "grader_source_sha",
        "grader_image_digest",
        "environment_sha256",
    ):
        if key not in data:
            raise SystemExit(f"response artifact missing {key}")
    digest = hashlib.sha256(data["candidate_text"].encode()).hexdigest()
    if digest != data["candidate_sha256"]:
        raise SystemExit("candidate_sha256 mismatch")
    return data


def _scrub_env() -> None:
    for key in list(os.environ):
        if key in _PROXY or key.endswith("_API_KEY") or key.endswith("_TOKEN"):
            os.environ.pop(key, None)


def _inner_report(stdout: str) -> dict:
    lines = [ln for ln in stdout.splitlines() if ln.strip().startswith("{")]
    if not lines:
        return {}
    return json.loads(lines[-1])


def verify_pins(artifact: dict, lock: dict, *, environment_sha256: str) -> None:
    locked = lock.get("grader_source_sha")
    if not locked:
        raise SystemExit("grader image lock missing grader_source_sha")
    if artifact["grader_source_sha"] != locked:
        raise SystemExit("grader_source_sha mismatch")
    if artifact["grader_image_digest"] != lock["digest"]:
        raise SystemExit("grader image digest mismatch")
    if artifact["environment_sha256"] != environment_sha256:
        raise SystemExit("environment_sha256 mismatch")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--response", required=True, type=Path)
    args = ap.parse_args()
    _scrub_env()
    artifact = load_artifact(args.response)
    lock = image_lock()
    verify_pins(artifact, lock, environment_sha256=environment_digest(ROOT))
    task_id = artifact["task_id"]
    checkout = materialize(spec(task_id), ROOT)
    tmp = Path(tempfile.mkdtemp())
    tree = tmp / "checkout"
    write_checkout(checkout, tree)
    archive = tmp / "task.tar"
    archive.write_bytes(_tar_bytes(tree, task_id))
    with tarfile.open(archive, "r") as tar:
        names = tar.getnames()
    if any("docs/solutions" in n or "/mutants/" in n or "gold" == n for n in names):
        raise SystemExit("archive leaked solutions or mutants")
    started = time.monotonic()
    result = run_container(archive=archive, response=args.response, image=lock["image"])
    duration = time.monotonic() - started
    inner = _inner_report(result["stdout"])
    patch_sha = inner.get("patch_sha256") or hashlib.sha256(
        artifact["candidate_text"].encode()
    ).hexdigest()
    output_sha = inner.get("output_sha256") or hashlib.sha256(
        result["stdout"].encode()
    ).hexdigest()
    collected = int(inner.get("tests_collected") or 0)
    failed = int(inner.get("tests_failed") or 0)
    if failed > collected:
        collected = failed
    report = GradeReport(
        schema_version=SCHEMA_VERSION,
        trial_id=str(artifact.get("trial_id") or f"{task_id}-offline"),
        task_id=task_id,
        benchmark_repo_sha=artifact["benchmark_repo_sha"],
        grader_source_sha=artifact["grader_source_sha"],
        grader_image_digest=lock["digest"],
        command=("python", "-m", "harness.grader"),
        exit_code=result["exit_code"],
        tests_collected=collected,
        tests_failed=failed,
        duration_s=round(duration, 4),
        output_sha256=output_sha,
        patch_sha256=patch_sha,
        sandbox_reason=result.get("sandbox_reason"),
    )
    print(encode_json(report))
    if inner:
        print(json.dumps(inner, separators=(",", ":")))
    elif result["stderr"].strip():
        print(result["stderr"].strip()[:400], file=__import__("sys").stderr)
    if result["sandbox_reason"] or result["exit_code"] != 0:
        return 1 if result["exit_code"] != 0 else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
