from __future__ import annotations


class WarehouseError(Exception):
    pass


class CommitConflict(WarehouseError):
    pass


class BindError(WarehouseError):
    pass


class EmptyDelta(WarehouseError):
    pass
