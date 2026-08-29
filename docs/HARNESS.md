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

Official candidate messages come from `prompt_bundle.py`: incident,
entrypoint, editable paths, instructions, and faulted production
context. Tests and answers stay in the clone and never enter that
message. `python run_providers.py --check-prompts` reprints SHA-256
digests.

Candidate responses must be a bare unified diff (`diff --git` or
`--- a/` / `+++ b/`). Markdown fences fail `invalid_patch_format`.
Apply is `git apply --index --whitespace=error -p1` with no fuzz
and no hunk rewrite.

Offline regrade is `python grade.py --response <artifact.json>`.
The runner writes a `ResponseArtifact` before `grade.py` starts as a
separate process with an environment allowlist. The container uses
`--network=none`, a read-only root, bounded tmpfs, dropped
capabilities, and a non-root user. Public tests are visible inside
the container. Resource limits, not secrecy, are the security claim.

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
