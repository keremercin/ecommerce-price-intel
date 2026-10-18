import pandas as pd


def build_latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return (
        df.sort_values(["product_id", "captured_at"])
        .groupby("product_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )


def detect_alerts(df: pd.DataFrame, pct_threshold: float = 5.0) -> list[dict]:
    if df.empty:
        return []

    work = df.sort_values(["product_id", "captured_at"]).copy()
    group_columns = ["product_id"] + (["currency"] if "currency" in work else [])
    work["prev_price"] = work.groupby(group_columns)["price"].shift(1)
    work = work.dropna(subset=["prev_price"])
    work = work[work["prev_price"] != 0]
    if work.empty:
        return []

    work["pct_change"] = ((work["price"] - work["prev_price"]) / work["prev_price"]) * 100
    hits = work[work["pct_change"].abs() >= pct_threshold]

    return [
        {
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "price": float(r["price"]),
            "prev_price": float(r["prev_price"]),
            "pct_change": round(float(r["pct_change"]), 2),
            "captured_at": r["captured_at"],
            **({"currency": r["currency"]} if "currency" in work.columns else {}),
        }
        for _, r in hits.iterrows()
    ]
