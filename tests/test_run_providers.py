from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from campaign_plan import expand, load_campaign
from run_providers import (
    TRIAL_ROW_KEYS,
    _attach_fail_mode,
    _delta_piece,
    _write_last_run,
    grade_env,
    print_campaign_plan,
    request_body,
    trial_pairs,
    usage_from_openrouter,
)

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


def test_delta_piece_does_not_double():
    reason, content = _delta_piece(
        {"reasoning": "The", "reasoning_details": [{"text": "The"}], "content": "x"}
    )
    assert reason == "The"
    assert content == "x"
    only, _ = _delta_piece({"reasoning": "Hi", "content": ""})
    assert only == "Hi"


def test_usage_from_openrouter_lifts_nested():
    fields = usage_from_openrouter(
        {
            "prompt_tokens": 546,
            "completion_tokens": 667,
            "total_tokens": 1213,
            "cost": 0.00017698,
            "prompt_tokens_details": {"cached_tokens": 512, "cache_write_tokens": 0},
            "completion_tokens_details": {"reasoning_tokens": 121},
            "cost_details": {
                "upstream_inference_prompt_cost": 1.023e-05,
                "upstream_inference_completions_cost": 0.00016675,
            },
        }
    )
    assert fields["cached_tokens"] == 512
    assert fields["reasoning_tokens"] == 121
    assert fields["total_tokens"] == 1213
    assert fields["cost_prompt"] == 1.023e-05
    assert fields["cost_completion"] == 0.00016675


def test_trial_row_keys_frozen():
    required = {
        "trial_id",
        "trial",
        "k",
        "reasoning_tokens",
        "cached_tokens",
        "applied_diff_path",
        "applied_sha256",
        "pass_shown",
        "pass_held",
        "quality",
        "cost_prompt",
        "files_changed_n",
        "hop_count",
        "fail_mode",
        "tps_out",
        "think_s",
        "raw_path",
        "hops_path",
        "cached_tokens",
    }
    assert required <= set(TRIAL_ROW_KEYS)


def test_trial_pairs_interleave_hosts():
    hosts = ["z-ai", "novita", "deepinfra", "gmicloud"]
    pairs = trial_pairs(("watermark_poison", "entity_reload"), hosts, 100)
    assert len(pairs) == 800
    first = [p for _, p, _ in pairs[:8]]
    assert set(first) == set(hosts)
    assert first[:4] == hosts
    assert [p for _, p, _ in pairs[4:8]] == hosts


def test_request_body_hosts_match_except_provider_only():
    a = request_body("checkout", "z-ai")
    b = request_body("checkout", "gmicloud")
    assert a["model"] == b["model"] == "z-ai/glm-5.3-flash"
    assert a["temperature"] == b["temperature"] == 0
    assert a["max_tokens"] == b["max_tokens"] == 131072
    assert a["reasoning"] == b["reasoning"] == {"effort": "high"}
    assert a["stream"] is True and b["stream"] is True
    assert a["stream_options"] == b["stream_options"]
    assert a["messages"] == b["messages"]
    assert a["provider"]["allow_fallbacks"] is False
    assert b["provider"]["allow_fallbacks"] is False
    assert a["provider"]["only"] == ["z-ai"]
    assert b["provider"]["only"] == ["gmicloud"]
    skip = {"provider"}
    for key in a:
        if key in skip:
            continue
        assert a[key] == b[key]


def test_attach_fail_mode_uses_shipped_fold():
    from logic_trace import cot_fail_mode, load_hops_file

    fixtures = ROOT / "tests" / "fixtures" / "hops"
    short = load_hops_file(fixtures / "short-drop_resurrect.json")
    late = load_hops_file(fixtures / "overthink-late_event_close.json")
    row = _attach_fail_mode({"pass": True, "quality": "equivalent"}, short)
    assert row["fail_mode"] == cot_fail_mode(passed=True, quality="equivalent", hops=short)
    assert row["fail_mode"] == "pass"
    row = _attach_fail_mode({"pass": False, "quality": "broken"}, late)
    assert row["fail_mode"] == cot_fail_mode(passed=False, quality="broken", hops=late)
    assert row["fail_mode"] == "overthink"
    row = _attach_fail_mode({"pass": False, "quality": None}, [])
    assert row["fail_mode"] == cot_fail_mode(passed=False, quality=None, hops=[])
    assert row["fail_mode"] == "no_response"


def test_cli_has_k_and_variance():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_providers.py"), "-h"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--variance" in proc.stdout
    assert "-k" in proc.stdout


def test_write_last_run_column_header(tmp_path, monkeypatch):
    import run_providers as rp

    monkeypatch.setattr(rp, "LOGS", tmp_path)
    _write_last_run(
        {
            "run_id": "t",
            "model": "m",
            "reasoning_effort": "high",
            "temperature": 0,
            "k": 1,
            "comparable": True,
            "benchmark_repo_sha": "abc",
        },
        [],
        0.0,
    )
    text = (tmp_path / "LAST_RUN.md").read_text()
    assert "reason_tok" in text
    assert "quality" in text
    assert (tmp_path / "runs" / "t" / "LAST_RUN.md").is_file()


def test_compare_trials_same_diff(tmp_path):
    left = tmp_path / "a.diff"
    right = tmp_path / "b.diff"
    left.write_bytes(b"same")
    right.write_bytes(b"same")
    jsonl = tmp_path / "run.jsonl"
    rows = [
        {
            "task": "entity_reload",
            "trial": 1,
            "provider": "z-ai",
            "pass": True,
            "quality": "gold",
            "applied_diff_path": str(left),
            "applied_sha256": "aa",
        },
        {
            "task": "entity_reload",
            "trial": 1,
            "provider": "novita",
            "pass": True,
            "quality": "gold",
            "applied_diff_path": str(right),
            "applied_sha256": "aa",
        },
    ]
    jsonl.write_text("".join(json.dumps(r) + "\n" for r in rows))
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "compare_trials.py"), str(jsonl)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "same_diff" in proc.stdout
    assert "yes" in proc.stdout


def test_write_findings_markdown_and_html_share_numbers(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "write_findings", ROOT / "scripts" / "write_findings.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    src = ROOT / "tests" / "fixtures" / "campaigns" / "findings-mini.jsonl"
    md_path, html_path = mod.write_findings(src, tmp_path)
    md = md_path.read_text()
    page = html_path.read_text()
    for blob in (md, page):
        assert "TESTK3" in blob
        assert "z-ai" in blob
        assert "novita" in blob
        assert "one-shot" in blob
        assert "reasoning_tokens" in blob or "reason_tok" in blob
        assert "cached" in blob
        assert "tps_out" in blob
        assert "hops" in blob
        assert "<script type=\"module\"" not in blob
    assert "<html" in page


def test_grade_env_drops_provider_secrets(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")
    monkeypatch.setenv("PATH", os.environ.get("PATH", "/usr/bin"))
    env = grade_env()
    assert "OPENROUTER_API_KEY" not in env
    assert "PATH" in env
