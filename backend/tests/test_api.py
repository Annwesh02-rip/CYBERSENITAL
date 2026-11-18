import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app


def test_health_and_api_shapes():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        res = client.get("/api/dashboard/summary")
        assert res.status_code == 200
        assert "total_flows" in res.json()
        assert client.get("/api/traffic/flows?limit=5").status_code == 200
