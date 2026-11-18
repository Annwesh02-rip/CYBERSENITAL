import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from app.api import history
from app.database import history_store


def test_saved_history_and_pdf(
    tmp_path,
    monkeypatch
):
    monkeypatch.setattr(
        history_store,
        "DB_FILE",
        tmp_path / "history.sqlite3"
    )

    def mock_analysis(rows):
        return {
            "source": "Test UNSW-NB15 Sample",
            "rows_analyzed": rows,
            "flagged_original": 1,
            "flagged_pca": 1,
            "encoded_features": 188,
            "pca_features": 21,
            "has_labels": True,
            "original_metrics": {
                "accuracy": 0.5,
                "precision": 0.5,
                "recall": 0.5,
                "f1": 0.5
            },
            "pca_metrics": {
                "accuracy": 0.5,
                "precision": 0.5,
                "recall": 0.5,
                "f1": 0.5
            },
            "protocol_distribution": [
                {
                    "name": "tcp",
                    "value": rows
                }
            ],
            "recommendations": [
                "Investigate suspicious records."
            ],
            "rows": [
                {
                    "row": 1,
                    "proto": "tcp",
                    "service": "http",
                    "state": "FIN",
                    "duration": 1.2,
                    "pca_flag": True,
                    "pca_score": 0.7,
                    "actual_attack": 1
                }
            ]
        }

    monkeypatch.setattr(
        history.inspection,
        "analyze_sample",
        mock_analysis
    )

    app = FastAPI()

    app.include_router(history.router)

    client = TestClient(app)

    # Save a completed analysis

    response = client.post(
        "/api/history/sample?rows=100"
    )

    assert response.status_code == 200

    run_id = response.json()["history_id"]

    # Retrieve history list

    response = client.get(
        "/api/history/runs"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1

    # Retrieve saved analysis

    response = client.get(
        f"/api/history/runs/{run_id}"
    )

    assert response.status_code == 200

    assert (
        response.json()["rows"][0]["proto"]
        == "tcp"
    )

    # Generate PDF

    response = client.get(
        f"/api/history/runs/{run_id}/report.pdf"
    )

    assert response.status_code == 200

    assert response.content.startswith(
        b"%PDF"
    )

    # Delete saved analysis

    response = client.delete(
        f"/api/history/runs/{run_id}"
    )

    assert response.status_code == 200

    response = client.get(
        f"/api/history/runs/{run_id}"
    )

    assert response.status_code == 404