from __future__ import annotations

from pathlib import Path


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()
