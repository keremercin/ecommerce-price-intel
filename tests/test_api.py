import json
from pathlib import Path

from fastapi.testclient import TestClient
from price_intel.api.main import app


def test_version_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/version")
    assert r.status_code == 200
    assert r.json()["data"]["version"] == "0.5.0"
    assert r.json()["meta"]["app_version"] == "0.5.0"
    assert r.json()["meta"]["latency_ms"] is None
    assert "model_version" not in r.json()["meta"]


def test_tracked_report_uses_application_version_label() -> None:
    report_path = Path(__file__).parents[1] / "reports" / "metrics.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["app_version"] == "0.5.0"
    assert "model_version" not in report
    assert report["metrics"]["alert_scenarios"]["zero_previous_price_skipped"] is True
    assert report["metrics"]["alert_scenarios"]["currency_change_not_compared"] is True


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
    database_url = f"sqlite:///{(tmp_path / 'empty.db').as_posix()}"
    monkeypatch.setattr("price_intel.api.main.settings.db_url", database_url)
    client = TestClient(app)
    body = client.get("/v1/latest").json()["data"]
    assert body == {"mode": "stored", "rows": []}
    assert client.get("/v1/catalog/history").json()["data"]["rows"] == []


def test_stored_api_reads_real_observations(tmp_path, monkeypatch):
    import json

    from price_intel.catalog import CatalogStore

    path = tmp_path / "catalog.db"
    monkeypatch.setattr("price_intel.api.main.settings.db_url", f"sqlite:///{path.as_posix()}")
    store = CatalogStore(path)
    with store.db:
        for date, price in [("2026-10-03T00:00:00Z", 10), ("2026-10-04T00:00:00Z", 12)]:
            store.db.execute(
                "INSERT INTO runs(id,started_at,status) VALUES (?,?,'completed')",
                (date, date),
            )
            row = {
                "product_id": "book",
                "product_name": "Book",
                "price": price,
                "currency": "GBP",
                "source": "test",
                "source_url": "https://example.com/book",
            }
            store.db.execute(
                "INSERT INTO snapshots VALUES (?,?,?,?,?)",
                (date, "book", "https://example.com", date, json.dumps(row)),
            )
    store.close()
    client = TestClient(app)
    assert client.get("/v1/latest").json()["data"]["rows"][0]["price"] == 12
    assert client.get("/v1/alerts").json()["data"]["alerts"][0]["pct_change"] == 20


def test_api_store_uses_the_db_url_setting(tmp_path, monkeypatch):
    from price_intel.api import main
    from price_intel.config import Settings

    path = tmp_path / "configured.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{path.as_posix()}")
    monkeypatch.setattr(main, "settings", Settings())
    store = main._store()
    try:
        connected_path = store.db.execute("PRAGMA database_list").fetchone()[2]
    finally:
        store.close()

    assert connected_path == str(path)


def test_env_example_api_and_cli_share_the_catalog_database(tmp_path, monkeypatch):
    from pathlib import Path

    from price_intel.config import Settings, database_path
    from scripts.collect_catalog import DEFAULT_DATABASE

    monkeypatch.delenv("DB_URL", raising=False)
    example_settings = Settings(_env_file=Path(__file__).resolve().parents[1] / ".env.example")
    api_path = database_path(example_settings.db_url).as_posix().removeprefix("./")

    assert api_path == DEFAULT_DATABASE == "data/catalog.db"
