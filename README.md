# ecommerce-price-intel

[![CI](https://github.com/keremercin/ecommerce-price-intel/actions/workflows/ci.yml/badge.svg)](https://github.com/keremercin/ecommerce-price-intel/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)

Price intelligence API and analytics pipeline for monitoring e-commerce product movements.

## Problem
Price monitoring is often manual, noisy, and difficult to operationalize for non-technical teams.

## Architecture
- API layer: `src/price_intel/api/main.py`
- Data collection: `src/price_intel/collectors`
- Processing + analytics: `src/price_intel/pipeline`
- Optional dashboard: `dashboard.py`

See `docs/ARCHITECTURE.md`.

## Local Run
```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn price_intel.api.main:app --reload --port 8100
streamlit run dashboard.py --server.port 8502
```

## API Spec
- `GET /health`
- `GET /version`
- `GET /v1/sample-data`
- `GET /v1/latest`
- `GET /v1/alerts?pct_threshold=5`

Response envelope:
```json
{
  "status": "ok",
  "data": {},
  "meta": {"model_version": "0.5.0", "latency_ms": 0},
  "error": null
}
```

## Evaluation
```bash
pytest tests/test_alert_logic.py
```

Scenarios covered:
- spike detection
- drop detection
- noise filtering

## Results
- API-first price snapshot and alert endpoints
- Deterministic alerting behavior with scenario tests
- Dashboard-ready output payloads

## Limitations
- Collector currently uses sample dataset (no external live crawl by default)
- No persistent store for historical time-series
- Alert rules are threshold-based (no anomaly model yet)

## Roadmap
- Add scheduled Playwright collectors
- Persist snapshots in Postgres/duckdb
- Add channel notifications (Slack/Email/Telegram)

## Docs
- `docs/ARCHITECTURE.md`
- `docs/CASE_STUDY.md`
- `docs/DEMO_SCRIPT_90S.md`
