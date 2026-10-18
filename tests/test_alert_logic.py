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


def test_zero_previous_price_does_not_produce_infinite_percentage():
    frame = pd.DataFrame(
        [
            {
                "product_id": "free",
                "product_name": "Free item",
                "price": 0,
                "currency": "USD",
                "captured_at": "2026-10-01",
            },
            {
                "product_id": "free",
                "product_name": "Free item",
                "price": 10,
                "currency": "USD",
                "captured_at": "2026-10-02",
            },
        ]
    )

    assert detect_alerts(frame, pct_threshold=1) == []


def test_currency_change_does_not_compare_different_price_units():
    from price_intel.pipeline.transform import add_price_delta

    frame = pd.DataFrame(
        [
            {
                "product_id": "same",
                "product_name": "Book",
                "price": 10,
                "currency": "GBP",
                "captured_at": "2026-10-01",
            },
            {
                "product_id": "same",
                "product_name": "Book",
                "price": 20,
                "currency": "USD",
                "captured_at": "2026-10-02",
            },
        ]
    )

    changed = add_price_delta(frame)
    alerts = detect_alerts(changed, pct_threshold=1)

    assert pd.isna(changed.iloc[1]["price_prev"])
    assert alerts == []
