from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from harness.campaign_plan import expand, load_campaign
from run_providers import (
    TRIAL_ROW_KEYS,
    HostBreaker,
    _attach_fail_mode,
    _delta_piece,
    _write_last_run,
    done_pair_keys,
    grade_env,
    is_infra_error,
    print_campaign_plan,
    remaining_pairs,
    request_body,
    stream_abort,
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


def test_stream_abort_stall_and_wall():
    assert stream_abort(now=100.0, last_token=50.0, t0=0.0) == "stall"
    assert stream_abort(now=250.0, last_token=249.0, t0=0.0) == "wall"
    assert stream_abort(now=10.0, last_token=9.0, t0=0.0) is None
    assert stream_abort(now=44.0, last_token=0.0, t0=0.0) is None


def test_host_breaker_skips_after_streak():
    br = HostBreaker(streak=3)
    assert not br.skipped("baseten")
    br.fail("baseten")
    br.fail("baseten")
    assert not br.skipped("baseten")
    br.fail("baseten")
    assert br.skipped("baseten")
    br.ok("z-ai")
    br.fail("z-ai")
    assert not br.skipped("z-ai")


def test_is_infra_error():
    assert is_infra_error("HTTP 429 provider=baseten: rate-limited")
    assert is_infra_error("stream stall provider=gmicloud after 45s")
    assert is_infra_error("stream wall provider=gmicloud after 240s")
    assert is_infra_error("stream error provider=gmicloud: Provider returned error")
    assert not is_infra_error("patch_did_not_apply: hunk context is not unique")
    assert not is_infra_error("FAILED tests/test_basis.py")


def test_resume_skips_written_pairs():
    rows = [
        {"task": "watermark_poison", "provider": "z-ai", "trial": 1},
        {"task": "watermark_poison", "provider": "novita", "trial": 1},
    ]
    done = done_pair_keys(rows)
    pairs = trial_pairs(("watermark_poison",), ["z-ai", "novita"], 2)
    left = remaining_pairs(pairs, done)
    assert left == [
        ("watermark_poison", "z-ai", 2),
        ("watermark_poison", "novita", 2),
    ]


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
    from harness.logic_trace import cot_fail_mode, load_hops_file

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
    assert "--continue-run" in proc.stdout
    assert "fireworks-direct" in proc.stdout
    assert "--fireworks-pad-chars" in proc.stdout
    assert "--fireworks-session" in proc.stdout


def test_fireworks_direct_spend_needs_fireworks_key(monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "run_providers.py"),
            "--spend",
            "--variance",
            "-k",
            "1",
            "--providers",
            "fireworks-direct",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "FIREWORKS_API_KEY" in proc.stderr
    assert "OPENROUTER_API_KEY" not in proc.stderr


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
