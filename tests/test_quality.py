from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from catalog import spec
from checkouts import materialize, write_checkout
from quality import classify, tag_quality

ROOT = Path(__file__).resolve().parents[1]


def _seed(task_id: str) -> Path:
    checkout = materialize(spec(task_id), ROOT)
    dest = Path(tempfile.mkdtemp()) / "wh"
    write_checkout(checkout, dest)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(
        ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "seed"],
        cwd=dest,
        check=True,
    )
    return dest


def test_classify_sees_staged_index():
    work = _seed("timestamptz_cutoff")
    extra = work / "warehouse" / "settings.py"
    extra.write_text(extra.read_text() + "\n# staged-only\n")
    subprocess.run(["git", "add", "--", "warehouse/settings.py"], cwd=work, check=True)
    unstaged = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=work,
        capture_output=True,
        text=True,
        check=True,
    )
    assert unstaged.stdout.strip() == ""
    cached = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=work,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "warehouse/settings.py" in cached.stdout
    report = classify("timestamptz_cutoff", work)
    assert "warehouse/settings.py" in report["changed"]
    assert report["quality"] == "other"


def test_held_fail_tagging():
    assert tag_quality("gold", False, True) == "broken"
    assert tag_quality("equivalent", False, False) == "broken"
    assert tag_quality("gold", True, False) == "held_fail"
    assert tag_quality("other", True, False) == "held_fail"
    assert tag_quality("gold", True, True) == "gold"
    assert tag_quality("equivalent", True, True) == "equivalent"
    assert tag_quality("other", True, True) == "other"
