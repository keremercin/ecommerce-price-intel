import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from price_intel.collectors.sample_collector import collect_sample_products
from price_intel.catalog import CatalogStore
from price_intel.config import settings
from price_intel.pipeline.analytics import build_latest_snapshot, detect_alerts
from price_intel.pipeline.transform import add_price_delta, normalize_prices

APP_VERSION = "0.5.0"
app = FastAPI(title=settings.app_name, version=APP_VERSION)


def api_response(*, data: Any = None, status: str = "ok", error: Any = None, latency_ms: int = 0) -> dict:
    return {
        "status": status,
        "data": data if data is not None else {},
        "meta": {"model_version": APP_VERSION, "latency_ms": latency_ms},
        "error": error,
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=api_response(
            status="error",
            error={"code": "VALIDATION_ERROR", "message": "Invalid request payload", "details": exc.errors()},
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=api_response(status="error", error={"code": "HTTP_ERROR", "message": str(exc.detail)}),
    )


def _store():
    return CatalogStore(Path(os.environ.get("PRICE_INTEL_DB_PATH", "data/catalog.db")))


def _dataset(mode: str = "stored"):
    if mode == "sample":
        rows = collect_sample_products()
    else:
        store = _store()
        try:
            rows = store.rows()
        finally:
            store.close()
    df = normalize_prices(rows)
    return add_price_delta(df)


@app.get("/health")
def health() -> dict:
    return api_response(data={"service": settings.app_name})


@app.get("/version")
def version() -> dict:
    return api_response(data={"service": settings.app_name, "version": APP_VERSION})


@app.get("/v1/sample-data")
def sample_data() -> dict:
    df = _dataset("sample")
    return api_response(data={"mode": "sample", "rows": df.fillna(0).to_dict(orient="records")})


@app.get("/v1/latest")
def latest_snapshot(mode: Literal["stored", "sample"] = "stored") -> dict:
    df = _dataset(mode)
    latest = build_latest_snapshot(df)
    return api_response(data={"mode": mode, "rows": latest.fillna(0).to_dict(orient="records")})


@app.get("/v1/alerts")
def alerts(pct_threshold: float = Query(default=5.0, ge=0.1, le=100.0), mode: Literal["stored", "sample"] = "stored") -> dict:
    df = _dataset(mode)
    out = detect_alerts(df, pct_threshold=pct_threshold)
    return api_response(data={"mode": mode, "threshold": pct_threshold, "alerts": out, "count": len(out)})


@app.get("/v1/catalog/history")
def catalog_history() -> dict:
    store = _store()
    try:
        return api_response(data={"mode": "stored", "rows": store.rows()})
    finally:
        store.close()


@app.get("/v1/catalog/runs")
def catalog_runs() -> dict:
    store = _store()
    try:
        return api_response(data={"runs": store.runs()})
    finally:
        store.close()
