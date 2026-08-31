#!/usr/bin/env python3
"""Spend against Fireworks directly and report prompt-cache hits.

    FIREWORKS_API_KEY=fw_... python scripts/probe_fireworks_cache.py
    FIREWORKS_API_KEY=fw_... python scripts/probe_fireworks_cache.py --task timestamptz_cutoff --rounds 2

OpenRouter is not used. Cache stickiness is sent as JSON ``prompt_cache_key``
plus the ``x-session-affinity`` header.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.fireworks import (  # noqa: E402
    API,
    MODEL,
    request_body,
    request_headers,
    usage_from_fireworks,
)
from harness.prompt_bundle import bundle_for  # noqa: E402


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def _post(api_key: str, body: dict, session_key: str, isolation_key: str | None) -> dict:
    payload = json.dumps(body, separators=(",", ":")).encode()
    req = urllib.request.Request(
        API,
        data=payload,
        headers=request_headers(api_key, session_key, isolation_key),
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read()
            headers = {k: v for k, v in resp.headers.items()}
            status = resp.status
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:800]
        raise SystemExit(f"HTTP {exc.code}: {err}") from exc
    latency_s = round(time.perf_counter() - t0, 3)
    parsed = json.loads(raw.decode("utf-8"))
    usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else {}
    fields = usage_from_fireworks(usage, headers)
    choice = (parsed.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    return {
        "status": status,
        "id": parsed.get("id"),
        "model": parsed.get("model") or MODEL,
        "latency_s": latency_s,
        "finish_reason": choice.get("finish_reason"),
        "content_chars": len(content) if isinstance(content, str) else 0,
        "reasoning_chars": len(reasoning) if isinstance(reasoning, str) else 0,
        "usage": usage,
        **fields,
        "cache_headers": {
            k: v
            for k, v in headers.items()
            if "cache" in k.lower() or k.lower().startswith("fireworks-")
        },
    }


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="timestamptz_cutoff")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=32)
    ap.add_argument("--session", default="dpe-fireworks-cache")
    ap.add_argument("--isolation-key")
    ap.add_argument("--reasoning-effort")
    ap.add_argument(
        "--suffix",
        default="",
        help="Appended after the official prompt so the shared prefix stays stable.",
    )
    args = ap.parse_args()
    if args.rounds < 1:
        print("--rounds must be >= 1", file=sys.stderr)
        return 2
    key = os.environ.get("FIREWORKS_API_KEY", "")
    if not key:
        print("FIREWORKS_API_KEY is not set", file=sys.stderr)
        return 2
    bundle = bundle_for(args.task, ROOT)
    message = bundle.content.decode("utf-8")
    if args.suffix:
        message = message + args.suffix
    session_key = args.session
    rounds = []
    for i in range(args.rounds):
        body = request_body(
            message,
            session_key=session_key,
            max_tokens=args.max_tokens,
            reasoning_effort=args.reasoning_effort,
            isolation_key=args.isolation_key,
        )
        row = _post(key, body, session_key, args.isolation_key)
        row["round"] = i + 1
        rounds.append(row)
        cached = row.get("cached_tokens")
        header_cached = row.get("header_cached_tokens")
        print(
            f"round {i + 1}/{args.rounds}  prompt={row.get('prompt_tokens')}  "
            f"cached={cached}  header_cached={header_cached}  "
            f"write={row.get('cache_write_tokens')}  "
            f"completion={row.get('completion_tokens')}  "
            f"latency_s={row.get('latency_s')}",
            file=sys.stderr,
        )
    hits = sum(1 for r in rounds if isinstance(r.get("cached_tokens"), int) and r["cached_tokens"] > 0)
    report = {
        "backend": "fireworks-direct",
        "api": API,
        "model": MODEL,
        "task": args.task,
        "prompt_sha256": bundle.sha256,
        "prompt_bytes": len(bundle.content),
        "session_key": session_key,
        "isolation_key": args.isolation_key,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "rounds": rounds,
        "cache_hits": hits,
        "cache_hit": hits > 0,
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if hits > 0 or args.rounds == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
