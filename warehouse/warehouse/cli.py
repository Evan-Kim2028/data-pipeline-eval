from __future__ import annotations

import sys

from warehouse.ops.timers import job_names
from warehouse.serve.health import ok


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["health"]:
        print(ok())
        return 0
    if argv == ["jobs"]:
        print("\n".join(job_names()))
        return 0
    print("usage: warehouse health|jobs", file=sys.stderr)
    return 2
