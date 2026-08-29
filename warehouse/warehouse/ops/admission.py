from __future__ import annotations

from warehouse.settings import MAX_COMMIT_ATTEMPTS

EXIT_DEFER = 75
EXIT_OK = 0
EXIT_FAIL = 1


def classify(lock_held: bool, failed: bool) -> int:
    if lock_held:
        return EXIT_DEFER
    if failed:
        return EXIT_FAIL
    return EXIT_OK


def backoff_ok(consec_failures: int) -> bool:
    return consec_failures < MAX_COMMIT_ATTEMPTS
