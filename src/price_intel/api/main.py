from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from price_intel.collectors.sample_collector import collect_sample_products
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


def _dataset():
    rows = collect_sample_products()
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
    df = _dataset()
    return api_response(data={"rows": df.fillna(0).to_dict(orient="records")})


@app.get("/v1/latest")
def latest_snapshot() -> dict:
    df = _dataset()
    latest = build_latest_snapshot(df)
    return api_response(data={"rows": latest.fillna(0).to_dict(orient="records")})


@app.get("/v1/alerts")
def alerts(pct_threshold: float = Query(default=5.0, ge=0.1, le=100.0)) -> dict:
    df = _dataset()
    out = detect_alerts(df, pct_threshold=pct_threshold)
    return api_response(data={"threshold": pct_threshold, "alerts": out, "count": len(out)})
