# Docker grader

Docker is the official isolated grader. It is not the local clone check.

## When it is required

Required:

- `python grade.py --response <saved-response.json>` — host `grade.py` and `sandbox.py` (`image_lock`, `run_container`) run candidate code in the pinned image.
- Official campaign grading and resume-regrade, which invoke `grade.py`.
- `tests/test_sandbox.py`, which needs the locked image or a local `dpe-grader:dev`.

Not required:

- `python verify.py` — host pytest over faulted and gold checkouts. No Docker, no spend. This is the clean-clone check.

## How the pin works

`docker/grader-image.json` is the lock. `sandbox.image_lock()` reads it. `grade.py` grades only against that digest (`image` / `digest`, plus `grader_source_sha` and `environment_sha256`). `scripts/check_release.py` and `campaigns/official-v1.json` must match the same digest.

The image recipe is `docker/grader.Dockerfile` and `docker/entrypoint.sh`. There is no build or publish script in `scripts/`. The pin is frozen. Rebuilding or retagging is a new campaign, not a clone step.

Override for local sandbox tests only: `DPE_GRADER_IMAGE` or `dpe-grader:dev`. Comparable official rows still use the lock digest.
