#!/usr/bin/env python3
"""Optional OpenRouter bake-off. Refuses to spend unless you pass --spend.

    python run_providers.py                     # prints this help, exit 2
    python run_providers.py --spend --smoke     # timestamptz_cutoff on z-ai, novita
    python run_providers.py --spend --golden    # 5-task ladder on z-ai, novita
    python run_providers.py --spend --hard      # very_hard tasks on z-ai, novita
"""

from __future__ import annotations

import argparse
import hashlib
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

from dataclasses import asdict

from campaign_plan import Campaign, CampaignError, expand, load_campaign
from catalog import GOLDEN_IDS, all_ids, default_ids, hard_ids, spec
from contracts import SCHEMA_VERSION, ResponseArtifact, encode_json, environment_digest, git_revision
from patches import apply_patch
from prompt_bundle import all_bundles, bundle_for
from logic_trace import attach_throughput, hops_from_reasoning
from quality import classify, tag_quality
from sandbox import image_lock
from trial_store import SpendEvent, TrialStore

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
_GRADE_ENV = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TZ",
    "USER",
    "LOGNAME",
    "TMPDIR",
    "TMP",
    "TEMP",
    "PYTHONPATH",
)


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
    reason = ""
    details = delta.get("reasoning_details")
    if isinstance(details, list):
        bits: list[str] = []
        for item in details:
            if isinstance(item, dict):
                bit = item.get("text") or item.get("content") or ""
                if bit:
                    bits.append(str(bit))
        if bits:
            reason = "".join(bits)
    if not reason:
        for key in ("reasoning", "reasoning_content"):
            val = delta.get(key)
            if isinstance(val, str) and val:
                reason = val
                break
    content = delta.get("content")
    if not isinstance(content, str):
        content = ""
    return reason, content


TRIAL_ROW_KEYS = (
    "schema_version",
    "run_id",
    "campaign_id",
    "trial_id",
    "trial",
    "k",
    "task",
    "provider",
    "provider_name",
    "model",
    "temperature",
    "max_tokens",
    "reasoning_effort",
    "prompt_sha256",
    "benchmark_repo_sha",
    "environment_sha256",
    "comparable",
    "jobs",
    "ts",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "cost",
    "cost_prompt",
    "cost_completion",
    "latency_s",
    "finish_reason",
    "id",
    "content_chars",
    "reasoning_chars",
    "raw_path",
    "stream",
    "tool_calls",
    "patch_status",
    "patch_sha256",
    "applied_diff_path",
    "applied_sha256",
    "quality",
    "changed",
    "extra",
    "fault_files",
    "files_changed_n",
    "lines_added",
    "lines_deleted",
    "pass",
    "pass_shown",
    "pass_held",
    "pytest",
    "error",
    "think_s",
    "patch_s",
    "hop_count",
    "hops_path",
    "tps_out",
    "tps_total",
    "tps_reason",
    "tps_think",
)


def usage_from_openrouter(usage: dict | None) -> dict:
    usage = usage or {}
    pdet = usage.get("prompt_tokens_details")
    cdet = usage.get("completion_tokens_details")
    cost_det = usage.get("cost_details")
    pdet = pdet if isinstance(pdet, dict) else {}
    cdet = cdet if isinstance(cdet, dict) else {}
    cost_det = cost_det if isinstance(cost_det, dict) else {}
    cost = usage.get("cost")
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cached_tokens": pdet.get("cached_tokens"),
        "cache_write_tokens": pdet.get("cache_write_tokens"),
        "reasoning_tokens": cdet.get("reasoning_tokens"),
        "cost": cost if isinstance(cost, (int, float)) else None,
        "cost_prompt": cost_det.get("upstream_inference_prompt_cost"),
        "cost_completion": cost_det.get("upstream_inference_completions_cost"),
    }


def _trial_id(run_id: str, task: str, trial: int, provider: str) -> str:
    return f"{run_id}:{task}:r{trial}:{provider}"


def _base_row(task: str, provider: str, trial: int, run_meta: dict) -> dict:
    row = {key: None for key in TRIAL_ROW_KEYS}
    row.update(
        {
            "schema_version": run_meta.get("schema_version"),
            "run_id": run_meta.get("run_id"),
            "campaign_id": run_meta.get("campaign_id"),
            "trial_id": _trial_id(str(run_meta.get("run_id") or ""), task, trial, provider),
            "trial": trial,
            "k": run_meta.get("k"),
            "task": task,
            "provider": provider,
            "model": run_meta.get("model"),
            "temperature": run_meta.get("temperature"),
            "max_tokens": run_meta.get("max_tokens"),
            "reasoning_effort": run_meta.get("reasoning_effort"),
            "benchmark_repo_sha": run_meta.get("benchmark_repo_sha"),
            "environment_sha256": run_meta.get("environment_sha256"),
            "comparable": run_meta.get("comparable"),
            "jobs": run_meta.get("jobs"),
            "ts": run_meta.get("ts"),
            "pass": False,
            "tool_calls": 0,
            "changed": [],
            "extra": [],
            "fault_files": [],
            "pytest": [],
        }
    )
    return row


def _freeze_row(row: dict) -> dict:
    frozen = {key: row.get(key) for key in TRIAL_ROW_KEYS}
    extra = {key: value for key, value in row.items() if key not in frozen}
    frozen.update(extra)
    return frozen


def _diff_stats(blob: bytes) -> tuple[int, int, int]:
    files = plus = minus = 0
    for line in blob.decode("utf-8", "replace").splitlines():
        if line.startswith("diff --git "):
            files += 1
        elif line.startswith(("+++", "---")):
            continue
        elif line.startswith("+"):
            plus += 1
        elif line.startswith("-"):
            minus += 1
    return files, plus, minus


def _save_applied_diff(run_id: str, task: str, provider: str, trial: int, work: Path) -> tuple[str, str, bytes]:
    blob = subprocess.check_output(["git", "diff", "--cached"], cwd=work)
    directory = LOGS / "runs" / run_id / "patches"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{task}__{provider}__t{trial}.diff"
    path.write_bytes(blob)
    return str(path), hashlib.sha256(blob).hexdigest(), blob


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


def _complete(message: str, provider: str, *, task: str, require_parameters: bool = False) -> tuple[str, dict]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    provider_cfg: dict = {"only": [provider], "allow_fallbacks": False}
    if require_parameters:
        provider_cfg["require_parameters"] = True
    body = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"effort": REASONING_EFFORT},
        "stream": True,
        "stream_options": {"include_usage": True},
        "provider": provider_cfg,
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
    t_think = None
    t_patch = None
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
                if t_think is None:
                    t_think = now
                phase = "think"
            if c_bit:
                content_buf.append(c_bit)
                content_n += len(c_bit)
                if t_patch is None:
                    t_patch = now
                phase = "patch"
            if now - last_print >= 2.0:
                _tick(task, provider, t0, phase, reason_n, content_n)
                last_print = now
    finally:
        resp.close()
    reasoning = "".join(reason_buf)
    content = "".join(content_buf)
    text = content.strip() or reasoning.strip()
    ended = time.perf_counter()
    latency_s = ended - t0
    think_s = None
    patch_s = None
    if t_think is not None:
        think_s = round((t_patch if t_patch is not None else ended) - t_think, 3)
    if t_patch is not None:
        patch_s = round(ended - t_patch, 3)
    _tick(task, provider, t0, "done", len(reasoning), len(content), finish_reason or "")
    LOGS.mkdir(parents=True, exist_ok=True)
    raw_path = LOGS / f"raw-{task}-{provider}-{gen_id}.json"
    dumped = json.dumps(
        {
            "usage": usage,
            "choice": {
                "finish_reason": finish_reason,
                "message": {"content": content, "reasoning": reasoning[:80_000]},
            },
        },
        indent=2,
    )
    raw_path.write_text(dumped[:200_000])
    meta = {
        "provider": host,
        "latency_s": round(latency_s, 3),
        **usage_from_openrouter(usage),
        "id": gen_id,
        "finish_reason": finish_reason,
        "content_chars": len(content),
        "reasoning_chars": len(reasoning),
        "raw_path": str(raw_path),
        "stream": True,
        "tool_calls": 0,
        "think_s": think_s,
        "patch_s": patch_s,
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


def _sort_rows(rows: list[dict], tasks: tuple[str, ...]) -> list[dict]:
    order = {task: i for i, task in enumerate(tasks)}
    return sorted(
        rows,
        key=lambda r: (
            order.get(str(r.get("task") or ""), 999),
            str(r.get("provider") or ""),
            int(r.get("trial") or 1),
        ),
    )


def _write_last_run(run_meta: dict, rows: list[dict], spend: float) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    run_id = str(run_meta.get("run_id") or "")
    last = [
        f"# {run_id}",
        "",
        f"model `{run_meta.get('model')}`  effort `{run_meta.get('reasoning_effort')}`  "
        f"temp `{run_meta.get('temperature')}`  k `{run_meta.get('k')}`  "
        f"comparable `{run_meta.get('comparable')}`  sha `{run_meta.get('benchmark_repo_sha')}`  "
        f"spend~${spend:.4f}",
        "",
        "| task | provider | trial | pass | quality | shown | held | latency_s | prompt | completion | reason_tok | hops | tps_out | cached | cost | files | +ln | -ln | error |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        err = (r.get("error") or "").replace("|", " ")
        last.append(
            f"| {r.get('task')} | {r.get('provider')} | {r.get('trial')} | "
            f"{r.get('pass')} | {r.get('quality') or ''} | {r.get('pass_shown')} | "
            f"{r.get('pass_held')} | {r.get('latency_s', '')} | {r.get('prompt_tokens', '')} | "
            f"{r.get('completion_tokens', '')} | {r.get('reasoning_tokens', '')} | "
            f"{r.get('hop_count', '')} | {r.get('tps_out', '')} | "
            f"{r.get('cached_tokens', '')} | {r.get('cost', '')} | "
            f"{r.get('files_changed_n', '')} | {r.get('lines_added', '')} | "
            f"{r.get('lines_deleted', '')} | {err} |"
        )
    text = "\n".join(last) + "\n"
    (LOGS / "LAST_RUN.md").write_text(text)
    archive = LOGS / "runs" / run_id
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "LAST_RUN.md").write_text(text)


def _record(run_meta: dict, all_rows: list[dict], spend: list[float], row: dict) -> None:
    frozen = _freeze_row(row)
    with LOG_LOCK:
        all_rows.append(frozen)
        _append_jsonl(ROOT / "results.jsonl", frozen)
        _append_jsonl(LOGS / "runs" / f"{run_meta['run_id']}.jsonl", frozen)
        with SPEND_LOCK:
            spent = spend[0]
        _write_last_run(run_meta, list(all_rows), spent)


def _run_pair(
    task: str, provider: str, trial: int, spend: list[float], run_meta: dict, all_rows: list[dict]
) -> dict:
    with SPEND_LOCK:
        over = spend[0] >= MAX_SPEND_USD
    if over:
        row = _base_row(task, provider, trial, run_meta)
        row["error"] = "spend cap"
        _record(run_meta, all_rows, spend, row)
        _out(f"FAIL {task:22} {provider:14} t{trial} spend cap")
        return row
    row = _base_row(task, provider, trial, run_meta)
    tmp = None
    try:
        _out(f">> {task}  {provider}  t{trial}  seeding checkout")
        tmp = _seed_tree(task)
        tests = ROOT / "tasks" / task / "tests"
        held = ROOT / "tasks" / task / "tests_adjudication"
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
        hops: list[dict] = []
        raw_file = Path(str(meta.get("raw_path") or ""))
        if raw_file.is_file():
            payload = json.loads(raw_file.read_text())
            hops = hops_from_reasoning(
                ((payload.get("choice") or {}).get("message") or {}).get("reasoning") or ""
            )
        row["hop_count"] = len(hops)
        hop_dir = LOGS / "runs" / str(run_meta["run_id"]) / "hops"
        hop_dir.mkdir(parents=True, exist_ok=True)
        hop_path = hop_dir / f"{task}__{provider}__t{trial}.json"
        hop_path.write_text(json.dumps({"hops": hops}, indent=2)[:200_000])
        row["hops_path"] = str(hop_path)
        attach_throughput(row)
        _out(f"  {task}/{provider}  t{trial}  applying patch ({meta.get('content_chars', 0)}c)")
        report = apply_patch(tmp, spec(task), raw.encode() if isinstance(raw, str) else raw)
        row["patch_status"] = report.status
        row["patch_sha256"] = report.response_sha256
        if report.failure is not None:
            row["error"] = str(report.failure)
            row["quality"] = report.failure.code
            _out(f"  {task}/{provider}  t{trial}  {report.failure.code}")
            raise RuntimeError(str(report.failure))
        changed = set(report.changed_paths)
        row.update(classify(task, tmp, changed=changed))
        diff_path, diff_sha, diff_blob = _save_applied_diff(
            str(run_meta["run_id"]), task, provider, trial, tmp
        )
        row["applied_diff_path"] = diff_path
        row["applied_sha256"] = diff_sha
        files_n, plus, minus = _diff_stats(diff_blob)
        row["files_changed_n"] = files_n
        row["lines_added"] = plus
        row["lines_deleted"] = minus
        _out(f"  {task}/{provider}  t{trial}  pytest shown")
        shown_ok, shown_out = _pytest(tmp, tests)
        held_ok, held_out = True, ""
        if held.is_dir() and any(held.glob("test_*.py")):
            _out(f"  {task}/{provider}  t{trial}  pytest held-out")
            held_ok, held_out = _pytest(tmp, held)
        row["pass_shown"] = shown_ok
        row["pass_held"] = held_ok
        ok = shown_ok and held_ok
        row["pass"] = ok
        row["quality"] = tag_quality(str(row.get("quality") or "other"), shown_ok, held_ok)
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
            _out(f"  {task}/{provider}  t{trial}  pytest fail")
            for ln in lines[-6:]:
                _out(f"    {ln}")
    except Exception as exc:
        row["error"] = str(exc)[:400]
        _out(f"  {task}/{provider}  t{trial}  error: {row['error']}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp.parent, ignore_errors=True)
    _record(run_meta, all_rows, spend, row)
    q = row.get("quality") or ""
    _out(
        f"{'PASS' if row.get('pass') else 'FAIL':4} {task:22} {provider:14} t{trial} "
        f"{q:11} {row.get('latency_s', '')}s  ${row.get('cost') or 0}  {row.get('error') or ''}"
    )
    return row


def _summary(rows: list[dict], providers: list[str], tasks: tuple[str, ...]) -> None:
    grid = {
        (r["task"], str(r.get("provider") or "").lower(), int(r.get("trial") or 1)): r
        for r in rows
    }
    trials = sorted({int(r.get("trial") or 1) for r in rows}) or [1]
    header = "task".ljust(22) + "".join(f"{p:16}" for p in providers)
    _out("\n" + header)
    for task in tasks:
        for trial in trials:
            label = task if len(trials) == 1 else f"{task}:t{trial}"
            line = label.ljust(22)
            for p in providers:
                r = grid.get((task, p.lower(), trial))
                if r is None:
                    cell = "?"
                else:
                    mark = "PASS" if r.get("pass") else "FAIL"
                    cell = f"{mark}/{r.get('quality') or '?'}"
                line += f"{cell:16}"
            _out(line)
    for p in providers:
        subset = [r for r in rows if str(r.get("provider") or "").lower() == p.lower()]
        _out(f"{p}: {sum(1 for r in subset if r.get('pass'))}/{len(subset)}")


def grade_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in _GRADE_ENV if key in os.environ}
    for banned in ("OPENROUTER_API_KEY", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env.pop(banned, None)
    return env


def invoke_grade(artifact_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "grade.py"), "--response", str(artifact_path)],
        cwd=ROOT,
        env=grade_env(),
        capture_output=True,
        text=True,
    )


def write_response_artifact(results: Path, artifact: ResponseArtifact) -> Path:
    path = results / "responses" / f"{artifact.candidate_sha256}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(encode_json(artifact) + "\n")
    os.replace(tmp, path)
    return path


def print_campaign_plan(path: Path) -> int:
    campaign = load_campaign(path)
    for row in expand(campaign):
        print(json.dumps(asdict(row), separators=(",", ":"), sort_keys=True))
    return 0


def local_preflight(campaign: Campaign) -> list[dict]:
    lock = image_lock()
    env = environment_digest(ROOT)
    rows: list[dict] = []
    hashes = dict(campaign.manifest.prompt_hashes)
    for task_id in campaign.manifest.task_ids:
        rendered = bundle_for(task_id, ROOT)
        ok = rendered.sha256 == hashes[task_id]
        rows.append(
            {
                "kind": "prompt",
                "task_id": task_id,
                "ok": ok,
                "prompt_hash": rendered.sha256,
            }
        )
        if not ok:
            raise CampaignError(f"prompt hash mismatch for {task_id}")
    if campaign.grader_image_digest != lock["digest"]:
        raise CampaignError("grader_image_digest does not match docker/grader-image.json")
    if campaign.manifest.environment_sha256 != env:
        raise CampaignError("environment_sha256 does not match pinned environment")
    for provider in campaign.manifest.requested_providers:
        rows.append(
            {
                "kind": "provider",
                "requested_provider": provider,
                "require_parameters": True,
                "ok": True,
            }
        )
    rows.append(
        {
            "kind": "pins",
            "grader_image_digest": lock["digest"],
            "environment_sha256": env,
            "ok": True,
        }
    )
    return rows


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resume_regrade(campaign: Campaign, results: Path) -> int:
    store = TrialStore(results)
    specs = expand(campaign)
    store.plan(specs)
    pending = store.pending(specs)
    for row in pending:
        state = store.state_of(row.trial_id)
        if state not in {"response_saved", "graded"}:
            print(
                f"resume needs --spend for {row.trial_id} (state={state})",
                file=sys.stderr,
            )
            return 2
        matches = (
            list((results / "responses").glob("*.json"))
            if (results / "responses").is_dir()
            else []
        )
        chosen = None
        for path in matches:
            data = json.loads(path.read_text())
            if data.get("trial_id") == row.trial_id:
                chosen = path
                break
        if chosen is None:
            print(f"missing response artifact for {row.trial_id}", file=sys.stderr)
            return 2
        if state == "response_saved":
            proc = invoke_grade(chosen)
            store.append_trial(row, "graded")
            store.append_trial(row, "terminal")
            _out(f"{row.trial_id} regraded exit={proc.returncode}")
        elif state == "graded":
            store.append_trial(row, "terminal")
    return 0


def run_campaign(campaign: Campaign, results: Path) -> int:
    store = TrialStore(results)
    specs = expand(campaign)
    store.plan(specs)
    n = max(len(specs), 1)
    reserve_amt = min(0.25, campaign.spend_cap / n) if campaign.spend_cap else 0.0
    sha, dirty = git_revision(ROOT)
    published = sha if not dirty else f"{sha}-dirty"
    lock = image_lock()
    env = environment_digest(ROOT)
    pending = store.pending(specs)
    for row in pending:
        totals = store.spend_totals()
        if totals["exposure"] + reserve_amt > campaign.spend_cap + 1e-9:
            store.append_trial(row, "terminal")
            continue
        store.append_trial(row, "reserved")
        store.append_spend(
            SpendEvent(
                event_id=f"{row.trial_id}:reserve",
                trial_id=row.trial_id,
                kind="reserve",
                amount=reserve_amt,
                currency="USD",
                provider_generation_id=None,
                timestamp=_now(),
                manifest_hash=row.manifest_hash,
            )
        )
        store.append_trial(row, "dispatched")
        rendered = bundle_for(row.task_id, ROOT)
        try:
            text, meta = _complete(
                rendered.content.decode("utf-8"),
                row.requested_provider,
                task=row.task_id,
                require_parameters=True,
            )
        except Exception as exc:
            store.append_spend(
                SpendEvent(
                    event_id=f"{row.trial_id}:unknown",
                    trial_id=row.trial_id,
                    kind="unknown",
                    amount=reserve_amt,
                    currency="USD",
                    provider_generation_id=None,
                    timestamp=_now(),
                    manifest_hash=row.manifest_hash,
                )
            )
            store.append_trial(row, "terminal")
            _out(f"FAIL {row.trial_id} {exc}")
            continue
        served = str(meta.get("provider") or row.requested_provider)
        cost = meta.get("cost")
        settled = float(cost) if isinstance(cost, (int, float)) else 0.0
        digest = hashlib.sha256(text.encode()).hexdigest()
        artifact = ResponseArtifact(
            schema_version=SCHEMA_VERSION,
            trial_id=row.trial_id,
            task_id=row.task_id,
            candidate_text=text,
            candidate_sha256=digest,
            prompt_sha256=row.prompt_hash,
            model=campaign.manifest.model,
            requested_provider=row.requested_provider,
            served_provider=served,
            generation_id=None if meta.get("id") == "unknown" else str(meta.get("id")),
            usage=usage_from_openrouter(
                {
                    "prompt_tokens": meta.get("prompt_tokens"),
                    "completion_tokens": meta.get("completion_tokens"),
                    "total_tokens": meta.get("total_tokens"),
                    "prompt_tokens_details": {
                        "cached_tokens": meta.get("cached_tokens"),
                        "cache_write_tokens": meta.get("cache_write_tokens"),
                    },
                    "completion_tokens_details": {
                        "reasoning_tokens": meta.get("reasoning_tokens"),
                    },
                    "cost": cost if isinstance(cost, (int, float)) else None,
                    "cost_details": {
                        "upstream_inference_prompt_cost": meta.get("cost_prompt"),
                        "upstream_inference_completions_cost": meta.get("cost_completion"),
                    },
                }
            ),
            finish_reason=meta.get("finish_reason"),
            benchmark_repo_sha=published,
            grader_source_sha=campaign.grader_source_sha,
            grader_image_digest=lock["digest"],
            environment_sha256=env,
        )
        write_response_artifact(results, artifact)
        store.append_trial(row, "response_saved")
        store.append_spend(
            SpendEvent(
                event_id=f"{row.trial_id}:settle",
                trial_id=row.trial_id,
                kind="settle",
                amount=settled,
                currency="USD",
                provider_generation_id=artifact.generation_id,
                timestamp=_now(),
                manifest_hash=row.manifest_hash,
            )
        )
        proc = invoke_grade(results / "responses" / f"{digest}.json")
        store.append_trial(row, "graded")
        store.append_trial(row, "terminal")
        _out(f"{row.trial_id} served={served} grade={proc.returncode}")
    return 0


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
    ap.add_argument(
        "--variance",
        action="store_true",
        help="Original 9 very_hard tasks on z-ai and novita.",
    )
    ap.add_argument(
        "-k",
        type=int,
        default=1,
        metavar="N",
        help="Replicates per (task, host). Default 1.",
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
    ap.add_argument("--campaign", type=Path, help="Frozen campaign manifest JSON.")
    ap.add_argument(
        "--plan",
        action="store_true",
        help="Print the expanded trial plan for --campaign. No network.",
    )
    ap.add_argument(
        "--preflight",
        action="store_true",
        help="Validate campaign pins and prompt hashes. No provider spend.",
    )
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Finish pending campaign trials. Regrade saved artifacts without --spend.",
    )
    ap.add_argument(
        "--results",
        type=Path,
        help="Campaign result directory. Default: results/<campaign_id>.",
    )
    args = ap.parse_args()
    if args.check_prompts:
        for task_id, bundle in all_bundles(ROOT).items():
            print(f"{task_id} {len(bundle.content)} {bundle.sha256}")
        return 0
    if args.render_prompt:
        sys.stdout.buffer.write(bundle_for(args.render_prompt, ROOT).content)
        return 0
    if args.campaign:
        if args.plan:
            return print_campaign_plan(args.campaign)
        campaign = load_campaign(args.campaign)
        results = args.results or (ROOT / "results" / campaign.manifest.campaign_id)
        if args.preflight:
            rows = local_preflight(campaign)
            results.mkdir(parents=True, exist_ok=True)
            with (results / "preflight.jsonl").open("w") as fh:
                for row in rows:
                    line = json.dumps(row, separators=(",", ":"), sort_keys=True)
                    print(line)
                    fh.write(line + "\n")
            return 0
        if args.resume and not args.spend:
            return resume_regrade(campaign, results)
        if not args.spend:
            print(
                "Refusing to call OpenRouter. Pass --spend when you want to burn credits.\n"
                "Offline: --plan, --preflight, or --resume with saved artifacts.",
                file=sys.stderr,
            )
            return 2
        return run_campaign(campaign, results)
    if not args.spend:
        print(
            "Refusing to call OpenRouter. Pass --spend when you want to burn credits.\n"
            "Local check: python verify.py",
            file=sys.stderr,
        )
        return 2
    cheap = args.smoke or args.golden or args.hard or args.variance
    if args.k < 1:
        print("-k must be >= 1", file=sys.stderr)
        return 2
    if args.task:
        tasks = tuple(args.task)
    elif args.hard or args.variance:
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
    pairs = [(t, p, trial) for t in tasks for p in providers for trial in range(1, args.k + 1)]
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
        "k": args.k,
        "benchmark_repo_sha": published,
        "environment_sha256": environment_digest(ROOT),
        "comparable": not dirty,
    }
    _out(
        f"run {run_id}  {len(pairs)} pairs  jobs={jobs}  k={args.k}  "
        f"effort={REASONING_EFFORT}  temp={TEMPERATURE}"
    )
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = [
            pool.submit(_run_pair, task, provider, trial, spend, run_meta, rows)
            for task, provider, trial in pairs
        ]
        for fut in as_completed(futs):
            fut.result()
    rows[:] = _sort_rows(rows, tasks)
    run_path = LOGS / "runs" / f"{run_id}.jsonl"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    _write_last_run(run_meta, rows, spend[0])
    n_pass = sum(1 for r in rows if r.get("pass"))
    _summary(rows, providers, tasks)
    _out(
        f"\n{n_pass}/{len(rows)} passed  spend~${spend[0]:.4f}  "
        f"run={run_id}  appended {ROOT / 'results.jsonl'}  wrote {run_path}"
    )
    return 0 if n_pass == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
