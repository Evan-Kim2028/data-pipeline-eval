# OpenRouter harness for GLM 5.3 Flash

Locked so a score change is the host or the patch, not sampling.
Model slug `z-ai/glm-5.3-flash`. Thinking cannot be disabled.

| Setting | Value | Why |
|---|---|---|
| `temperature` | `0` | Repeatable host bake-off. |
| `max_tokens` | `131072` | Model max output. |
| `reasoning.effort` | `high` | Bake-off default. |
| `provider.only` | one host | No fallback. |
| `allow_fallbacks` | `false` | Same. |
| `require_parameters` | `true` | Official campaigns. |

Official candidate messages come from `prompt_bundle.py`: a stable
system prefix plus incident, entrypoint, and production context.
Editable paths are not named. Tests stay in the clone and never
enter that message.
`python run_providers.py --check-prompts` reprints SHA-256 digests.

Prefix cache only hits when the **same host** sees the **same full
prompt** again (k≥2, back-to-back). k=1 unique (task, host) pairs
should report ~0 `cached_tokens`.

`--spend --variance` is the original 9 very_hard on z-ai and novita.
Stay at `-k 1` until that campaign is clean; then `-k 3`. Applied
diffs: `logs/runs/<run_id>/patches/`. Compare:
`python scripts/compare_trials.py logs/runs/<id>.jsonl`.
Held-out fail is `held_fail`, not `equivalent`.

Candidate responses must contain a unified diff (`diff --git` or
`--- a/` / `+++ b/`). A markdown fence around the diff is unwrapped.
Apply rewrites `@@` from unique file context, then
`git apply --index --whitespace=error -p1` with no fuzz.

Offline regrade is `python grade.py --response <artifact.json>`.
The runner writes a `ResponseArtifact` before `grade.py` starts as a
separate process with an environment allowlist. The container uses
`--network=none`, a read-only root, bounded tmpfs, dropped
capabilities, and a non-root user. Public tests are visible inside
the container. Resource limits, not secrecy, are the security claim.

Campaigns:

```sh
python run_providers.py --campaign campaigns/official-v1.json --plan
python run_providers.py --campaign campaigns/official-v1.json --preflight
python run_providers.py --campaign campaigns/official-v1.json --resume
python report.py --manifest campaigns/official-v1.json --trials results/official-v1/trials.jsonl --out reports/official-v1 --check
```

`--resume` regrades saved artifacts. `--spend` is required to call
OpenRouter. Dirty trees are marked `-dirty` and are not comparable.
Compare published rows only at the frozen `benchmark_repo_sha`,
`grader_source_sha`, and image digest.
