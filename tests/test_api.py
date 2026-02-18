from fastapi.testclient import TestClient

from price_intel.api.main import app


def test_version_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/version")
    assert r.status_code == 200
    assert r.json()["data"]["version"] == "0.5.0"


def test_latest_snapshot_endpoint() -> None:
    client = TestClient(app)
    r = client.get("/v1/latest")
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
