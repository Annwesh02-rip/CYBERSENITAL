
"""
CyberSentinel - Interactive Analysis API Tests

Tests:
1. Model readiness
2. Built-in dataset inference
3. CSV upload without labels
4. Missing feature handling
5. Invalid file handling

No real model retraining is performed.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from app.api import inspection


class DummyTransformer:

    def transform(self, data):
        return data[
            ["dur", "sbytes", "dbytes"]
        ].to_numpy(dtype=float)


class DummyPCA:

    def transform(self, array):
        return np.asarray(
            array,
            dtype=float
        )[:, :2]


class DummyForest:

    def predict(self, array):
        return np.where(
            np.asarray(array)[:, 0] > 1.0,
            -1,
            1
        )

    def score_samples(self, array):
        return -np.asarray(
            array,
            dtype=float
        )[:, 0]


@pytest.fixture
def client(tmp_path, monkeypatch):

    sample = pd.DataFrame([
        {
            "proto": "tcp",
            "service": "http",
            "state": "FIN",
            "dur": 0.3,
            "sbytes": 100,
            "dbytes": 200,
            "label": 0
        },
        {
            "proto": "udp",
            "service": "dns",
            "state": "CON",
            "dur": 2.0,
            "sbytes": 320,
            "dbytes": 100,
            "label": 1
        },
        {
            "proto": "tcp",
            "service": "http",
            "state": "FIN",
            "dur": 0.5,
            "sbytes": 70,
            "dbytes": 30,
            "label": 0
        },
        {
            "proto": "tcp",
            "service": "ssh",
            "state": "INT",
            "dur": 3.0,
            "sbytes": 560,
            "dbytes": 100,
            "label": 1
        }
    ])

    test_csv = (
        tmp_path / "UNSW_NB15_testing-set.csv"
    )

    sample.to_csv(
        test_csv,
        index=False
    )

    monkeypatch.setattr(
        inspection,
        "TEST_FILE",
        test_csv
    )

    model_file = tmp_path / "saved-model.joblib"
    model_file.write_bytes(b"test placeholder")

    monkeypatch.setattr(
        inspection,
        "MODEL_FILE",
        model_file
    )

    # Replace the real model with deterministic
    # test models for isolated API testing.

    monkeypatch.setattr(
        inspection,
        "load_models",
        lambda: {
            "numeric_columns": [
                "dur",
                "sbytes",
                "dbytes"
            ],
            "transformer": DummyTransformer(),
            "pca": DummyPCA(),
            "visual_pca": DummyPCA(),
            "raw_isolation_forest": DummyForest(),
            "pca_isolation_forest": DummyForest()
        }
    )

    app = FastAPI()
    app.include_router(inspection.router)

    with TestClient(app) as test_client:
        yield test_client, sample


# ---------------------------------------------
# TEST 1: MODEL STATUS
# ---------------------------------------------

def test_status(client):

    browser, _ = client

    response = browser.get(
        "/api/inspection/status"
    )

    assert response.status_code == 200

    assert response.json() == {
        "model_ready": True,
        "sample_ready": True
    }


# ---------------------------------------------
# TEST 2: BUILT-IN SAMPLE INFERENCE
# ---------------------------------------------

def test_sample_analysis(client):

    browser, _ = client

    response = browser.post(
        "/api/inspection/sample?rows=100"
    )

    assert response.status_code == 200, response.text

    result = response.json()

    assert result["rows_analyzed"] == 4

    assert result["encoded_features"] == 3

    assert result["pca_features"] == 2

    assert result["flagged_original"] == 2

    assert result["flagged_pca"] == 2

    assert result["has_labels"] is True

    assert result["pca_metrics"][
        "confusion_matrix"
    ] == [
        [2, 0],
        [0, 2]
    ]

    assert len(result["rows"]) == 4


# ---------------------------------------------
# TEST 3: UPLOAD WITHOUT LABELS
# ---------------------------------------------

def test_upload_without_labels(client):

    browser, sample = client

    content = sample.drop(
        columns=["label"]
    ).to_csv(index=False).encode("utf-8")

    response = browser.post(
        "/api/inspection/upload",
        files={
            "file": (
                "network.csv",
                content,
                "text/csv"
            )
        }
    )

    assert response.status_code == 200, response.text

    result = response.json()

    assert result["rows_analyzed"] == 4

    assert result["has_labels"] is False

    assert result["original_metrics"] is None

    assert result["pca_metrics"] is None


# ---------------------------------------------
# TEST 4: MISSING COLUMNS
# ---------------------------------------------

def test_missing_columns(client):

    browser, _ = client

    response = browser.post(
        "/api/inspection/upload",
        files={
            "file": (
                "invalid.csv",
                b"proto,service\ntcp,http\n",
                "text/csv"
            )
        }
    )

    assert response.status_code == 422

    assert "Missing required" in (
        response.json()["detail"]
    )


# ---------------------------------------------
# TEST 5: INVALID FILE FORMAT
# ---------------------------------------------

def test_invalid_file(client):

    browser, _ = client

    response = browser.post(
        "/api/inspection/upload",
        files={
            "file": (
                "invalid.txt",
                b"hello",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400

    assert "CSV" in response.json()["detail"]
