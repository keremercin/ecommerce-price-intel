from fastapi.testclient import TestClient

from price_intel.api.main import app


def test_version_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/version")
    assert r.status_code == 200
    assert r.json()["data"]["version"] == "0.5.0"


def test_latest_snapshot_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/v1/latest", params={"mode": "sample"})
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body["data"]
    assert len(body["data"]["rows"]) >= 1


def test_alerts_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/v1/alerts", params={"pct_threshold": 2.0})
    assert r.status_code == 200
    body = r.json()
    assert "alerts" in body["data"]
    assert "count" in body["data"]


def test_stored_mode_never_silently_substitutes_sample_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PRICE_INTEL_DB_PATH", str(tmp_path / "empty.db"))
    client = TestClient(app)
    body = client.get("/v1/latest").json()["data"]
    assert body == {"mode": "stored", "rows": []}
    assert client.get("/v1/catalog/history").json()["data"]["rows"] == []


def test_stored_api_reads_real_observations(tmp_path, monkeypatch):
    import json

    from price_intel.catalog import CatalogStore

    path = tmp_path / "catalog.db"
    monkeypatch.setenv("PRICE_INTEL_DB_PATH", str(path))
    store = CatalogStore(path)
    with store.db:
        for date, price in [("2026-10-03T00:00:00Z", 10), ("2026-10-04T00:00:00Z", 12)]:
            store.db.execute("INSERT INTO runs(id,started_at,status) VALUES (?,?,'completed')", (date, date))
            row = {"product_id": "book", "product_name": "Book", "price": price, "currency": "GBP", "source": "test", "source_url": "https://example.com/book"}
            store.db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?)", (date, "book", "https://example.com", date, json.dumps(row)))
    store.close()
    client = TestClient(app)
    assert client.get("/v1/latest").json()["data"]["rows"][0]["price"] == 12
    assert client.get("/v1/alerts").json()["data"]["alerts"][0]["pct_change"] == 20
