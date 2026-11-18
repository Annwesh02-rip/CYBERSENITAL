
"""
CyberSentinel - Interactive Network Traffic Analysis API

Features:
- UNSW-NB15 CSV upload
- Built-in sample analysis
- Saved Isolation Forest inference
- PCA transformation
- Anomaly scores and predictions
- Optional classification evaluation
- Traffic analysis and recommendations
"""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile
)

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    average_precision_score
)


router = APIRouter(
    prefix="/api/inspection",
    tags=["Interactive Traffic Analysis"]
)

ROOT = Path(__file__).resolve().parents[3]

MODEL_FILE = (
    ROOT / "models" / "unsw_nb15_pipeline.joblib"
)

TEST_FILE = (
    ROOT / "datasets" / "raw"
    / "UNSW_NB15_testing-set.csv"
)

CATEGORICAL = ["proto", "service", "state"]

MAX_ROWS = 5000
MAX_UPLOAD_BYTES = 80 * 1024 * 1024


# --------------------------------------------------
# LOAD SAVED MACHINE LEARNING MODELS
# --------------------------------------------------

@lru_cache(maxsize=1)
def load_models():

    if not MODEL_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Trained model not found."
        )

    try:
        # Load only a trusted, locally trained model.
        return joblib.load(MODEL_FILE)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Model loading failed: {error}"
        ) from error


# --------------------------------------------------
# MODEL EVALUATION
# --------------------------------------------------

def calculate_metrics(labels, predictions, scores):

    if labels is None:
        return None

    results = {
        "accuracy": float(
            accuracy_score(labels, predictions)
        ),
        "precision": float(
            precision_score(
                labels,
                predictions,
                zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                labels,
                predictions,
                zero_division=0
            )
        ),
        "f1": float(
            f1_score(
                labels,
                predictions,
                zero_division=0
            )
        ),
        "confusion_matrix": confusion_matrix(
            labels,
            predictions,
            labels=[0, 1]
        ).tolist()
    }

    if len(np.unique(labels)) == 2:

        results["roc_auc"] = float(
            roc_auc_score(labels, scores)
        )

        results["pr_auc"] = float(
            average_precision_score(labels, scores)
        )

    return results


# --------------------------------------------------
# MAIN ANALYSIS FUNCTION
# --------------------------------------------------

def analyze_dataframe(
    dataframe,
    source,
    truncated=False
):

    if dataframe.empty:
        raise HTTPException(
            status_code=400,
            detail="Dataset is empty."
        )

    models = load_models()

    numeric_columns = models["numeric_columns"]

    required_columns = (
        numeric_columns + CATEGORICAL
    )

    missing = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                "Missing required UNSW-NB15 features: "
                + ", ".join(missing)
            )
        )

    df = dataframe.reset_index(drop=True).copy()

    X = df[required_columns].copy()

    # Clean numerical columns

    for column in numeric_columns:

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce"
        )

        X[column] = X[column].replace(
            [np.inf, -np.inf],
            np.nan
        )

    # Clean categorical columns

    for column in CATEGORICAL:

        X[column] = (
            X[column]
            .fillna("unknown")
            .astype(str)
        )

    # --------------------------------------------------
    # PREPROCESSING AND DIMENSIONALITY REDUCTION
    # --------------------------------------------------

    try:

        encoded = models["transformer"].transform(X)

        reduced = models["pca"].transform(encoded)

        visual = models["visual_pca"].transform(encoded)

        # Original Isolation Forest

        raw_model = models["raw_isolation_forest"]

        raw_predictions = (
            raw_model.predict(encoded) == -1
        ).astype(int)

        raw_scores = -raw_model.score_samples(encoded)

        # PCA Isolation Forest

        pca_model = models["pca_isolation_forest"]

        pca_predictions = (
            pca_model.predict(reduced) == -1
        ).astype(int)

        pca_scores = -pca_model.score_samples(reduced)

    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Analysis failed: {error}"
        ) from error

    # --------------------------------------------------
    # OPTIONAL GROUND TRUTH LABELS
    # --------------------------------------------------

    labels = None

    if "label" in df.columns:

        candidate = pd.to_numeric(
            df["label"],
            errors="coerce"
        )

        if (
            candidate.notna().all()
            and candidate.isin([0, 1]).all()
        ):
            labels = candidate.astype(int).to_numpy()

    raw_metrics = calculate_metrics(
        labels,
        raw_predictions,
        raw_scores
    )

    pca_metrics = calculate_metrics(
        labels,
        pca_predictions,
        pca_scores
    )

    # --------------------------------------------------
    # NETWORK TRAFFIC ANALYSIS
    # --------------------------------------------------

    def numeric_values(column):

        return (
            pd.to_numeric(
                df[column],
                errors="coerce"
            )
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
            .to_numpy(dtype=float)
        )

    sbytes = numeric_values("sbytes")
    dbytes = numeric_values("dbytes")
    duration = numeric_values("dur")

    total_bytes = sbytes + dbytes

    rates = total_bytes / np.maximum(
        duration,
        0.001
    )

    valid_rates = rates[duration >= 0.001]

    threshold = (
        float(np.percentile(valid_rates, 90))
        if len(valid_rates)
        else None
    )

    high_rate_count = (
        int(np.sum(
            (rates >= threshold)
            & (duration >= 0.001)
        ))
        if threshold is not None
        else 0
    )

    # --------------------------------------------------
    # PER-RECORD RESULTS
    # --------------------------------------------------

    records = []

    for i in range(len(df)):

        records.append({
            "row": i + 1,
            "proto": str(df.at[i, "proto"]),
            "service": str(df.at[i, "service"]),
            "state": str(df.at[i, "state"]),

            "duration": float(duration[i]),
            "sbytes": int(max(0, sbytes[i])),
            "dbytes": int(max(0, dbytes[i])),

            "rate_bytes_s": float(rates[i]),

            "pc1": float(visual[i, 0]),
            "pc2": float(visual[i, 1]),

            "raw_flag": bool(raw_predictions[i]),
            "pca_flag": bool(pca_predictions[i]),

            "raw_score": float(raw_scores[i]),
            "pca_score": float(pca_scores[i]),

            "actual_attack": (
                int(labels[i])
                if labels is not None
                else None
            ),

            "attack_cat": (
                str(df.at[i, "attack_cat"])
                if "attack_cat" in df.columns
                else None
            )
        })

    # --------------------------------------------------
    # PROTOCOL DISTRIBUTION
    # --------------------------------------------------

    counts = df["proto"].value_counts().head(8)

    protocol_distribution = [
        {
            "name": str(name),
            "value": int(count)
        }
        for name, count in counts.items()
    ]

    # --------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------

    recommendations = [
        "Investigate records flagged by Isolation Forest.",

        "Compare predictions before and after PCA.",

        "Inspect network protocol, service, duration "
        "and traffic volume for suspicious records.",

        "Flagged anomalies are not necessarily "
        "confirmed cyberattacks."
    ]

    if high_rate_count > 0:

        recommendations.append(
            f"{high_rate_count} records have "
            "high-throughput indicators. "
            "Investigate before concluding congestion."
        )

    # --------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------

    return {
        "source": source,
        "rows_analyzed": len(df),
        "truncated": truncated,

        "encoded_features": int(encoded.shape[1]),
        "pca_features": int(reduced.shape[1]),

        "flagged_original": int(raw_predictions.sum()),
        "flagged_pca": int(pca_predictions.sum()),

        "total_bytes": int(total_bytes.sum()),

        "high_rate_count": high_rate_count,
        "high_rate_threshold_bytes_s": threshold,

        "has_labels": labels is not None,

        "original_metrics": raw_metrics,
        "pca_metrics": pca_metrics,

        "protocol_distribution": protocol_distribution,

        "recommendations": recommendations,

        "rows": records,

        "note": (
            "Offline network traffic analysis using "
            "saved unsupervised models. "
            "Labels are used only for evaluation."
        )
    }


# --------------------------------------------------
# CHECK MODEL STATUS
# --------------------------------------------------

@router.get("/status")
def get_status():

    return {
        "model_ready": MODEL_FILE.exists(),
        "sample_ready": TEST_FILE.exists()
    }


# --------------------------------------------------
# ANALYZE BUILT-IN DATASET
# --------------------------------------------------

@router.post("/sample")
def analyze_sample(
    rows: int = Query(
        default=1500,
        ge=100,
        le=MAX_ROWS
    )
):

    if not TEST_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Testing dataset not found."
        )

    dataset = pd.read_csv(
        TEST_FILE,
        low_memory=False
    )

    if len(dataset) > rows:

        sample = dataset.sample(
            n=rows,
            random_state=43
        )

    else:
        sample = dataset

    return analyze_dataframe(
        sample,
        source="Built-in UNSW-NB15 testing sample",
        truncated=len(dataset) > rows
    )


# --------------------------------------------------
# ANALYZE UPLOADED CSV
# --------------------------------------------------

@router.post("/upload")
async def analyze_uploaded_csv(
    file: UploadFile = File(...)
):

    filename = Path(file.filename or "").name

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file."
        )

    contents = await file.read(
        MAX_UPLOAD_BYTES + 1
    )

    await file.close()

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="CSV exceeds the 80 MB limit."
        )

    try:

        dataset = pd.read_csv(
            BytesIO(contents),
            nrows=MAX_ROWS + 1,
            low_memory=False
        )

    except (
        ValueError,
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError
    ) as error:

        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV: {error}"
        ) from error

    truncated = len(dataset) > MAX_ROWS

    return analyze_dataframe(
        dataset.head(MAX_ROWS),
        source=filename,
        truncated=truncated
    )
