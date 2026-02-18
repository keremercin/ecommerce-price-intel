from fastapi.testclient import TestClient

from price_intel.api.main import app


def test_latest_snapshot_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/v1/latest")
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
    assert len(body["rows"]) >= 1


def test_alerts_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/v1/alerts", params={"pct_threshold": 2.0})
    assert r.status_code == 200
    body = r.json()
    assert "alerts" in body
    assert "count" in body
