"""Strict unified-diff validation and a single git-apply route."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from catalog import spec
from contracts import TaskSpec

FORMAT = "format"
POLICY = "policy"
APPLY = "apply"

INVALID_PATCH_FORMAT = "invalid_patch_format"
PATCH_POLICY_REJECTED = "patch_policy_rejected"
PATCH_DID_NOT_APPLY = "patch_did_not_apply"

_DENIED_PARTS = frozenset(
    {
        "tests",
        "tests_held",
        "tests_adjudication",
        "solutions",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "logs",
        "results",
    }
)
_DIFF_GIT = re.compile(r"^diff --git a/(.+) b/(.+)$")
_HEADER_A = re.compile(r"^--- a/(.+)$")
_HEADER_B = re.compile(r"^\+\+\+ b/(.+)$")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_LANGS = frozenset({"diff", "patch", "udiff"})


def _is_hunk_header(line: str) -> bool:
    if line == "@@" or line.startswith("@@ "):
        return True
    return bool(_HUNK.match(line))


@dataclass(frozen=True)
class PatchFailure(Exception):
    cls: str
    code: str
    diagnostic: str

    def __str__(self) -> str:
        return f"{self.code}: {self.diagnostic}"


@dataclass(frozen=True)
class ValidatedPatch:
    sha256: str
    content: bytes
    paths: tuple[str, ...]


@dataclass(frozen=True)
class PatchReport:
    task_id: str
    response_sha256: str
    status: str
    changed_paths: tuple[str, ...]
    failure: PatchFailure | None


def _fail(cls: str, code: str, diagnostic: str) -> PatchFailure:
    return PatchFailure(cls=cls, code=code, diagnostic=diagnostic[:400])


def _posix(path: str) -> str:
    if not path or path.startswith("/") or "\\" in path or "\x00" in path:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "path is not relative POSIX")
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise _fail(POLICY, PATCH_POLICY_REJECTED, "path traversal")
    if any(p in _DENIED_PARTS for p in parts):
        raise _fail(POLICY, PATCH_POLICY_REJECTED, f"denied path {path}")
    return path


def _fence_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    i = 0
    while True:
        start = text.find("```", i)
        if start < 0:
            break
        nl = text.find("\n", start + 3)
        if nl < 0:
            break
        lang = text[start + 3 : nl].strip().split()[0].lower() if text[start + 3 : nl].strip() else ""
        end = text.find("```", nl + 1)
        if end < 0:
            break
        blocks.append((lang, text[nl + 1 : end]))
        i = end + 3
    return blocks


def _is_diff_body(body: str) -> bool:
    stripped = body.lstrip("\n")
    return stripped.startswith(("diff --git ", "--- a/"))


def _strip_trailing_prose(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    last = -1
    for i, line in enumerate(lines):
        if line.startswith(
            ("diff --git ", "--- ", "+++ ", "@@", "+", "-", " ", "\\")
        ) or line == "":
            last = i
    if last < 0:
        return text if text.endswith("\n") else text + "\n"
    return "\n".join(lines[: last + 1]) + "\n"


def unwrap_candidate(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "```" not in text:
        return _strip_trailing_prose(text)
    blocks = _fence_blocks(text)
    if not blocks:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "markdown fence")
    chosen = None
    for lang, body in blocks:
        if lang in _DIFF_LANGS or _is_diff_body(body):
            chosen = body
            break
    if chosen is None:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "markdown fence")
    return _strip_trailing_prose(chosen)


def _old_side(hunk: list[str]) -> list[str]:
    out: list[str] = []
    for line in hunk:
        if line.startswith("\\"):
            continue
        if not line:
            out.append("")
            continue
        if line[0] in " -":
            out.append(line[1:])
    return out


def _hunk_counts(hunk: list[str]) -> tuple[int, int]:
    old_n = new_n = 0
    for line in hunk:
        if line.startswith("\\"):
            continue
        if not line:
            old_n += 1
            new_n += 1
            continue
        tag = line[0]
        if tag in " -":
            old_n += 1
        if tag in " +":
            new_n += 1
    return old_n, new_n


def _locate(file_lines: list[str], needle: list[str]) -> int:
    if not needle:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "empty hunk context")
    n = len(needle)
    matches = [
        i + 1
        for i in range(len(file_lines) - n + 1)
        if file_lines[i : i + n] == needle
    ]
    if len(matches) != 1:
        raise _fail(APPLY, PATCH_DID_NOT_APPLY, "hunk context is not unique")
    return matches[0]


def rewrite_hunks(text: str, work: Path) -> bytes:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    path = ""
    while i < len(lines):
        line = lines[i]
        header_a = _HEADER_A.match(line)
        if header_a:
            path = header_a.group(1)
        if _is_hunk_header(line):
            end = i + 1
            while end < len(lines) and not (
                _is_hunk_header(lines[end])
                or lines[end].startswith(("diff --git ", "--- "))
            ):
                end += 1
            hunk = lines[i + 1 : end]
            old_n, new_n = _hunk_counts(hunk)
            if not path:
                raise _fail(FORMAT, INVALID_PATCH_FORMAT, "hunk without file header")
            file_lines = (work / path).read_text(encoding="utf-8").splitlines()
            start = _locate(file_lines, _old_side(hunk))
            out.append(f"@@ -{start},{old_n} +{start},{new_n} @@")
            out.extend(hunk)
            i = end
            continue
        out.append(line)
        i += 1
    return ("\n".join(out) + "\n").encode("utf-8")


def parse_unified_diff(raw: bytes, allowed: tuple[str, ...]) -> ValidatedPatch:
    if not raw or b"\x00" in raw:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "empty or NUL patch")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "not utf-8") from exc
    if "```" in text:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "markdown fence")
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    if not body.startswith(("diff --git ", "--- a/")):
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "not a bare unified diff")
    if "GIT binary patch" in body or "\nrename from " in body or "\ncopy from " in body:
        raise _fail(POLICY, PATCH_POLICY_REJECTED, "binary, rename, or copy")
    if "/dev/null" in body:
        raise _fail(POLICY, PATCH_POLICY_REJECTED, "new or deleted file")
    paths: list[str] = []
    seen: set[str] = set()
    lines = body.splitlines()
    i = 0
    hunks = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            match = _DIFF_GIT.match(line)
            if not match or match.group(1) != match.group(2):
                raise _fail(FORMAT, INVALID_PATCH_FORMAT, "mismatched diff --git paths")
            path = _posix(match.group(1))
            if path in seen:
                raise _fail(POLICY, PATCH_POLICY_REJECTED, f"duplicate file {path}")
            seen.add(path)
            paths.append(path)
            i += 1
            continue
        if line.startswith("--- "):
            a = _HEADER_A.match(line)
            if not a:
                raise _fail(FORMAT, INVALID_PATCH_FORMAT, "bad --- header")
            if i + 1 >= len(lines):
                raise _fail(FORMAT, INVALID_PATCH_FORMAT, "missing +++ header")
            b = _HEADER_B.match(lines[i + 1])
            if not b:
                raise _fail(FORMAT, INVALID_PATCH_FORMAT, "bad +++ header")
            path = _posix(a.group(1))
            if path != _posix(b.group(1)):
                raise _fail(FORMAT, INVALID_PATCH_FORMAT, "a/b path mismatch")
            if path not in seen:
                seen.add(path)
                paths.append(path)
            i += 2
            continue
        if _is_hunk_header(line):
            hunks += 1
        i += 1
    if not paths or hunks == 0:
        raise _fail(FORMAT, INVALID_PATCH_FORMAT, "no file hunks")
    allowed_set = set(allowed)
    extra = [p for p in paths if p not in allowed_set]
    if extra:
        raise _fail(POLICY, PATCH_POLICY_REJECTED, f"undeclared path {extra[0]}")
    content = body.encode("utf-8")
    if not content.endswith(b"\n"):
        content += b"\n"
    return ValidatedPatch(
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
        paths=tuple(paths),
    )


def apply_patch(work: Path, task: TaskSpec, raw: bytes) -> PatchReport:
    allowed = tuple(p.value for p in task.editable_checkout_paths)
    try:
        unwrapped = unwrap_candidate(raw.decode("utf-8")).encode("utf-8")
        parsed = parse_unified_diff(unwrapped, allowed)
    except UnicodeDecodeError:
        failure = _fail(FORMAT, INVALID_PATCH_FORMAT, "not utf-8")
        return PatchReport(task.id, hashlib.sha256(raw).hexdigest(), "failed", (), failure)
    except PatchFailure as exc:
        return PatchReport(task.id, hashlib.sha256(raw).hexdigest(), "failed", (), exc)
    for path in parsed.paths:
        target = work / path
        if not target.is_file() or target.is_symlink() or target.stat().st_nlink != 1:
            failure = _fail(POLICY, PATCH_POLICY_REJECTED, f"target is not a regular file {path}")
            return PatchReport(task.id, parsed.sha256, "failed", (), failure)
    try:
        rewritten = rewrite_hunks(parsed.content.decode("utf-8"), work)
    except PatchFailure as exc:
        return PatchReport(task.id, parsed.sha256, "failed", (), exc)
    proc = subprocess.run(
        ["git", "apply", "--index", "--whitespace=error", "-p1"],
        cwd=work,
        input=rewritten,
        capture_output=True,
    )
    if proc.returncode != 0:
        diagnostic = (proc.stderr or proc.stdout).decode("utf-8", "replace")[:400]
        failure = _fail(APPLY, PATCH_DID_NOT_APPLY, diagnostic or "git apply failed")
        subprocess.run(["git", "reset", "--hard", "-q"], cwd=work, check=False)
        subprocess.run(["git", "clean", "-qfd"], cwd=work, check=False)
        return PatchReport(task.id, parsed.sha256, "failed", (), failure)
    status = subprocess.check_output(
        ["git", "diff", "--cached", "--name-status"], cwd=work, text=True
    )
    changed: list[str] = []
    for line in status.splitlines():
        if not line:
            continue
        code, path = line.split("\t", 1)
        if code != "M":
            failure = _fail(POLICY, PATCH_POLICY_REJECTED, f"unexpected change {code} {path}")
            subprocess.run(["git", "reset", "--hard", "-q"], cwd=work, check=False)
            return PatchReport(task.id, parsed.sha256, "failed", (), failure)
        changed.append(path)
    if set(changed) != set(parsed.paths):
        failure = _fail(POLICY, PATCH_POLICY_REJECTED, "staged paths mismatch parsed paths")
        subprocess.run(["git", "reset", "--hard", "-q"], cwd=work, check=False)
        return PatchReport(task.id, parsed.sha256, "failed", (), failure)
    return PatchReport(task.id, parsed.sha256, "applied", tuple(changed), None)


def gold_unified_diff(root: Path, task: TaskSpec) -> bytes:
    if len(task.editable_checkout_paths) != 1:
        raise PatchFailure(POLICY, PATCH_POLICY_REJECTED, "gold diff expects one editable path")
    rel = task.editable_checkout_paths[0].value
    old = root / task.fault_repo_path.value / rel
    new = root / task.gold_repo_path.value
    proc = subprocess.run(
        ["diff", "-u", "--label", f"a/{rel}", "--label", f"b/{rel}", str(old), str(new)],
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 1):
        raise PatchFailure(FORMAT, INVALID_PATCH_FORMAT, "gold diff failed")
    body = proc.stdout
    if not body.endswith("\n"):
        body += "\n"
    return f"diff --git a/{rel} b/{rel}\n{body}".encode()


def apply_task_patch(root: Path, work: Path, task_id: str, raw: bytes) -> PatchReport:
    return apply_patch(work, spec(task_id), raw)
