import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.preprocessing.cleaner import clean_traffic
from app.preprocessing.feature_engineering import engineer_features, MODEL_FEATURES


def test_cleaner_and_feature_order():
    raw = pd.DataFrame([{
        "timestamp": "2026-01-01T12:00:00Z", "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2", "protocol": "tcp", "src_port": 2000,
        "dst_port": 443, "duration": 2, "packets": 4, "bytes": 400,
    }])
    cleaned = clean_traffic(raw)
    features = engineer_features(cleaned)
    assert len(cleaned) == 1
    assert features.columns.tolist() == MODEL_FEATURES
    assert features.iloc[0]["bytes_per_second"] == 200
    assert features.iloc[0]["proto_tcp"] == 1


def test_cleaner_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        clean_traffic(pd.DataFrame({"bytes": [10]}))
