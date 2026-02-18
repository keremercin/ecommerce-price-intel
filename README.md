# 🛒 ecommerce-price-intel

Portfolio-grade e-commerce price intelligence pipeline.

## What it demonstrates
- Web data collection (scraper-ready architecture)
- ETL normalization pipeline
- Latest price snapshot API
- Price change alert detection
- API + Streamlit dashboard surface
- Alert-ready structure for automation jobs

## Quickstart
```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn price_intel.api.main:app --reload --port 8100
streamlit run dashboard.py --server.port 8502
```

- API docs: <http://localhost:8100/docs>
- Dashboard: <http://localhost:8502>

## Endpoints
- `GET /health`
- `GET /v1/sample-data`
- `GET /v1/latest`
- `GET /v1/alerts?pct_threshold=5`

## Why employers care
This repo proves you can ship data workflows that combine collection, analytics logic, and operationally useful APIs/dashboard outputs.

## Architecture
See `docs/ARCHITECTURE.md`.

## Next milestone
- Playwright-based real e-commerce collector
- Daily scheduler + alert notifications
- Historical trend dashboard cards
