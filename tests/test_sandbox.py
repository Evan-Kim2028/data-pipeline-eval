from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from catalog import spec
from checkouts import materialize, write_checkout
from contracts import environment_digest, git_revision
from grade import _tar_bytes
from patches import gold_unified_diff
from sandbox import LOCK, run_container

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "sentinel-openrouter-test-key-not-for-github"


def _image() -> str:
    proc = subprocess.run(
        ["docker", "inspect", "-f", "{{.Id}}", "dpe-grader:dev"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        pytest.skip("dpe-grader:dev is not built")
    return proc.stdout.strip()


def _artifact(task_id: str, candidate: str, image: str) -> Path:
    sha, dirty = git_revision(ROOT)
    published = sha if not dirty else f"{sha}-dirty"
    digest = image if image.startswith("sha256:") else "sha256:" + "0" * 64
    if image.startswith("sha256:"):
        digest = image
    body = {
        "schema_version": "1",
        "trial_id": f"{task_id}-probe",
        "task_id": task_id,
        "candidate_text": candidate,
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "prompt_sha256": "a" * 64,
        "model": "none",
        "requested_provider": "none",
        "served_provider": None,
        "generation_id": None,
        "usage": {},
        "finish_reason": None,
        "benchmark_repo_sha": published,
        "grader_source_sha": published,
        "grader_image_digest": digest,
        "environment_sha256": environment_digest(ROOT),
    }
    path = Path(tempfile.mkdtemp()) / "response.json"
    path.write_text(json.dumps(body))
    return path


def _archive(task_id: str) -> Path:
    checkout = materialize(spec(task_id), ROOT)
    tmp = Path(tempfile.mkdtemp())
    tree = tmp / "co"
    write_checkout(checkout, tree)
    archive = tmp / "task.tar"
    archive.write_bytes(_tar_bytes(tree, task_id))
    return archive


def _probe_patch(source: str) -> str:
    rel = "warehouse/sidecar/cutoff.py"
    old = (ROOT / "tasks/timestamptz_cutoff/fault" / rel).read_text()
    new_file = Path(tempfile.mkdtemp()) / "new.py"
    old_file = Path(tempfile.mkdtemp()) / "old.py"
    old_file.write_text(old)
    new_file.write_text(source)
    proc = subprocess.run(
        ["diff", "-u", "--label", f"a/{rel}", "--label", f"b/{rel}", str(old_file), str(new_file)],
        capture_output=True,
        text=True,
    )
    return f"diff --git a/{rel} b/{rel}\n{proc.stdout}"


def test_image_lock_is_an_immutable_digest():
    if not LOCK.is_file():
        pytest.skip("grader image lock not published yet")
    lock = json.loads(LOCK.read_text())
    assert lock["digest"].startswith("sha256:")
    assert len(lock["digest"]) == 71


def test_gold_patch_exits_zero_in_the_container():
    image = _image()
    candidate = gold_unified_diff(ROOT, spec("timestamptz_cutoff")).decode()
    result = run_container(
        archive=_archive("timestamptz_cutoff"),
        response=_artifact("timestamptz_cutoff", candidate, image),
        image=image,
    )
    inner = json.loads([ln for ln in result["stdout"].splitlines() if ln.startswith("{")][-1])
    assert result["exit_code"] == 0
    assert inner["patch_status"] == "applied"
    assert inner["shown_exit"] == 0
    assert inner["held_exit"] == 0


def test_invalid_and_noop_patches_are_distinct_from_gold():
    image = _image()
    invalid = run_container(
        archive=_archive("timestamptz_cutoff"),
        response=_artifact("timestamptz_cutoff", "please fix the cutoff\n", image),
        image=image,
    )
    inner = json.loads([ln for ln in invalid["stdout"].splitlines() if ln.startswith("{")][-1])
    assert invalid["exit_code"] == 2
    assert inner["patch_failure"]["code"] == "invalid_patch_format"
    noop_src = """from __future__ import annotations

from datetime import date


def event_at_cutoff(cutoff: date) -> object:
    _keep = cutoff
    return cutoff.isoformat()
"""
    noop = run_container(
        archive=_archive("timestamptz_cutoff"),
        response=_artifact(
            "timestamptz_cutoff",
            _probe_patch(noop_src),
            image,
        ),
        image=image,
    )
    assert noop["exit_code"] == 1
    inner_noop = json.loads(
        [ln for ln in noop["stdout"].splitlines() if ln.startswith("{")][-1]
    )
    assert inner_noop["patch_status"] == "applied"
    assert inner_noop["shown_exit"] != 0


def test_secret_and_network_probes_stay_inside_the_container(monkeypatch):
    image = _image()
    monkeypatch.setenv("OPENROUTER_API_KEY", SENTINEL)
    secret_src = """from __future__ import annotations

from datetime import date
import os


def event_at_cutoff(cutoff: date) -> object:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return f"LEAK:{key}"
    return cutoff.isoformat()
"""
    network_src = """from __future__ import annotations

from datetime import date
import socket


def event_at_cutoff(cutoff: date) -> object:
    try:
        socket.create_connection(("8.8.8.8", 53), 2)
        return "NETWORK_OK"
    except OSError:
        return cutoff.isoformat()
"""
    secret = run_container(
        archive=_archive("timestamptz_cutoff"),
        response=_artifact("timestamptz_cutoff", _probe_patch(secret_src), image),
        image=image,
    )
    blob = secret["stdout"] + secret["stderr"]
    assert SENTINEL not in blob
    assert "LEAK:" not in blob
    network = run_container(
        archive=_archive("timestamptz_cutoff"),
        response=_artifact("timestamptz_cutoff", _probe_patch(network_src), image),
        image=image,
    )
    blob = network["stdout"] + network["stderr"]
    assert "NETWORK_OK" not in blob
    assert network["sandbox_reason"] != "timeout"
    assert json.loads([ln for ln in network["stdout"].splitlines() if ln.startswith("{")][-1])
