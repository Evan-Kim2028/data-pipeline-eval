from logic_trace import attach_throughput, hops_from_reasoning


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
