from __future__ import annotations

from harness.fireworks import request_body, request_headers, usage_from_fireworks


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
