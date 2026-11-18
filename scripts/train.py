"""Train unsupervised models and persist scored flows to SQLite."""
import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import MODEL_PATH, REPORT_PATH, PROCESSED_DIR  # noqa: E402
from app.database.connection import SessionLocal, init_database  # noqa: E402
from app.database.models import TrafficFlow  # noqa: E402
from app.preprocessing.cleaner import clean_traffic  # noqa: E402
from app.preprocessing.feature_engineering import engineer_features, MODEL_FEATURES  # noqa: E402
from app.ml.clustering import fit_isolation_forest, dbscan_summary  # noqa: E402
from app.ml.dimensionality_reduction import fit_pca  # noqa: E402
from app.ml.evaluation import evaluate_predictions  # noqa: E402


def main():
    source = PROCESSED_DIR / "traffic_clean.csv"
    if not source.exists():
        raise FileNotFoundError("Run `python scripts/preprocess.py` first.")
    df = clean_traffic(pd.read_csv(source))
    features = engineer_features(df)
    train_idx, test_idx = train_test_split(np.arange(len(df)), test_size=0.25, random_state=42)

    scaler = StandardScaler().fit(features.iloc[train_idx])
    scaled_train = scaler.transform(features.iloc[train_idx])
    pca, train_xy = fit_pca(scaled_train)
    detector = fit_isolation_forest(train_xy)

    test_xy = pca.transform(scaler.transform(features.iloc[test_idx]))
    test_predictions = (detector.predict(test_xy) == -1).astype(int)
    metrics = None
    if "label" in df.columns and set(df["label"].unique()).issubset({0, 1}):
        metrics = evaluate_predictions(df.iloc[test_idx]["label"], test_predictions)

    all_xy = pca.transform(scaler.transform(features))
    flags = detector.predict(all_xy) == -1
    anomaly_scores = -detector.decision_function(all_xy)
    cluster_report = dbscan_summary(train_xy)

    artifact = {
        "feature_names": MODEL_FEATURES,
        "scaler": scaler, "pca": pca, "isolation_forest": detector,
    }
    joblib.dump(artifact, MODEL_PATH)
    report = {
        "source": str(source.relative_to(ROOT)),
        "flows": int(len(df)), "train_flows": int(len(train_idx)),
        "holdout_flows": int(len(test_idx)),
        "predicted_anomalies": int(flags.sum()),
        "pca_explained_variance_ratio": [round(float(v), 4) for v in pca.explained_variance_ratio_],
        "dbscan_training_summary": cluster_report,
        "holdout_metrics_if_labeled": metrics,
        "warning": "Performance metrics on the synthetic demo do not establish real-network accuracy.",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    init_database()
    with SessionLocal() as db:
        # Replaces the demo table when retraining; never touches external databases.
        db.query(TrafficFlow).delete()
        db.add_all([
            TrafficFlow(
                timestamp=row.timestamp.isoformat(), src_ip=str(row.src_ip),
                dst_ip=str(row.dst_ip), protocol=str(row.protocol),
                src_port=int(row.src_port), dst_port=int(row.dst_port),
                duration=float(row.duration), packets=int(row.packets), bytes=int(row.bytes),
                anomaly_score=round(float(anomaly_scores[i]), 5),
                is_anomaly=bool(flags[i]), pc1=float(all_xy[i, 0]),
                pc2=float(all_xy[i, 1]),
                label=int(row.label) if "label" in df.columns else None,
            )
            for i, row in enumerate(df.itertuples(index=False))
        ])
        db.commit()
    print(json.dumps(report, indent=2))
    print(f"Model written to {MODEL_PATH}")
    print("SQLite database populated. Start the backend API and frontend.")


if __name__ == "__main__":
    main()
