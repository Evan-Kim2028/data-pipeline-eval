from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from campaign_plan import expand, load_campaign
from run_providers import grade_env, print_campaign_plan

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "tests" / "fixtures" / "campaigns" / "mini.json"


def test_campaign_plan_is_byte_identical_twice(capsys):
    print_campaign_plan(MINI)
    first = capsys.readouterr().out
    print_campaign_plan(MINI)
    second = capsys.readouterr().out
    assert first == second
    lines = [json.loads(line) for line in first.splitlines() if line]
    specs = expand(load_campaign(MINI))
    assert [row["trial_id"] for row in lines] == [spec.trial_id for spec in specs]
    assert [row["prompt_hash"] for row in lines] == [spec.prompt_hash for spec in specs]
    assert [row["seed"] for row in lines] == [spec.seed for spec in specs]


def test_cli_plan_matches_python_helper():
    first = subprocess.run(
        [sys.executable, str(ROOT / "run_providers.py"), "--campaign", str(MINI), "--plan"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    second = subprocess.run(
        [sys.executable, str(ROOT / "run_providers.py"), "--campaign", str(MINI), "--plan"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert first.stdout == second.stdout
    assert first.returncode == 0


def test_campaign_without_spend_is_refused():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_providers.py"), "--campaign", str(MINI)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "Refusing" in proc.stderr


def test_grade_env_drops_provider_secrets(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")
    monkeypatch.setenv("PATH", os.environ.get("PATH", "/usr/bin"))
    env = grade_env()
    assert "OPENROUTER_API_KEY" not in env
    assert "PATH" in env
