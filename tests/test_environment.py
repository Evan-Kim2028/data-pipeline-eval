from __future__ import annotations

from pathlib import Path

from contracts import environment_digest, python_version_pin

ROOT = Path(__file__).resolve().parents[1]


def test_python_pin_is_a_patch_version():
    major, minor, patch = python_version_pin(ROOT)
    assert (major, minor, patch) == (3, 14, 3)


def test_environment_digest_changes_when_lock_changes(tmp_path: Path):
    (tmp_path / ".python-version").write_text("3.14.3\n")
    (tmp_path / "requirements.lock").write_text("pytest==9.1.1\n")
    first = environment_digest(tmp_path)
    (tmp_path / "requirements.lock").write_text("pytest==9.1.0\n")
    second = environment_digest(tmp_path)
    assert first != second
    assert len(first) == 64


def test_lockfile_pins_hashes():
    text = (ROOT / "requirements.lock").read_text()
    assert "--hash=sha256:" in text
    assert "pytest==9.1.1" in text
