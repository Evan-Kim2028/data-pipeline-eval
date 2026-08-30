# Docker grader

`scripts/grade.py` runs candidate code in the image pinned by
`docker/grader-image.json`. `verify.py` does not.

`tests/test_sandbox.py` needs that lock or a local `dpe-grader:dev`.
`scripts/check_release.py` and `campaigns/official-v1.json` must
match the same digest.

Recipe: `docker/grader.Dockerfile` and `docker/entrypoint.sh`. There
is no build script. A new image is a new campaign. Local sandbox
override: `DPE_GRADER_IMAGE` or `dpe-grader:dev`.
