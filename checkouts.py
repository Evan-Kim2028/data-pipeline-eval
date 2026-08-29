"""Materialize one faulted candidate checkout from a validated TaskSpec."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from contracts import ContractError, TaskCheckout, TaskSpec, git_revision


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def materialize(spec: TaskSpec, root: Path) -> TaskCheckout:
    warehouse = root / "warehouse"
    if not warehouse.is_dir():
        raise ContractError("warehouse/ is missing")
    tmp = Path(tempfile.mkdtemp(prefix="task-checkout-"))
    dest = tmp / "checkout"
    try:
        shutil.copytree(warehouse, dest)
        fault = root / spec.fault_repo_path.value
        if fault.is_dir():
            shutil.copytree(fault, dest, dirs_exist_ok=True)
        files: list[tuple[str, bytes]] = []
        for path in sorted(p for p in dest.rglob("*") if p.is_file()):
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            rel = path.relative_to(dest).as_posix()
            files.append((rel, path.read_bytes()))
        hashes = tuple((rel, _hash_bytes(data)) for rel, data in files)
        digest = _hash_bytes("\n".join(f"{rel} {h}" for rel, h in hashes).encode())
        sha, dirty = git_revision(root)
        if dirty:
            sha = f"{sha}-dirty"
        checkout = TaskCheckout(
            task_id=spec.id,
            benchmark_repo_sha=sha,
            files=tuple(files),
            ordered_hashes=hashes,
            checkout_digest=digest,
        )
        _assert_context(spec, checkout)
        entrypoint_source(spec, checkout)
        return checkout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _assert_context(spec: TaskSpec, checkout: TaskCheckout) -> None:
    available = {rel for rel, _ in checkout.files}
    for path in spec.context_checkout_paths:
        if path.value not in available:
            raise ContractError(f"{spec.id}: context missing {path.value}")
    for path in spec.editable_checkout_paths:
        if path.value not in available:
            raise ContractError(f"{spec.id}: editable missing {path.value}")


def write_checkout(checkout: TaskCheckout, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for rel, data in checkout.files:
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def entrypoint_source(spec: TaskSpec, checkout: TaskCheckout) -> bytes:
    parts = spec.entrypoint.split(".")
    if len(parts) < 2:
        raise ContractError(f"{spec.id}: entrypoint is not dotted")
    rel = "/".join(parts[:-1]) + ".py"
    mapping = checkout.file_map()
    if rel not in mapping:
        raise ContractError(f"{spec.id}: entrypoint module {rel} missing from checkout")
    attr = parts[-1]
    source = mapping[rel]
    if f"def {attr}".encode() not in source and f"{attr} =".encode() not in source:
        raise ContractError(f"{spec.id}: {attr} not found in {rel}")
    return source
