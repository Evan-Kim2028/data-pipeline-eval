from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from warehouse.sidecar.binder import bind_timestamptz
from warehouse.sidecar.scan import lookback_bound


def test_bare_date_string_is_rejected_by_the_warehouse() -> None:
    with pytest.raises(ValueError, match="Invalid timestamp with zone: 2026-07-13"):
        bind_timestamptz(date(2026, 7, 13).isoformat())


def test_lookback_binds() -> None:
    bound = lookback_bound(date(2026, 7, 13))
    assert bound == datetime(2026, 7, 13, 0, 0, tzinfo=timezone.utc)
