from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "tests" / "fixtures" / "campaigns" / "mini.json"
TRIALS = ROOT / "tests" / "fixtures" / "campaigns" / "report-trials.jsonl"


def test_report_twice_is_byte_identical(tmp_path: Path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    cmd = [
        sys.executable,
        str(ROOT / "report.py"),
        "--manifest",
        str(MINI),
        "--trials",
        str(TRIALS),
        "--out",
        str(first),
        "--seed",
        "42",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "report.py"),
            "--manifest",
            str(MINI),
            "--trials",
            str(TRIALS),
            "--out",
            str(second),
            "--seed",
            "42",
        ],
        check=True,
        cwd=ROOT,
    )
    for name in ("report.json", "report.md", "difficulty.json", "checksums.txt"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    check = subprocess.run(
        [
            sys.executable,
            str(ROOT / "report.py"),
            "--manifest",
            str(MINI),
            "--trials",
            str(TRIALS),
            "--out",
            str(first),
            "--check",
            "--seed",
            "42",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0
    report = json.loads((first / "report.json").read_text())
    blob = json.dumps(report).lower()
    assert "rank" not in blob
    assert "winner" not in blob
    assert report["end_to_end"]["denominator"] == 8
    assert report["conditional_repair"]["denominator"] == 7


def test_report_rejects_duplicates_and_unknown_providers(tmp_path: Path):
    trials = tmp_path / "trials.jsonl"
    trials.write_text(TRIALS.read_text() + TRIALS.read_text().splitlines()[0] + "\n")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "report.py"),
            "--manifest",
            str(MINI),
            "--trials",
            str(trials),
            "--out",
            str(tmp_path / "out"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    rows = [json.loads(line) for line in TRIALS.read_text().splitlines()]
    rows[0]["requested_provider"] = "nope"
    bad = tmp_path / "bad.jsonl"
    bad.write_text("".join(json.dumps(row) + "\n" for row in rows))
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "report.py"),
            "--manifest",
            str(MINI),
            "--trials",
            str(bad),
            "--out",
            str(tmp_path / "out2"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
