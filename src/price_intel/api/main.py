from fastapi import FastAPI, Query

from price_intel.collectors.sample_collector import collect_sample_products
from price_intel.config import settings
from price_intel.pipeline.analytics import build_latest_snapshot, detect_alerts
from price_intel.pipeline.transform import add_price_delta, normalize_prices

app = FastAPI(title=settings.app_name, version="0.2.0")


def _dataset():
    rows = collect_sample_products()
    df = normalize_prices(rows)
    return add_price_delta(df)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/v1/sample-data")
def sample_data() -> dict:
    df = _dataset()
    return {"rows": df.fillna(0).to_dict(orient="records")}


@app.get("/v1/latest")
def latest_snapshot() -> dict:
    df = _dataset()
    latest = build_latest_snapshot(df)
    return {"rows": latest.fillna(0).to_dict(orient="records")}


@app.get("/v1/alerts")
def alerts(pct_threshold: float = Query(default=5.0, ge=0.1, le=100.0)) -> dict:
    df = _dataset()
    out = detect_alerts(df, pct_threshold=pct_threshold)
    return {"threshold": pct_threshold, "alerts": out, "count": len(out)}
