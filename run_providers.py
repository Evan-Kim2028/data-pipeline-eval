#!/usr/bin/env python3
"""Optional OpenRouter bake-off. Refuses to spend unless you pass --spend.

    python run_providers.py                     # prints this help, exit 2
    python run_providers.py --spend --smoke     # timestamptz_cutoff on z-ai, novita
    python run_providers.py --spend --golden    # 5-task ladder on z-ai, novita
    python run_providers.py --spend --hard      # very_hard tasks on z-ai, novita
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from catalog import GOLDEN_IDS, all_ids, default_ids, hard_ids, spec
from contracts import environment_digest, git_revision
from patches import apply_patch
from prompt_bundle import all_bundles, bundle_for
from quality import classify

ROOT = Path(__file__).resolve().parent


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


_load_dotenv()
MODEL = "z-ai/glm-5.3-flash"
API = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_PROVIDERS = (
    "z-ai",
    "novita",
    "deepinfra",
    "together",
    "fireworks",
    "siliconflow",
    "friendli",
    "modal",
)
TASKS = default_ids()
ALL_TASKS = all_ids()
MAX_SPEND_USD = 5.0
MAX_TOKENS = 131072
TEMPERATURE = 0
REASONING_EFFORT = "high"
HTTP_TIMEOUT_S = 600
LOGS = ROOT / "logs"
PRINT_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
SPEND_LOCK = threading.Lock()
SEM_LOCK = threading.Lock()
PROVIDER_SEMS: dict[str, threading.Semaphore] = {}
DEFAULT_JOBS = 8
PER_PROVIDER = 1
RETRY_429 = 4


def _message_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text") or part.get("content") or ""))
        joined = "".join(parts).strip()
        if joined:
            return joined
    for key in ("reasoning", "reasoning_content"):
        val = msg.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def _delta_piece(delta: dict) -> tuple[str, str]:
    reason: list[str] = []
    for key in ("reasoning", "reasoning_content"):
        val = delta.get(key)
        if isinstance(val, str) and val:
            reason.append(val)
    details = delta.get("reasoning_details")
    if isinstance(details, list):
        for item in details:
            if isinstance(item, dict):
                bit = item.get("text") or item.get("content") or ""
                if bit:
                    reason.append(str(bit))
    content = delta.get("content")
    if not isinstance(content, str):
        content = ""
    return "".join(reason), content


def _out(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def _tick(task: str, provider: str, t0: float, phase: str, reason_n: int, content_n: int, note: str = "") -> None:
    elapsed = time.perf_counter() - t0
    line = (
        f"  {task}/{provider}  {elapsed:6.1f}s  {phase:5}  "
        f"think={reason_n}c  patch={content_n}c"
    )
    if note:
        line += f"  {note}"
    _out(line)


def _complete(message: str, provider: str, *, task: str) -> tuple[str, dict]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    body = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"effort": REASONING_EFFORT},
        "stream": True,
        "stream_options": {"include_usage": True},
        "provider": {"only": [provider], "allow_fallbacks": False},
        "messages": [
            {
                "role": "user",
                "content": message,
            }
        ],
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "HTTP-Referer": "https://github.com/Evan-Kim2028",
            "X-OpenRouter-Title": "data-pipeline-eval",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    last_print = t0
    phase = "wait"
    reason_buf: list[str] = []
    content_buf: list[str] = []
    reason_n = 0
    content_n = 0
    usage: dict = {}
    gen_id = "unknown"
    finish_reason = None
    host = provider
    _tick(task, provider, t0, phase, 0, 0, "requesting")
    resp = None
    last_http = b""
    for attempt in range(RETRY_429):
        try:
            resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S)
            break
        except urllib.error.HTTPError as exc:
            last_http = exc.read()
            if exc.code == 429 and attempt + 1 < RETRY_429:
                wait = 5 * (2 ** attempt)
                _tick(task, provider, t0, "wait", 0, 0, f"429 retry {attempt + 1}/{RETRY_429 - 1} in {wait}s")
                time.sleep(wait)
                continue
            raise RuntimeError(
                f"HTTP {exc.code} provider={provider}: {last_http.decode()[:400]}"
            ) from exc
    if resp is None:
        raise RuntimeError(f"HTTP 429 provider={provider}: {last_http.decode()[:400]}")
    try:
        while True:
            raw_line = resp.readline()
            if not raw_line:
                break
            line = raw_line.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
            now = time.perf_counter()
            if line.startswith(":"):
                note = line[1:].strip() or "keepalive"
                if now - last_print >= 2.0:
                    _tick(task, provider, t0, phase, reason_n, content_n, note)
                    last_print = now
                continue
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            if payload.get("error"):
                err = payload["error"]
                msg = err.get("message") if isinstance(err, dict) else str(err)
                raise RuntimeError(f"stream error provider={provider}: {msg}")
            gen_id = payload.get("id") or gen_id
            host = payload.get("provider") or host
            if payload.get("usage"):
                usage = payload["usage"]
            choice = (payload.get("choices") or [{}])[0]
            if choice.get("finish_reason"):
                finish_reason = choice.get("finish_reason")
            delta = choice.get("delta") or {}
            r_bit, c_bit = _delta_piece(delta)
            if r_bit:
                reason_buf.append(r_bit)
                reason_n += len(r_bit)
                phase = "think"
            if c_bit:
                content_buf.append(c_bit)
                content_n += len(c_bit)
                phase = "patch"
            if now - last_print >= 2.0:
                _tick(task, provider, t0, phase, reason_n, content_n)
                last_print = now
    finally:
        resp.close()
    reasoning = "".join(reason_buf)
    content = "".join(content_buf)
    text = content.strip() or reasoning.strip()
    latency_s = time.perf_counter() - t0
    _tick(task, provider, t0, "done", len(reasoning), len(content), finish_reason or "")
    LOGS.mkdir(parents=True, exist_ok=True)
    raw_path = LOGS / f"raw-{task}-{provider}-{gen_id}.json"
    raw_path.write_text(
        json.dumps(
            {
                "choice": {
                    "finish_reason": finish_reason,
                    "message": {"content": content, "reasoning": reasoning[:80_000]},
                },
                "usage": usage,
            },
            indent=2,
        )[:200_000]
    )
    meta = {
        "provider": host,
        "latency_s": round(latency_s, 3),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cost": usage.get("cost") if isinstance(usage.get("cost"), (int, float)) else None,
        "id": gen_id,
        "finish_reason": finish_reason,
        "content_chars": len(content),
        "reasoning_chars": len(reasoning),
        "raw_path": str(raw_path),
        "stream": True,
    }
    if not text:
        raise RuntimeError(f"empty content finish_reason={finish_reason}")
    return text, meta


def _pytest(tree: Path, tests: Path) -> tuple[bool, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tree)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(tests)],
        cwd=tree,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()[-800:]


def _seed_tree(task: str) -> Path:
    tmp = Path(tempfile.mkdtemp()) / "wh"
    shutil.copytree(ROOT / "warehouse", tmp)
    fault = ROOT / "tasks" / task / "fault"
    if fault.exists():
        shutil.copytree(fault, tmp, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    subprocess.run(
        ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "seed"],
        cwd=tmp,
        check=True,
    )
    return tmp


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _write_last_run(run_id: str, rows: list[dict], spend: float) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    last = [
        f"# {run_id}",
        "",
        f"model `{MODEL}`  effort `{REASONING_EFFORT}`  temp `{TEMPERATURE}`  "
        f"spend~${spend:.4f}",
        "",
        "| task | provider | pass | latency_s | prompt | completion | cost | error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        err = (r.get("error") or "").replace("|", " ")
        last.append(
            f"| {r.get('task')} | {r.get('provider')} | {r.get('pass')} | "
            f"{r.get('latency_s', '')} | {r.get('prompt_tokens', '')} | "
            f"{r.get('completion_tokens', '')} | {r.get('cost', '')} | {err} |"
        )
    (LOGS / "LAST_RUN.md").write_text("\n".join(last) + "\n")


def _record(run_meta: dict, all_rows: list[dict], spend: list[float], row: dict) -> None:
    with LOG_LOCK:
        all_rows.append(row)
        _append_jsonl(ROOT / "results.jsonl", row)
        _append_jsonl(LOGS / "runs" / f"{run_meta['run_id']}.jsonl", row)
        with SPEND_LOCK:
            spent = spend[0]
        _write_last_run(run_meta["run_id"], list(all_rows), spent)


def _run_pair(task: str, provider: str, spend: list[float], run_meta: dict, all_rows: list[dict]) -> dict:
    with SPEND_LOCK:
        over = spend[0] >= MAX_SPEND_USD
    if over:
        row = {"task": task, "provider": provider, "pass": False, "error": "spend cap", **run_meta}
        _record(run_meta, all_rows, spend, row)
        _out(f"FAIL {task:22} {provider:14} spend cap")
        return row
    row: dict = {"task": task, "provider": provider, "pass": False, **run_meta}
    tmp = None
    try:
        _out(f">> {task}  {provider}  seeding checkout")
        tmp = _seed_tree(task)
        tests = ROOT / "tasks" / task / "tests"
        held = ROOT / "tasks" / task / "tests_held"
        rendered = bundle_for(task, ROOT)
        row["prompt_sha256"] = rendered.sha256
        message = rendered.content.decode("utf-8")
        with SEM_LOCK:
            sem = PROVIDER_SEMS.setdefault(provider, threading.Semaphore(PER_PROVIDER))
        with sem:
            raw, meta = _complete(message, provider, task=task)
        host_name = meta.get("provider")
        row.update(meta)
        row["provider"] = provider
        if host_name:
            row["provider_name"] = host_name
        if meta.get("cost"):
            with SPEND_LOCK:
                spend[0] += float(meta["cost"])
        _out(f"  {task}/{provider}  applying patch ({meta.get('content_chars', 0)}c)")
        report = apply_patch(tmp, spec(task), raw.encode() if isinstance(raw, str) else raw)
        row["patch_status"] = report.status
        row["patch_sha256"] = report.response_sha256
        if report.failure is not None:
            row["error"] = str(report.failure)
            row["quality"] = report.failure.code
            _out(f"  {task}/{provider}  {report.failure.code}")
            raise RuntimeError(str(report.failure))
        row.update(classify(task, tmp))
        _out(f"  {task}/{provider}  pytest shown")
        shown_ok, shown_out = _pytest(tmp, tests)
        held_ok, held_out = True, ""
        if held.is_dir() and any(held.glob("test_*.py")):
            _out(f"  {task}/{provider}  pytest held-out")
            held_ok, held_out = _pytest(tmp, held)
        row["pass_shown"] = shown_ok
        row["pass_held"] = held_ok
        ok = shown_ok and held_ok
        row["pass"] = ok
        if not shown_ok:
            row["quality"] = "broken"
        row["pytest"] = (shown_out + "\n" + held_out).splitlines()[-12:]
        if not ok:
            blob = held_out if shown_ok and not held_ok else shown_out
            lines = [ln for ln in blob.strip().splitlines() if ln.strip()]
            fail_line = next(
                (ln for ln in reversed(lines) if "Error" in ln or "assert" in ln or ln.startswith("FAILED")),
                lines[-1] if lines else "pytest failed",
            )
            if shown_ok and not held_ok:
                fail_line = "held-out: " + fail_line
            row["error"] = fail_line[:400]
            _out(f"  {task}/{provider}  pytest fail")
            for ln in lines[-6:]:
                _out(f"    {ln}")
    except Exception as exc:
        row["error"] = str(exc)[:400]
        if str(exc).startswith("apply_fail"):
            row["quality"] = "apply_fail"
        _out(f"  {task}/{provider}  error: {row['error']}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp.parent, ignore_errors=True)
    _record(run_meta, all_rows, spend, row)
    q = row.get("quality") or ""
    _out(
        f"{'PASS' if row.get('pass') else 'FAIL':4} {task:22} {provider:14} "
        f"{q:11} {row.get('latency_s', '')}s  ${row.get('cost') or 0}  {row.get('error') or ''}"
    )
    return row


def _summary(rows: list[dict], providers: list[str], tasks: tuple[str, ...]) -> None:
    grid = {(r["task"], str(r.get("provider") or "").lower()): r for r in rows}
    header = "task".ljust(22) + "".join(f"{p:16}" for p in providers)
    _out("\n" + header)
    for task in tasks:
        line = task.ljust(22)
        for p in providers:
            r = grid.get((task, p.lower()))
            if r is None:
                cell = "?"
            elif r.get("pass"):
                cell = f"PASS/{r.get('quality') or '?'}"
            else:
                cell = "FAIL"
            line += f"{cell:16}"
        _out(line)
    for p in providers:
        subset = [r for r in rows if str(r.get("provider") or "").lower() == p.lower()]
        _out(f"{p}: {sum(1 for r in subset if r.get('pass'))}/{len(subset)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spend",
        action="store_true",
        help="Call OpenRouter. Off by default; I will not spend without this flag.",
    )
    ap.add_argument("--task", choices=ALL_TASKS, action="append")
    ap.add_argument(
        "--smoke",
        action="store_true",
        help="E2E: timestamptz_cutoff on z-ai and novita.",
    )
    ap.add_argument(
        "--golden",
        action="store_true",
        help="Five-task ladder on z-ai and novita.",
    )
    ap.add_argument(
        "--hard",
        action="store_true",
        help="All very_hard tasks on z-ai and novita.",
    )
    ap.add_argument("--providers", default=",".join(DEFAULT_PROVIDERS))
    ap.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="Parallel (task, host) workers. 0 = min(8, number of pairs).",
    )
    ap.add_argument(
        "--render-prompt",
        choices=ALL_TASKS,
        help="Print the official candidate message for one task. No network.",
    )
    ap.add_argument(
        "--check-prompts",
        action="store_true",
        help="Render all official prompts and print SHA-256 digests. No network.",
    )
    args = ap.parse_args()
    if args.check_prompts:
        for task_id, bundle in all_bundles(ROOT).items():
            print(f"{task_id} {len(bundle.content)} {bundle.sha256}")
        return 0
    if args.render_prompt:
        sys.stdout.buffer.write(bundle_for(args.render_prompt, ROOT).content)
        return 0
    if not args.spend:
        print(
            "Refusing to call OpenRouter. Pass --spend when you want to burn credits.\n"
            "Local check: python verify.py",
            file=sys.stderr,
        )
        return 2
    cheap = args.smoke or args.golden or args.hard
    if args.task:
        tasks = tuple(args.task)
    elif args.hard:
        tasks = hard_ids()
    elif args.golden:
        tasks = GOLDEN_IDS
    elif args.smoke:
        tasks = ("timestamptz_cutoff",)
    else:
        tasks = TASKS
    if cheap and args.providers == ",".join(DEFAULT_PROVIDERS):
        providers = ["z-ai", "novita"]
    else:
        providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    pairs = [(t, p) for t in tasks for p in providers]
    jobs = args.jobs if args.jobs > 0 else min(DEFAULT_JOBS, max(1, len(pairs)))
    spend = [0.0]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha, dirty = git_revision(ROOT)
    published = sha if not dirty else f"{sha}-dirty"
    run_meta = {
        "schema_version": "1",
        "run_id": run_id,
        "campaign_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning_effort": REASONING_EFFORT,
        "jobs": jobs,
        "benchmark_repo_sha": published,
        "environment_sha256": environment_digest(ROOT),
        "comparable": not dirty,
    }
    _out(
        f"run {run_id}  {len(pairs)} pairs  jobs={jobs}  "
        f"effort={REASONING_EFFORT}  temp={TEMPERATURE}"
    )
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = [
            pool.submit(_run_pair, task, provider, spend, run_meta, rows)
            for task, provider in pairs
        ]
        for fut in as_completed(futs):
            fut.result()
    n_pass = sum(1 for r in rows if r.get("pass"))
    run_path = LOGS / "runs" / f"{run_id}.jsonl"
    _summary(rows, providers, tasks)
    _out(
        f"\n{n_pass}/{len(rows)} passed  spend~${spend[0]:.4f}  "
        f"run={run_id}  appended {ROOT / 'results.jsonl'}  wrote {run_path}"
    )
    return 0 if n_pass == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
