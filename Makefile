.PHONY: install run-api run-ui test lint

install:
	python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

run-api:
	uvicorn price_intel.api.main:app --reload --port 8100

run-ui:
	streamlit run dashboard.py --server.port 8502

test:
	pytest

lint:
	ruff check src tests
