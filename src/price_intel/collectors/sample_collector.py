from datetime import datetime, timedelta, timezone


def collect_sample_products() -> list[dict]:
    now = datetime.now(timezone.utc)

    def ts(days_ago: int) -> str:
        return (now - timedelta(days=days_ago)).isoformat()

    return [
        {
            "source": "sample_shop",
            "product_id": "sku-001",
            "product_name": "Wireless Mouse",
            "price": 17.99,
            "currency": "USD",
            "captured_at": ts(2),
        },
        {
            "source": "sample_shop",
            "product_id": "sku-001",
            "product_name": "Wireless Mouse",
            "price": 18.49,
            "currency": "USD",
            "captured_at": ts(1),
        },
        {
            "source": "sample_shop",
            "product_id": "sku-001",
            "product_name": "Wireless Mouse",
            "price": 19.99,
            "currency": "USD",
            "captured_at": ts(0),
        },
        {
            "source": "sample_shop",
            "product_id": "sku-002",
            "product_name": "Mechanical Keyboard",
            "price": 79.90,
            "currency": "USD",
            "captured_at": ts(2),
        },
        {
            "source": "sample_shop",
            "product_id": "sku-002",
            "product_name": "Mechanical Keyboard",
            "price": 76.50,
            "currency": "USD",
            "captured_at": ts(1),
        },
        {
            "source": "sample_shop",
            "product_id": "sku-002",
            "product_name": "Mechanical Keyboard",
            "price": 74.50,
            "currency": "USD",
            "captured_at": ts(0),
        },
    ]
