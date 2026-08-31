#!/usr/bin/env python3
"""Optional OpenRouter bake-off. Refuses to spend unless you pass --spend.

    python run_providers.py                     # prints this help, exit 2
    python run_providers.py --spend --smoke     # timestamptz_cutoff on z-ai, novita
    python run_providers.py --spend --golden    # 5-task ladder on z-ai, novita
    python run_providers.py --spend --hard      # very_hard tasks on z-ai, novita
    python run_providers.py --spend --variance -k 1 --providers fireworks-direct --jobs 1
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

from harness.campaign_plan import Campaign, CampaignError, expand, load_campaign
from harness.catalog import GOLDEN_IDS, all_ids, default_ids, hard_ids, spec
from harness import fireworks as fireworks_direct
from harness.contracts import SCHEMA_VERSION, ResponseArtifact, encode_json, environment_digest, git_revision
from harness.patches import apply_patch
from harness.prompt_bundle import all_bundles, bundle_for
from harness.logic_trace import attach_throughput, cot_fail_mode, hops_from_reasoning, load_hops_file
from harness.quality import classify, tag_quality
from harness.sandbox import image_lock
from harness.trial_store import SpendEvent, TrialStore

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
STALL_S = 45
TRIAL_WALL_S = 240
HOST_FAIL_STREAK = 3
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
    "fail_mode",
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


def trial_pairs(tasks: tuple[str, ...] | list[str], providers: list[str], k: int) -> list[tuple[str, str, int]]:
    return [(t, p, trial) for t in tasks for trial in range(1, k + 1) for p in providers]


def stream_abort(
    *,
    now: float,
    last_token: float,
    t0: float,
    stall_s: float = STALL_S,
    wall_s: float = TRIAL_WALL_S,
) -> str | None:
    if now - t0 >= wall_s:
        return "wall"
    if now - last_token >= stall_s:
        return "stall"
    return None


def is_infra_error(err: str) -> bool:
    low = err.lower()
    return any(
        token in low
        for token in (
            "http 429",
            "stream stall",
            "stream wall",
            "stream error",
            "host_skipped",
            "empty content",
        )
    )


def done_pair_keys(rows: list[dict]) -> set[tuple[str, str, int]]:
    out: set[tuple[str, str, int]] = set()
    for row in rows:
        task = str(row.get("task") or "")
        provider = str(row.get("provider") or "")
        trial = int(row.get("trial") or 0)
        if task and provider and trial:
            out.add((task, provider, trial))
    return out


def remaining_pairs(
    pairs: list[tuple[str, str, int]], done: set[tuple[str, str, int]]
) -> list[tuple[str, str, int]]:
    return [p for p in pairs if p not in done]


class HostBreaker:
    def __init__(self, streak: int = HOST_FAIL_STREAK) -> None:
        self.streak = streak
        self._fails: dict[str, int] = {}
        self._skip: set[str] = set()
        self._lock = threading.Lock()

    def skipped(self, provider: str) -> bool:
        with self._lock:
            return provider in self._skip

    def fail(self, provider: str) -> bool:
        with self._lock:
            n = self._fails.get(provider, 0) + 1
            self._fails[provider] = n
            if n >= self.streak:
                self._skip.add(provider)
                return True
            return False

    def ok(self, provider: str) -> None:
        with self._lock:
            self._fails[provider] = 0

    def reset(self) -> None:
        with self._lock:
            self._fails.clear()
            self._skip.clear()


HOST_BREAKER = HostBreaker()


def request_body(message: str, provider: str, *, require_parameters: bool = False) -> dict:
    provider_cfg: dict = {"only": [provider], "allow_fallbacks": False}
    if require_parameters:
        provider_cfg["require_parameters"] = True
    return {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"effort": REASONING_EFFORT},
        "stream": True,
        "stream_options": {"include_usage": True},
        "provider": provider_cfg,
        "messages": [{"role": "user", "content": message}],
    }


def _attach_fail_mode(row: dict, hops: list[dict] | None = None) -> dict:
    if hops is None:
        hops = []
        hop_path = row.get("hops_path")
        if hop_path and Path(str(hop_path)).is_file():
            hops = load_hops_file(Path(str(hop_path)))
    quality = row.get("quality")
    row["fail_mode"] = cot_fail_mode(
        passed=bool(row.get("pass")),
        quality=None if quality is None else str(quality),
        hops=hops,
    )
    return row


def _complete(message: str, provider: str, *, task: str, require_parameters: bool = False) -> tuple[str, dict]:
    if provider == fireworks_direct.PROVIDER:
        key = os.environ.get("FIREWORKS_API_KEY", "")
        if not key:
            raise SystemExit("FIREWORKS_API_KEY is not set")
        session = fireworks_direct.session_key_for_task(task)
        body = fireworks_direct.request_body(
            message,
            session_key=session,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            reasoning_effort=REASONING_EFFORT,
            stream=True,
        )
        headers = fireworks_direct.request_headers(key, session)
        headers["Accept"] = "text/event-stream"
        url = fireworks_direct.API
        served_default = fireworks_direct.PROVIDER
    else:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            raise SystemExit("OPENROUTER_API_KEY is not set")
        body = request_body(message, provider, require_parameters=require_parameters)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "HTTP-Referer": "https://github.com/Evan-Kim2028",
            "X-OpenRouter-Title": "data-pipeline-eval",
        }
        url = API
        served_default = provider
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    t0 = time.perf_counter()
    last_print = t0
    last_token = t0
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
    host = served_default
    resp_headers: dict = {}
    _tick(task, provider, t0, phase, 0, 0, "requesting")
    resp = None
    last_http = b""
    for attempt in range(RETRY_429):
        try:
            resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S)
            resp_headers = {k: v for k, v in resp.headers.items()}
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
        sock = getattr(getattr(resp, "fp", None), "raw", None)
        sock = getattr(sock, "_sock", None)
        if sock is not None:
            sock.settimeout(STALL_S + 5)
    except OSError:
        pass
    try:
        while True:
            try:
                raw_line = resp.readline()
            except (TimeoutError, OSError) as exc:
                raise RuntimeError(
                    f"stream stall provider={provider} after {time.perf_counter() - t0:.0f}s "
                    f"think={reason_n}c patch={content_n}c"
                ) from exc
            if not raw_line:
                break
            line = raw_line.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
            now = time.perf_counter()
            why = stream_abort(now=now, last_token=last_token, t0=t0)
            if why:
                raise RuntimeError(
                    f"stream {why} provider={provider} after {now - t0:.0f}s "
                    f"think={reason_n}c patch={content_n}c"
                )
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
            if not delta and isinstance(choice.get("message"), dict):
                delta = choice["message"]
            r_bit, c_bit = _delta_piece(delta)
            if r_bit:
                reason_buf.append(r_bit)
                reason_n += len(r_bit)
                last_token = now
                if t_think is None:
                    t_think = now
                phase = "think"
            if c_bit:
                content_buf.append(c_bit)
                content_n += len(c_bit)
                last_token = now
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
    if provider == fireworks_direct.PROVIDER:
        fields = fireworks_direct.usage_from_fireworks(usage, resp_headers)
        fields["cost"] = fireworks_direct.estimate_cost(
            prompt_tokens=fields.get("prompt_tokens"),
            cached_tokens=fields.get("cached_tokens"),
            completion_tokens=fields.get("completion_tokens"),
        )
        fields["cost_prompt"] = None
        fields["cost_completion"] = None
        model_name = fireworks_direct.MODEL
    else:
        fields = usage_from_openrouter(usage)
        model_name = MODEL
    meta = {
        "provider": host,
        "model": model_name,
        "latency_s": round(latency_s, 3),
        **fields,
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
        _attach_fail_mode(row, [])
        _record(run_meta, all_rows, spend, row)
        _out(f"FAIL {task:22} {provider:14} t{trial} spend cap")
        return row
    row = _base_row(task, provider, trial, run_meta)
    tmp = None
    hops: list[dict] = []
    if HOST_BREAKER.skipped(provider):
        row["error"] = f"host_skipped provider={provider}"
        _attach_fail_mode(row, [])
        _record(run_meta, all_rows, spend, row)
        _out(f"FAIL {task:22} {provider:14} t{trial} host_skipped")
        return row
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
        if is_infra_error(row["error"]):
            if HOST_BREAKER.fail(provider):
                _out(
                    f"SKIP {provider}: {HOST_FAIL_STREAK} infra failures in a row "
                    f"(429/stall/stream). Remaining {provider} pairs will not call OpenRouter."
                )
        else:
            HOST_BREAKER.ok(provider)
    else:
        HOST_BREAKER.ok(provider)
    finally:
        if tmp is not None:
            shutil.rmtree(tmp.parent, ignore_errors=True)
    _attach_fail_mode(row, hops)
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
        [sys.executable, str(ROOT / "scripts" / "grade.py"), "--response", str(artifact_path)],
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
        help="Call a model host. Off by default; I will not spend without this flag.",
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
    ap.add_argument(
        "--providers",
        default=",".join(DEFAULT_PROVIDERS),
        help="Comma-separated hosts. fireworks-direct calls api.fireworks.ai (needs FIREWORKS_API_KEY).",
    )
    ap.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="Parallel (task, host) workers. 0 = min(8, number of pairs).",
    )
    ap.add_argument(
        "--continue-run",
        metavar="RUN",
        help="Resume an incomplete bake-off jsonl (run id or path). Skip pairs already written.",
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
    needs_openrouter = any(p != fireworks_direct.PROVIDER for p in providers)
    needs_fireworks = any(p == fireworks_direct.PROVIDER for p in providers)
    if needs_openrouter and not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY is not set", file=sys.stderr)
        return 2
    if needs_fireworks and not os.environ.get("FIREWORKS_API_KEY"):
        print("FIREWORKS_API_KEY is not set", file=sys.stderr)
        return 2
    pairs = trial_pairs(tasks, providers, args.k)
    spend = [0.0]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows: list[dict] = []
    HOST_BREAKER.reset()
    if args.continue_run:
        cont = Path(args.continue_run)
        if not cont.suffix:
            cont = LOGS / "runs" / f"{args.continue_run}.jsonl"
        if not cont.is_file():
            print(f"--continue-run not found: {cont}", file=sys.stderr)
            return 2
        prior = [json.loads(line) for line in cont.read_text().splitlines() if line.strip()]
        done = done_pair_keys(prior)
        skipped = len(pairs)
        pairs = remaining_pairs(pairs, done)
        skipped -= len(pairs)
        rows = prior
        spend[0] = sum(float(r.get("cost") or 0) for r in prior)
        if prior:
            run_id = str(prior[0].get("run_id") or run_id)
        _out(f"continue {cont.name}  skip {skipped} written  {len(pairs)} left  spend~${spend[0]:.4f}")
    jobs = args.jobs if args.jobs > 0 else min(DEFAULT_JOBS, max(1, len(pairs) or 1))
    sha, dirty = git_revision(ROOT)
    published = sha if not dirty else f"{sha}-dirty"
    run_meta = {
        "schema_version": "1",
        "run_id": run_id,
        "campaign_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": fireworks_direct.MODEL
        if providers == [fireworks_direct.PROVIDER]
        else MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning_effort": REASONING_EFFORT,
        "jobs": jobs,
        "k": args.k,
        "benchmark_repo_sha": published,
        "environment_sha256": environment_digest(ROOT),
        "comparable": not dirty,
    }
    if args.continue_run and rows:
        first = rows[0]
        for key in (
            "benchmark_repo_sha",
            "environment_sha256",
            "comparable",
            "model",
            "temperature",
            "reasoning_effort",
            "k",
        ):
            if key in first and first[key] is not None:
                run_meta[key] = first[key]
    _out(
        f"run {run_id}  {len(pairs)} pairs  jobs={jobs}  k={args.k}  "
        f"effort={REASONING_EFFORT}  temp={TEMPERATURE}"
    )
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
