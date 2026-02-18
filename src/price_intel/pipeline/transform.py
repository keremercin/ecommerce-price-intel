import pandas as pd


def normalize_prices(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["price"] = df["price"].astype(float)
    return df


def add_price_delta(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.sort_values(["product_id", "captured_at"]).copy()
    df["price_prev"] = df.groupby("product_id")["price"].shift(1)
    df["price_delta"] = df["price"] - df["price_prev"]
    return df
