#!/usr/bin/env python3
"""Optional OpenRouter bake-off. Refuses to spend unless you pass --spend.

    python run_providers.py              # prints this help, exit 2
    python run_providers.py --spend      # you opted in
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from catalog import all_ids, default_ids

ROOT = Path(__file__).resolve().parent
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


def _extract_python_or_diff(text: str) -> str:
    blocks = re.findall(r"```(?:diff|patch|python)?\n(.*?)```", text, re.DOTALL)
    if blocks:
        return blocks[0]
    return text


def _apply_model_output(work: Path, raw: str) -> None:
    """Apply a unified diff in work/, or overwrite a single hinted file."""
    blob = _extract_python_or_diff(raw)
    if blob.lstrip().startswith(("diff ", "--- ", "+++ ")):
        proc = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-p0"],
            cwd=work,
            input=blob.encode(),
            capture_output=True,
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", "-p1"],
                cwd=work,
                input=blob.encode(),
                capture_output=True,
            )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode()[-400:])
        return
    raise RuntimeError("model output was not a unified diff")


def _file_tree(root: Path) -> str:
    return "\n".join(
        sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    )


def _complete(prompt: str, bundle: str, provider: str) -> tuple[str, dict]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    body = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 2500,
        "provider": {"only": [provider], "allow_fallbacks": False},
        "messages": [
            {
                "role": "user",
                "content": prompt + "\n\nCheckout files:\n\n" + bundle,
            }
        ],
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Evan-Kim2028",
            "X-OpenRouter-Title": "analytics-incidents-eval",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} provider={provider}: {exc.read().decode()[:400]}") from exc
    latency_s = time.perf_counter() - t0
    usage = payload.get("usage") or {}
    meta = {
        "provider": payload.get("provider") or provider,
        "latency_s": round(latency_s, 3),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cost": usage.get("cost") if isinstance(usage.get("cost"), (int, float)) else None,
        "id": payload.get("id"),
    }
    return payload["choices"][0]["message"]["content"], meta


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


def run_task(task: str, providers: list[str], spend: list[float]) -> list[dict]:
    task_dir = ROOT / "tasks" / task
    prompt = (task_dir / "prompt.txt").read_text()
    tests = task_dir / "tests"
    rows = []
    for provider in providers:
        if spend[0] >= MAX_SPEND_USD:
            rows.append({"task": task, "provider": provider, "pass": False, "error": "spend cap"})
            continue
        row: dict = {"task": task, "provider": provider, "pass": False}
        tmp = _seed_tree(task)
        tree = _file_tree(tmp)
        bundle = tree + "\n\nHidden tests (do not edit):\n"
        for p in sorted(tests.glob("test_*.py")):
            bundle += f"\n## tests/{p.name}\n```python\n{p.read_text()}```\n"
        try:
            raw, meta = _complete(prompt, bundle, provider)
            row.update(meta)
            if meta.get("cost"):
                spend[0] += float(meta["cost"])
            _apply_model_output(tmp, raw)
            ok, pytest_out = _pytest(tmp, tests)
            row["pass"] = ok
            row["pytest"] = pytest_out.splitlines()[-8:]
        except Exception as exc:
            row["error"] = str(exc)[:400]
        rows.append(row)
        print(f"{'PASS' if row.get('pass') else 'FAIL':4} {task:22} {provider:14} {row.get('error') or ''}", flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spend",
        action="store_true",
        help="Call OpenRouter. Off by default; I will not spend without this flag.",
    )
    ap.add_argument("--task", choices=ALL_TASKS, action="append")
    ap.add_argument("--providers", default=",".join(DEFAULT_PROVIDERS))
    args = ap.parse_args()
    if not args.spend:
        print(
            "Refusing to call OpenRouter. Pass --spend when you want to burn credits.\n"
            "Local check: python verify.py",
            file=sys.stderr,
        )
        return 2
    tasks = tuple(args.task) if args.task else TASKS
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    spend = [0.0]
    rows: list[dict] = []
    for task in tasks:
        rows.extend(run_task(task, providers, spend))
    out = ROOT / "results.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"\n{sum(1 for r in rows if r.get('pass'))}/{len(rows)} passed  spend~${spend[0]:.4f}  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
