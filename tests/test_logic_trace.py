from logic_trace import (
    attach_throughput,
    hop_size_stats,
    hops_from_reasoning,
    host_hop_rollup,
    task_hop_rollup,
)


def test_hops_split_paragraphs_and_numbers():
    text = (
        "The bug: watermark advances too soon.\n\n"
        "Fix: persist last_ok first.\n\n"
        "1. keep the cursor\n"
        "2. write the checkpoint\n"
        "3. then advance"
    )
    hops = hops_from_reasoning(text)
    assert len(hops) >= 4
    assert hops[0]["text"].startswith("The bug:")
    assert hops[0]["chars"] == len(hops[0]["text"])


def test_hops_empty():
    assert hops_from_reasoning("") == []
    assert hops_from_reasoning("   ") == []


def test_attach_throughput_tps():
    row = attach_throughput(
        {
            "latency_s": 10.0,
            "completion_tokens": 500,
            "prompt_tokens": 100,
            "total_tokens": 600,
            "reasoning_tokens": 200,
            "think_s": 8.0,
        }
    )
    assert row["tps_out"] == 50.0
    assert row["tps_total"] == 60.0
    assert row["tps_reason"] == 20.0
    assert row["tps_think"] == 25.0


def test_hop_size_stats_from_splitter():
    multi = hops_from_reasoning("The bug: x.\n\nFix: y.\n\nAlso: z.")
    assert len(multi) == 3
    stats = hop_size_stats(multi, reasoning_tokens=90, think_s=9.0)
    assert stats["hop_count"] == 3
    assert stats["chars_per_hop"] == stats["chars_total"] / 3
    assert stats["tokens_per_hop"] == 30
    assert stats["tokens_per_think_s"] == 10.0
    wall = "Word. " * 80
    long = hops_from_reasoning(wall)
    assert len(long) > 1
    long_stats = hop_size_stats(long, reasoning_tokens=400)
    assert long_stats["hop_count"] == len(long)
    assert long_stats["chars_per_hop"] == long_stats["chars_total"] / long_stats["hop_count"]


def test_host_hop_rollup_chars_per_hop():
    rows = [
        {
            "provider": "gmicloud",
            "pass": True,
            "reasoning_tokens": 200,
            "think_s": 20.0,
            "latency_s": 25.0,
            "hops": [{"chars": 400, "text": "a" * 400}, {"chars": 400, "text": "b" * 400}],
        },
        {
            "provider": "novita",
            "pass": True,
            "reasoning_tokens": 50,
            "think_s": 5.0,
            "latency_s": 10.0,
            "hops": [{"chars": 80, "text": "c" * 80}],
        },
    ]
    roll = {item["provider"]: item for item in host_hop_rollup(rows)}
    assert roll["gmicloud"]["mean_hops"] == 2
    assert roll["gmicloud"]["mean_chars_per_hop"] == 400
    assert roll["gmicloud"]["mean_tokens_per_hop"] == 100
    assert roll["novita"]["mean_hops"] == 1
    assert roll["novita"]["mean_chars_per_hop"] == 80


def test_task_hop_rollup_bands_and_pass_fail_hops():
    hops_ok = [{"chars": 20, "text": "a" * 20}]
    hops_trip = [{"chars": 50, "text": "b" * 50}] * 8
    rows = []
    for i in range(3):
        rows.append(
            {
                "task": "drop_resurrect",
                "provider": "gmicloud",
                "pass": True,
                "quality": "equivalent",
                "think_s": 2.0,
                "hops": hops_ok,
            }
        )
        rows.append(
            {
                "task": "late_event_close",
                "provider": "gmicloud",
                "pass": False,
                "quality": "broken",
                "think_s": 40.0,
                "hops": hops_trip,
            }
        )
    tasks = {t["task"]: t for t in task_hop_rollup(rows, difficulty_of={"drop_resurrect": "very_hard", "late_event_close": "very_hard"})}
    assert tasks["drop_resurrect"]["band"] == "solved"
    assert tasks["drop_resurrect"]["mean_hops_pass"] == 1
    assert tasks["late_event_close"]["band"] == "trip"
    assert tasks["late_event_close"]["mean_hops_fail"] == 8
    assert tasks["late_event_close"]["estimated_difficulty"] == "very_hard"


def test_write_observations_from_shipped_rollup(tmp_path):
    import importlib.util
    import json
    from pathlib import Path

    hops_path = tmp_path / "h.json"
    hops_path.write_text(
        json.dumps({"hops": [{"chars": 40, "text": "x" * 40}, {"chars": 40, "text": "y" * 40}]})
    )
    jsonl = tmp_path / "run.jsonl"
    jsonl.write_text(
        json.dumps(
            {
                "run_id": "OBS1",
                "task": "drop_resurrect",
                "provider": "gmicloud",
                "pass": True,
                "reasoning_tokens": 80,
                "think_s": 8.0,
                "latency_s": 10.0,
                "hops_path": str(hops_path),
            }
        )
        + "\n"
        + json.dumps(
            {
                "run_id": "OBS1",
                "task": "drop_resurrect",
                "provider": "z-ai",
                "pass": False,
                "reasoning_tokens": 20,
                "think_s": 2.0,
                "latency_s": 4.0,
                "hops_path": str(hops_path),
            }
        )
        + "\n"
    )
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "write_observations", root / "scripts" / "write_observations.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    md_path, html_path, hosts = mod.write_observations(jsonl, tmp_path / "out")
    md = md_path.read_text()
    page = html_path.read_text()
    for blob in (md, page):
        assert "gmicloud" in blob
        assert "z-ai" in blob
        assert "hop" in blob.lower()
        assert "one-shot" in blob.lower() or "not tool" in blob.lower()
        assert "very_hard" in blob or "complexity" in blob.lower()
        assert "drop_resurrect" in blob
        assert "<script type=\"module\"" not in blob
    by = {h["provider"]: h for h in hosts}
    assert by["gmicloud"]["mean_chars_per_hop"] == 40
    assert by["gmicloud"]["mean_tokens_per_hop"] == 40
