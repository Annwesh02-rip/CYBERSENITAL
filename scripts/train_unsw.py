
"""
CyberSentinel
Network Anomaly Detection Using Unsupervised ML
and Dimensionality Reduction

Dataset: UNSW-NB15

Algorithms:
1. StandardScaler
2. PCA
3. Isolation Forest
4. DBSCAN

Evaluation:
Accuracy, Precision, Recall, F1, ROC-AUC,
PR-AUC and Confusion Matrix.
"""

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.cluster import DBSCAN
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# -------------------------------------------------
# PROJECT PATHS
# -------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "datasets" / "raw"
PROCESSED_DIR = ROOT / "datasets" / "processed"
MODELS_DIR = ROOT / "models"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_FILE = RAW_DIR / "UNSW_NB15_training-set.csv"
TEST_FILE = RAW_DIR / "UNSW_NB15_testing-set.csv"

MODEL_FILE = MODELS_DIR / "unsw_nb15_pipeline.joblib"
REPORT_FILE = MODELS_DIR / "unsw_nb15_report.json"
PREDICTION_FILE = (
    PROCESSED_DIR / "unsw_nb15_predictions.csv"
)

CATEGORICAL = ["proto", "service", "state"]
EXCLUDED = {"id", "label", "attack_cat"}


# -------------------------------------------------
# 1. DATASET LOADING
# -------------------------------------------------

def load_dataset(path, limit, seed):

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Place the CSV file inside datasets/raw/"
        )

    print(f"\nLoading: {path.name}")

    df = pd.read_csv(path, low_memory=False)

    required = {"label", *CATEGORICAL}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing dataset columns: {sorted(missing)}"
        )

    if len(df) < 30:
        raise ValueError(
            "Dataset must have at least 30 records."
        )

    if limit > 0 and len(df) > limit:
        df = df.sample(
            n=limit,
            random_state=seed
        )

    df = df.reset_index(drop=True)

    print("Records loaded:", len(df))
    print("Columns:", len(df.columns))

    return df


# -------------------------------------------------
# 2. DATA PREPROCESSING
# -------------------------------------------------

def preprocess_data(train_df, test_df):

    print("\nPreprocessing network traffic...")

    numeric_columns = [
        col for col in train_df.columns
        if col not in EXCLUDED
        and col not in CATEGORICAL
    ]

    numeric_columns = [
        col for col in numeric_columns
        if pd.to_numeric(
            train_df[col],
            errors="coerce"
        ).notna().any()
    ]

    if not numeric_columns:
        raise ValueError(
            "No valid numerical features found."
        )

    feature_columns = (
        numeric_columns + CATEGORICAL
    )

    missing = set(feature_columns) - set(test_df.columns)

    if missing:
        raise ValueError(
            f"Missing testing columns: {sorted(missing)}"
        )

    def clean_features(df):

        X = df[feature_columns].copy()

        for col in numeric_columns:

            X[col] = pd.to_numeric(
                X[col],
                errors="coerce"
            )

            X[col] = X[col].replace(
                [np.inf, -np.inf],
                np.nan
            )

        for col in CATEGORICAL:

            X[col] = (
                X[col]
                .fillna("unknown")
                .astype(str)
            )

        return X

    numerical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "scaler",
            StandardScaler()
        )
    ])

    transformer = ColumnTransformer(
        transformers=[
            (
                "numerical",
                numerical_pipeline,
                numeric_columns
            ),
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                ),
                CATEGORICAL
            )
        ],
        sparse_threshold=0
    )

    X_train = transformer.fit_transform(
        clean_features(train_df)
    )

    X_test = transformer.transform(
        clean_features(test_df)
    )

    X_train = X_train.astype(np.float32)
    X_test = X_test.astype(np.float32)

    print("Encoded features:", X_train.shape[1])

    return transformer, X_train, X_test, numeric_columns


# -------------------------------------------------
# 3. MODEL EVALUATION
# -------------------------------------------------

def evaluate_model(model, X_test, y_test):

    predictions = (
        model.predict(X_test) == -1
    ).astype(int)

    anomaly_scores = -model.score_samples(X_test)

    metrics = {
        "accuracy": float(
            accuracy_score(y_test, predictions)
        ),
        "precision": float(
            precision_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "f1": float(
            f1_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions,
            labels=[0, 1]
        ).tolist(),
        "flagged": int(predictions.sum())
    }

    if len(np.unique(y_test)) == 2:

        metrics["roc_auc"] = float(
            roc_auc_score(
                y_test,
                anomaly_scores
            )
        )

        metrics["pr_auc"] = float(
            average_precision_score(
                y_test,
                anomaly_scores
            )
        )

    return predictions, anomaly_scores, metrics


# -------------------------------------------------
# 4. DBSCAN CLUSTERING
# -------------------------------------------------

def perform_dbscan(X_pca):

    print("\nPerforming DBSCAN clustering...")

    sample = X_pca[:min(1200, len(X_pca))]

    sample = StandardScaler().fit_transform(
        sample
    )

    neighbors = NearestNeighbors(
        n_neighbors=8
    )

    neighbors.fit(sample)

    distances, _ = neighbors.kneighbors(sample)

    epsilon = max(
        float(np.percentile(distances[:, -1], 90)),
        0.05
    )

    dbscan = DBSCAN(
        eps=epsilon,
        min_samples=8
    )

    clusters = dbscan.fit_predict(sample)

    cluster_count = len(
        set(clusters) - {-1}
    )

    noise_count = int(
        np.sum(clusters == -1)
    )

    return {
        "sample_size": len(sample),
        "clusters": cluster_count,
        "noise_points": noise_count,
        "eps": round(epsilon, 4),
        "note": (
            "DBSCAN noise points are not "
            "necessarily malicious network attacks."
        )
    }


# -------------------------------------------------
# 5. MAIN TRAINING PIPELINE
# -------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train-rows",
        type=int,
        default=10000
    )

    parser.add_argument(
        "--test-rows",
        type=int,
        default=5000
    )

    parser.add_argument(
        "--contamination",
        type=float,
        default=0.10
    )

    args = parser.parse_args()

    if not 0 < args.contamination <= 0.5:
        parser.error(
            "Contamination must be between 0 and 0.5."
        )

    print("=" * 55)
    print("CYBERSENTINEL - UNSW-NB15 TRAINING")
    print("=" * 55)

    # Dataset loading
    train_df = load_dataset(
        TRAIN_FILE,
        args.train_rows,
        42
    )

    test_df = load_dataset(
        TEST_FILE,
        args.test_rows,
        43
    )

    # Labels are reserved for evaluation.
    # They are not passed into the model.

    y_test = pd.to_numeric(
        test_df["label"],
        errors="raise"
    ).astype(int).to_numpy()

    if not np.isin(y_test, [0, 1]).all():
        raise ValueError(
            "Labels must be binary: 0 or 1."
        )

    # Preprocessing
    transformer, X_train, X_test, numeric_columns = (
        preprocess_data(train_df, test_df)
    )

    # -------------------------------------------------
    # ISOLATION FOREST: ORIGINAL FEATURES
    # -------------------------------------------------

    print("\nTraining Isolation Forest on original features...")

    model_original = IsolationForest(
        n_estimators=120,
        contamination=args.contamination,
        random_state=42,
        n_jobs=-1
    )

    model_original.fit(X_train)

    original_predictions, original_scores, original_metrics = (
        evaluate_model(
            model_original,
            X_test,
            y_test
        )
    )

    # -------------------------------------------------
    # PCA DIMENSIONALITY REDUCTION
    # -------------------------------------------------

    print("\nApplying PCA dimensionality reduction...")

    pca = PCA(
        n_components=0.95,
        svd_solver="full",
        random_state=42
    )

    X_train_pca = pca.fit_transform(X_train)
    X_test_pca = pca.transform(X_test)

    print("Original dimensions:", X_train.shape[1])
    print("Reduced dimensions:", X_train_pca.shape[1])

    # -------------------------------------------------
    # ISOLATION FOREST: PCA FEATURES
    # -------------------------------------------------

    print("\nTraining Isolation Forest on PCA features...")

    model_pca = IsolationForest(
        n_estimators=120,
        contamination=args.contamination,
        random_state=42,
        n_jobs=-1
    )

    model_pca.fit(X_train_pca)

    pca_predictions, pca_scores, pca_metrics = (
        evaluate_model(
            model_pca,
            X_test_pca,
            y_test
        )
    )

    # -------------------------------------------------
    # 2D PCA FOR VISUALIZATION
    # -------------------------------------------------

    print("\nGenerating 2D PCA visualization data...")

    visual_pca = PCA(
        n_components=2,
        random_state=42
    )

    X_train_visual = visual_pca.fit_transform(X_train)
    X_test_visual = visual_pca.transform(X_test)

    # DBSCAN
    dbscan_results = perform_dbscan(
        X_train_visual
    )

    # -------------------------------------------------
    # SAVE PREDICTIONS
    # -------------------------------------------------

    predictions_df = test_df.copy()

    predictions_df["pc1"] = X_test_visual[:, 0]
    predictions_df["pc2"] = X_test_visual[:, 1]

    predictions_df["predicted_anomaly"] = (
        pca_predictions
    )

    predictions_df["actual_attack"] = y_test

    predictions_df["anomaly_score"] = (
        pca_scores
    )

    selected_columns = [
        "pc1",
        "pc2",
        "predicted_anomaly",
        "actual_attack",
        "anomaly_score",
        "proto",
        "service",
        "state",
        "dur",
        "sbytes",
        "dbytes",
        "attack_cat"
    ]

    selected_columns = [
        col for col in selected_columns
        if col in predictions_df.columns
    ]

    predictions_df[selected_columns].sample(
        n=min(1000, len(predictions_df)),
        random_state=42
    ).to_csv(
        PREDICTION_FILE,
        index=False
    )

    # -------------------------------------------------
    # SAVE EVALUATION REPORT
    # -------------------------------------------------

    report = {
        "dataset": "UNSW-NB15",
        "train_rows_used": len(train_df),
        "test_rows_used": len(test_df),
        "input_features": X_train.shape[1],
        "pca_components_95pct": int(
            pca.n_components_
        ),
        "pca_retained_variance": float(
            pca.explained_variance_ratio_.sum()
        ),
        "test_attacks": int(y_test.sum()),
        "test_normal": int((y_test == 0).sum()),
        "contamination": args.contamination,
        "raw_isolation_forest": original_metrics,
        "pca_isolation_forest": pca_metrics,
        "dbscan": dbscan_results,
        "notice": (
            "Offline UNSW-NB15 dataset experiment. "
            "Training is unsupervised; labels are "
            "used only for evaluation. "
            "Training data may contain attacks."
        )
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    # -------------------------------------------------
    # SAVE TRAINED MODELS
    # -------------------------------------------------

    joblib.dump(
        {
            "transformer": transformer,
            "numeric_columns": numeric_columns,
            "raw_isolation_forest": model_original,
            "pca": pca,
            "visual_pca": visual_pca,
            "pca_isolation_forest": model_pca
        },
        MODEL_FILE
    )

    print("\n" + "=" * 55)
    print("TRAINING COMPLETE")
    print("=" * 55)

    print("\nOriginal Isolation Forest:")
    print(json.dumps(original_metrics, indent=4))

    print("\nPCA Isolation Forest:")
    print(json.dumps(pca_metrics, indent=4))

    print("\nDBSCAN:")
    print(json.dumps(dbscan_results, indent=4))

    print("\nSaved files:")
    print(MODEL_FILE)
    print(REPORT_FILE)
    print(PREDICTION_FILE)

    print("\nCyberSentinel training finished successfully!")


if __name__ == "__main__":
    main()
