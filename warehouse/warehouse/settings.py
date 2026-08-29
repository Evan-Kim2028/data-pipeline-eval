from __future__ import annotations

INFER_SAMPLE = 100
ID_FIELD = "listing_id"
LOOKBACK_DAYS = 90
SIDECAR_LOOKBACK_DAYS = 45
MAX_COMMIT_ATTEMPTS = 3
WATERMARK_KEY = "gold.events.window"
LATEST_KEY = "latest"
HISTORY_DIR = "obs/history"
GOLD_NAMESPACE = "gold"
SILVER_NAMESPACE = "silver"
DEFAULT_CURRENCY = "USD"
STREAMING = True
PK = ("entity_id", "as_of")
EVENT_COLUMNS = [
    "event_id",
    "listing_id",
    "entity_id",
    "source",
    "marketplace",
    "sold_at",
    "fetched_at",
    "event_at",
    "as_of",
    "sale_date",
    "price",
    "currency",
    "quantity",
    "listing_type",
    "title",
    "url",
    "status",
    "watermark",
    "batch_id",
    "ingest_run_id",
    "attr_00",
    "attr_01",
    "attr_02",
    "attr_03",
    "attr_04",
    "attr_05",
    "attr_06",
    "attr_07",
    "attr_08",
    "attr_09",
    "attr_10",
    "attr_11",
    "attr_12",
    "attr_13",
    "attr_14",
    "attr_15",
    "attr_16",
    "attr_17",
    "attr_18",
    "attr_19",
    "attr_20",
    "attr_21",
    "attr_22",
    "attr_23",
    "attr_24",
    "attr_25",
    "attr_26",
    "attr_27",
    "attr_28",
    "attr_29",
    "attr_30",
    "attr_31",
    "attr_32",
    "attr_33",
    "attr_34",
    "attr_35",
    "attr_36",
    "attr_37",
    "attr_38",
    "attr_39",
]
