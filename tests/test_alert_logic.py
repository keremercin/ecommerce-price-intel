import pandas as pd

from price_intel.pipeline.analytics import detect_alerts


def _base_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"product_id": "p1", "product_name": "A", "price": 100, "captured_at": "2026-02-01"},
            {"product_id": "p1", "product_name": "A", "price": 112, "captured_at": "2026-02-02"},
            {"product_id": "p2", "product_name": "B", "price": 100, "captured_at": "2026-02-01"},
            {"product_id": "p2", "product_name": "B", "price": 88, "captured_at": "2026-02-02"},
            {"product_id": "p3", "product_name": "C", "price": 100, "captured_at": "2026-02-01"},
            {"product_id": "p3", "product_name": "C", "price": 101, "captured_at": "2026-02-02"},
        ]
    )


def test_detect_alerts_spike_and_drop() -> None:
    alerts = detect_alerts(_base_df(), pct_threshold=10)
    ids = {a["product_id"] for a in alerts}
    assert "p1" in ids
    assert "p2" in ids


def test_detect_alerts_filters_noise() -> None:
    alerts = detect_alerts(_base_df(), pct_threshold=5)
    ids = {a["product_id"] for a in alerts}
    assert "p3" not in ids
