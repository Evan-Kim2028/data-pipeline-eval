"""Render official candidate messages from TaskSpec + TaskCheckout only."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from catalog import TASKS, spec
from checkouts import materialize
from contracts import TaskCheckout, TaskSpec

DENIED_MARKERS = (
    "tests_held/",
    "tests_adjudication/",
    "docs/solutions/",
    "solutions/",
    ".git/",
    "__pycache__",
    ".pytest_cache",
    "\n### tests/",
    "\n## tests/",
)

SHARED_INSTRUCTIONS = (
    "The checkout is the warehouse package at its current (faulted) revision.\n"
    "Edit only the disclosed files. Return one unified diff against that checkout.\n"
    "Do not add, delete, or rename files. Do not modify tests."
)


@dataclass(frozen=True)
class PromptBundle:
    task_id: str
    checkout_digest: str
    entrypoint: str
    ordered_context_paths: tuple[str, ...]
    editable_paths: tuple[str, ...]
    content: bytes
    sha256: str


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def render(task: TaskSpec, checkout: TaskCheckout, incident: str) -> PromptBundle:
    if checkout.task_id != task.id:
        raise ValueError("checkout task_id does not match spec")
    files = checkout.file_map()
    sections = [
        _lf(incident).strip(),
        "",
        "## Entrypoint",
        task.entrypoint,
        "",
        "## Editable paths",
        "\n".join(p.value for p in task.editable_checkout_paths),
        "",
        "## Instructions",
        SHARED_INSTRUCTIONS,
        "",
        "## Production context",
    ]
    ordered: list[str] = []
    for path in task.context_checkout_paths:
        rel = path.value
        ordered.append(rel)
        text = files[rel].decode("utf-8")
        sections.append(f"### {rel}")
        sections.append(text if text.endswith("\n") else text + "\n")
    body = "\n".join(sections)
    if not body.endswith("\n"):
        body += "\n"
    content = body.encode("utf-8")
    _assert_clean(content)
    return PromptBundle(
        task_id=task.id,
        checkout_digest=checkout.checkout_digest,
        entrypoint=task.entrypoint,
        ordered_context_paths=tuple(ordered),
        editable_paths=tuple(p.value for p in task.editable_checkout_paths),
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _assert_clean(content: bytes) -> None:
    text = content.decode("utf-8")
    for marker in DENIED_MARKERS:
        if marker in text:
            raise ValueError(f"candidate message leaked {marker!r}")


def bundle_for(task_id: str, root: Path) -> PromptBundle:
    item = spec(task_id)
    checkout = materialize(item, root)
    incident = (root / item.prompt_repo_path.value).read_text(encoding="utf-8")
    return render(item, checkout, incident)


def all_bundles(root: Path) -> dict[str, PromptBundle]:
    return {task.id: bundle_for(task.id, root) for task in TASKS}
