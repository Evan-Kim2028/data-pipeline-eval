from __future__ import annotations

from harness.fireworks import (
    estimate_cost,
    request_body,
    request_headers,
    session_key_for_task,
    stable_pad,
    usage_from_fireworks,
)


def test_stable_pad_is_deterministic_and_exact():
    assert stable_pad(0) == ""
    assert stable_pad(-3) == ""
    first = stable_pad(4000)
    assert first == stable_pad(4000)
    assert len(first) == 4000
    assert first.startswith("static warehouse context")


def test_request_body_sets_cache_affinity():
    body = request_body("checkout", session_key="sess-1", max_tokens=32)
    assert body["model"] == "accounts/fireworks/models/glm-5p3-flash"
    assert body["prompt_cache_key"] == "sess-1"
    assert body["user"] == "sess-1"
    assert body["stream"] is False
    assert body["messages"] == [{"role": "user", "content": "checkout"}]
    assert "provider" not in body


def test_request_headers_pin_replica():
    headers = request_headers("fw_test", "sess-1", "iso-9")
    assert headers["Authorization"] == "Bearer fw_test"
    assert headers["x-session-affinity"] == "sess-1"
    assert headers["x-prompt-cache-isolation-key"] == "iso-9"


def test_usage_from_fireworks_prefers_body_then_headers():
    fields = usage_from_fireworks(
        {
            "prompt_tokens": 1200,
            "completion_tokens": 16,
            "total_tokens": 1216,
            "prompt_tokens_details": {
                "cached_tokens": 1024,
                "created_cache_tokens": 176,
            },
        },
        {
            "Fireworks-Cached-Prompt-Tokens": "1024",
            "Fireworks-Prompt-Tokens": "1200",
        },
    )
    assert fields["cached_tokens"] == 1024
    assert fields["cache_write_tokens"] == 176
    assert fields["header_cached_tokens"] == 1024
    assert fields["prompt_tokens"] == 1200


def test_estimate_cost_uses_published_glm_flash_rates():
    assert estimate_cost(prompt_tokens=1_000_000, cached_tokens=0, completion_tokens=0) == 0.15
    assert estimate_cost(prompt_tokens=1_000_000, cached_tokens=1_000_000, completion_tokens=0) == 0.029
    assert estimate_cost(prompt_tokens=0, cached_tokens=0, completion_tokens=1_000_000) == 0.5
    assert estimate_cost() is None


def test_session_key_pins_the_task():
    assert session_key_for_task("field_readd") == "dpe-field_readd"


def test_usage_from_fireworks_falls_back_to_headers():
    fields = usage_from_fireworks(
        {},
        {
            "fireworks-cached-prompt-tokens": "512",
            "fireworks-prompt-tokens": "800",
        },
    )
    assert fields["cached_tokens"] == 512
    assert fields["prompt_tokens"] == 800
    assert fields["header_cached_tokens"] == 512
