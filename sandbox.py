"""Docker lifecycle for the public grader image."""

from __future__ import annotations

import json
import os
import subprocess
import tarfile
import uuid
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "docker" / "grader-image.json"
LIMITS = {
    "memory": "256m",
    "pids": "64",
    "cpus": "1",
    "timeout_s": 60,
    "output_bytes": 200_000,
}


def image_lock() -> dict:
    return json.loads(LOCK.read_text())


def run_container(*, archive: Path, response: Path, image: str | None = None) -> dict:
    lock_image = None
    if LOCK.is_file():
        lock_image = image_lock()["image"]
    chosen = image or os.environ.get("DPE_GRADER_IMAGE") or lock_image
    if not chosen:
        raise RuntimeError("grader image is not pinned")
    name = f"dpe-grade-{uuid.uuid4().hex[:12]}"
    create = [
        "docker",
        "create",
        "-i",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--tmpfs",
        "/in:rw,noexec,nosuid,size=32m,uid=1000,gid=1000",
        "--tmpfs",
        "/work:rw,exec,nosuid,size=64m,uid=1000,gid=1000",
        "--tmpfs",
        "/tmp:rw,exec,nosuid,size=32m,uid=1000,gid=1000",
        "--user",
        "1000:1000",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        LIMITS["pids"],
        "--memory",
        LIMITS["memory"],
        "--cpus",
        LIMITS["cpus"],
        "--ulimit",
        "nofile=256:256",
        "--ulimit",
        "fsize=33554432:33554432",
        "--log-driver",
        "none",
        chosen,
    ]
    subprocess.run(create, check=True, capture_output=True)
    payload = BytesIO()
    with tarfile.open(fileobj=payload, mode="w") as tar:
        tar.add(archive, arcname="task.tar")
        tar.add(response, arcname="response.json")
    blob = payload.getvalue()
    try:
        try:
            proc = subprocess.run(
                ["docker", "start", "-a", "-i", name],
                input=blob,
                capture_output=True,
                timeout=LIMITS["timeout_s"],
            )
            reason = None
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            proc = subprocess.CompletedProcess(["docker", "start"], 124, b"", b"timeout")
            reason = "timeout"
        inspect = subprocess.check_output(["docker", "inspect", name], text=True)
        state = json.loads(inspect)[0]["State"]
        stdout = (proc.stdout or b"")[-LIMITS["output_bytes"] :]
        stderr = (proc.stderr or b"")[-20_000:]
        if isinstance(stdout, bytes):
            stdout_text = stdout.decode("utf-8", "replace")
        else:
            stdout_text = stdout
        if isinstance(stderr, bytes):
            stderr_text = stderr.decode("utf-8", "replace")
        else:
            stderr_text = stderr
        if reason is None and state.get("OOMKilled"):
            reason = "oom"
        return {
            "stdout": stdout_text[-LIMITS["output_bytes"] :],
            "stderr": stderr_text[-20_000:],
            "exit_code": int(proc.returncode if proc.returncode is not None else 124),
            "oom": bool(state.get("OOMKilled")),
            "image": chosen,
            "sandbox_reason": reason,
        }
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
