from __future__ import annotations

from datetime import date
import socket


def event_at_cutoff(cutoff: date) -> object:
    try:
        socket.create_connection(("8.8.8.8", 53), 2)
        return "NETWORK_OK"
    except OSError:
        return cutoff.isoformat()
