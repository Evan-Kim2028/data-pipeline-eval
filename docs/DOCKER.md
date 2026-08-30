# Docker grader

`scripts/grade.py` runs candidate code in the image pinned by
`docker/grader-image.json`. Local clone checks use `verify.py` on
the host.

`tests/test_sandbox.py` needs that lock or a local `dpe-grader:dev`.
`scripts/check_release.py` and `campaigns/official-v1.json` must
match the same digest.

The recipe is `docker/grader.Dockerfile` and `docker/entrypoint.sh`.
The image is a frozen pin. Rebuilding starts a new campaign. Local
sandbox tests may set `DPE_GRADER_IMAGE` or use `dpe-grader:dev`.
