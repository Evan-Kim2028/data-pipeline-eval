"""Direct Fireworks chat-completions helpers. OpenRouter is not involved.

Fireworks serverless prompt cache is replica-local and on by default.
Sticky routing is required for hits: prefer ``prompt_cache_key`` in the
body (takes priority over ``user``), and send the same value as
``x-session-affinity``. Cache metrics land in response headers
(``fireworks-cached-prompt-tokens``) and in
``usage.prompt_tokens_details.cached_tokens``.
"""

from __future__ import annotations

API = "https://api.fireworks.ai/inference/v1/chat/completions"
MODEL = "accounts/fireworks/models/glm-5p3-flash"

CACHE_HEADER = "fireworks-cached-prompt-tokens"
PROMPT_HEADER = "fireworks-prompt-tokens"
SESSION_HEADER = "x-session-affinity"
ISOLATION_HEADER = "x-prompt-cache-isolation-key"
PAD_UNIT = "static warehouse context for prefix cache. "


def stable_pad(n: int) -> str:
    """Repeat a fixed block so a short official prompt can exceed the cache floor."""
    if n <= 0:
        return ""
    return (PAD_UNIT * ((n // len(PAD_UNIT)) + 1))[:n]


def request_body(
    message: str,
    *,
    session_key: str,
    max_tokens: int,
    temperature: float = 0,
    reasoning_effort: str | None = None,
    isolation_key: str | None = None,
    stream: bool = False,
) -> dict:
    body: dict = {
        "model": MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
        "prompt_cache_key": session_key,
        "user": session_key,
        "messages": [{"role": "user", "content": message}],
        "perf_metrics_in_response": True,
    }
    if stream:
        body["stream_options"] = {"include_usage": True}
    if reasoning_effort:
        body["reasoning"] = {"effort": reasoning_effort}
        body["reasoning_effort"] = reasoning_effort
    if isolation_key:
        body["prompt_cache_isolation_key"] = isolation_key
    return body


def request_headers(api_key: str, session_key: str, isolation_key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        SESSION_HEADER: session_key,
    }
    if isolation_key:
        headers[ISOLATION_HEADER] = isolation_key
    return headers


def _header(headers: dict | None, name: str) -> str | None:
    if not headers:
        return None
    want = name.lower()
    for key, val in headers.items():
        if str(key).lower() == want:
            text = str(val).strip()
            return text if text else None
    return None


def _int_or_none(val: object) -> int | None:
    if isinstance(val, bool) or val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float) and val.is_integer():
        return int(val)
    if isinstance(val, str) and val.strip().lstrip("-").isdigit():
        return int(val)
    return None


def usage_from_fireworks(usage: dict | None, headers: dict | None = None) -> dict:
    """Lift Fireworks cache fields the same way OpenRouter usage is flattened."""
    usage = usage or {}
    pdet = usage.get("prompt_tokens_details")
    cdet = usage.get("completion_tokens_details")
    pdet = pdet if isinstance(pdet, dict) else {}
    cdet = cdet if isinstance(cdet, dict) else {}
    cached = pdet.get("cached_tokens")
    if cached is None:
        cached = _int_or_none(_header(headers, CACHE_HEADER))
    prompt = usage.get("prompt_tokens")
    if prompt is None:
        prompt = _int_or_none(_header(headers, PROMPT_HEADER))
    return {
        "prompt_tokens": prompt,
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cached_tokens": cached,
        "cache_write_tokens": pdet.get("created_cache_tokens", pdet.get("cache_write_tokens")),
        "reasoning_tokens": cdet.get("reasoning_tokens"),
        "header_cached_tokens": _int_or_none(_header(headers, CACHE_HEADER)),
        "header_prompt_tokens": _int_or_none(_header(headers, PROMPT_HEADER)),
    }
