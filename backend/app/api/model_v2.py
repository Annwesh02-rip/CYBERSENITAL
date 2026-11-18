
"""V2-only UNSW-NB15 inference, history and report downloads."""

import csv
import io
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile,
)

from fastapi.responses import StreamingResponse

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.database.history_store import (
    get_analysis,
    save_analysis,
)

from app.api.v2_report import create_v2_report_pdf


router = APIRouter(
    prefix="/api/model-v2",
    tags=["V2 Network Anomaly Detection"],
)

ROOT = Path(__file__).resolve().parents[3]

MODEL = (
    ROOT / "models"
    / "unsw_nb15_v2_pipeline.joblib"
)

REPORT = (
    ROOT / "models"
    / "unsw_nb15_v2_report.json"
)

TEST = (
    ROOT / "datasets" / "raw"
    / "UNSW_NB15_testing-set.csv"
)

MAX_ROWS = 5000
MAX_BYTES = 80 * 1024 * 1024


@lru_cache(maxsize=1)
def load_model():

    if not MODEL.is_file():
        raise HTTPException(
            404,
            "V2 model missing. Run scripts/train_unsw_v2.py.",
        )

    # Only load locally generated, trusted joblib models.
    return joblib.load(MODEL)


@router.get("/status")
def status():

    return {
        "model_ready": MODEL.is_file(),
        "report_ready": REPORT.is_file(),
        "sample_ready": TEST.is_file(),
        "active_model": "V2",
    }


@router.get("/report")
def training_report():

    if not REPORT.is_file():
        raise HTTPException(
            404,
            "V2 training report missing.",
        )

    return json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    )


def _metrics(labels, predictions, scores):

    if labels is None:
        return None

    y = np.asarray(
        labels,
        dtype=int,
    )

    p = np.asarray(
        predictions,
        dtype=int,
    )

    tn, fp, fn, tp = confusion_matrix(
        y,
        p,
        labels=[0, 1],
    ).ravel()

    result = {
        "accuracy": float(
            accuracy_score(y, p)
        ),

        "balanced_accuracy": float(
            balanced_accuracy_score(y, p)
        ),

        "precision": float(
            precision_score(
                y,
                p,
                zero_division=0,
            )
        ),

        "recall": float(
            recall_score(
                y,
                p,
                zero_division=0,
            )
        ),

        "f1": float(
            f1_score(
                y,
                p,
                zero_division=0,
            )
        ),

        "f2": float(
            fbeta_score(
                y,
                p,
                beta=2,
                zero_division=0,
            )
        ),

        "mcc": float(
            matthews_corrcoef(y, p)
        ),

        "false_positive_rate": float(
            fp / max(1, fp + tn)
        ),

        "confusion_matrix": [
            [int(tn), int(fp)],
            [int(fn), int(tp)],
        ],
    }

    if len(np.unique(y)) == 2:

        result["roc_auc"] = float(
            roc_auc_score(y, scores)
        )

        result["pr_auc"] = float(
            average_precision_score(
                y,
                scores,
            )
        )

    return result


def analyze_dataframe(
    df: pd.DataFrame,
    source: str,
    truncated: bool = False,
):

    if df.empty:
        raise HTTPException(
            400,
            "CSV has no records.",
        )

    model = load_model()

    numeric = list(
        model["numeric_columns"]
    )

    categorical = list(
        model["categorical_columns"]
    )

    missing = [
        col
        for col in numeric + categorical
        if col not in df.columns
    ]

    if missing:
        raise HTTPException(
            422,
            "Missing V2 dataset features: "
            + ", ".join(missing[:15]),
        )

    raw = df.reset_index(
        drop=True
    ).copy()

    features = raw[
        numeric + categorical
    ].copy()

    for name in numeric:

        features[name] = pd.to_numeric(
            features[name],
            errors="coerce",
        ).replace(
            [np.inf, -np.inf],
            np.nan,
        )

    for name in categorical:

        features[name] = (
            features[name]
            .fillna("unknown")
            .astype(str)
        )

    try:

        encoded = model[
            "transformer"
        ].transform(features)

        selected = str(
            model["selected_model_name"]
        )

        if selected == "numeric_only":

            count = int(
                model["number_of_numeric_columns"]
            )

            x = encoded[:, :count]

        elif selected == "full_features":

            x = encoded

        elif selected == "pca_95":

            x = model[
                "pca95"
            ].transform(encoded)

        elif selected == "pca_99":

            x = model[
                "pca99"
            ].transform(encoded)

        else:

            raise ValueError(
                "Unrecognized feature space: "
                + selected
            )

        scores = -model[
            "detector"
        ].score_samples(x)

        threshold = float(
            model["threshold"]
        )

        flags = (
            scores >= threshold
        ).astype(int)

        # PCA is a visualization only when the
        # selected model is numeric_only.

        projected = model[
            "pca95"
        ].transform(encoded)

    except Exception as exc:

        raise HTTPException(
            422,
            f"V2 inference failed: {exc}",
        ) from exc

    labels = None

    if "label" in raw:

        candidate = pd.to_numeric(
            raw["label"],
            errors="coerce",
        )

        if (
            candidate.notna().all()
            and candidate.isin([0, 1]).all()
        ):

            labels = candidate.to_numpy(
                dtype=int
            )

    def clean_text(value):
        return (
            ""
            if pd.isna(value)
            else str(value)
        )

    rows = []

    for i, record in raw.iterrows():

        rows.append({
            "row": i + 1,

            "proto": clean_text(
                record.get("proto", "")
            ),

            "service": clean_text(
                record.get("service", "")
            ),

            "state": clean_text(
                record.get("state", "")
            ),

            "pc1": float(
                projected[i, 0]
            ),

            "pc2": (
                float(projected[i, 1])
                if projected.shape[1] > 1
                else 0.0
            ),

            "anomaly_score": float(
                scores[i]
            ),

            "predicted_anomaly": bool(
                flags[i]
            ),

            "actual_attack": (
                int(labels[i])
                if labels is not None
                else None
            ),

            "attack_cat": clean_text(
                record.get("attack_cat", "")
            ),
        })

    counts = (
        raw["proto"]
        .fillna("unknown")
        .astype(str)
        .value_counts()
        .head(10)
    )

    return {
        "analysis_type": "v2_dataset",
        "model_version": "V2",

        "source": (
            "UNSW-NB15 V2 - " + source
        ),

        "rows_analyzed": len(rows),
        "truncated": bool(truncated),

        "selected_model": selected,
        "threshold": threshold,

        "encoded_features": int(
            encoded.shape[1]
        ),

        "model_input_dimensions": int(
            x.shape[1]
        ),

        "pca95_dimensions": int(
            projected.shape[1]
        ),

        "flagged": int(
            flags.sum()
        ),

        "has_labels": (
            labels is not None
        ),

        "metrics": _metrics(
            labels,
            flags,
            scores,
        ),

        "protocol_distribution": [
            {
                "name": str(name),
                "value": int(count),
            }
            for name, count
            in counts.items()
        ],

        "rows": rows,

        "recommendations": [
            (
                "Review high-scoring flows with "
                "network logs before treating "
                "them as attacks."
            ),
            (
                "PCA positions illustrate traffic "
                "structure; they do not drive "
                "numeric-only predictions."
            ),
            (
                "Outlier flags are not confirmed "
                "malicious activity."
            ),
        ],

        # Compatibility with existing history_store.
        # These fields do not represent V2 predictions.

        "flagged_original": 0,
        "flagged_pca": 0,

        "original_metrics": None,
        "pca_metrics": None,

        "note": (
            "V2 normal-only Isolation Forest "
            "with validation-calibrated threshold."
        ),
    }


def _maybe_save(result, save):

    if save:

        saved = save_analysis(result)

        run_id = int(
            saved["history_id"]
        )

        result = {
            **result,

            "history_id": run_id,

            "report_url": (
                f"/api/model-v2/history/"
                f"{run_id}/report.pdf"
            ),

            "csv_url": (
                f"/api/model-v2/history/"
                f"{run_id}/predictions.csv"
            ),
        }

    return result


@router.post("/sample")
def sample(
    rows: int = Query(
        1500,
        ge=100,
        le=MAX_ROWS,
    ),
    save: bool = True,
):

    if not TEST.is_file():
        raise HTTPException(
            404,
            "UNSW-NB15 testing CSV is missing.",
        )

    df = pd.read_csv(
        TEST,
        low_memory=False,
    )

    chosen = df.sample(
        n=min(rows, len(df)),
        random_state=43,
    ).reset_index(
        drop=True
    )

    result = analyze_dataframe(
        chosen,
        "built-in testing sample",
        len(df) > len(chosen),
    )

    return _maybe_save(
        result,
        save,
    )


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    save: bool = True,
):

    filename = Path(
        file.filename or ""
    ).name

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            400,
            "Upload a CSV file.",
        )

    content = await file.read(
        MAX_BYTES + 1
    )

    await file.close()

    if len(content) > MAX_BYTES:
        raise HTTPException(
            413,
            "CSV exceeds 80 MB limit.",
        )

    try:

        df = pd.read_csv(
            io.BytesIO(content),
            nrows=MAX_ROWS + 1,
            low_memory=False,
        )

    except (
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        UnicodeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            400,
            f"Cannot read CSV: {exc}",
        ) from exc

    truncated = (
        len(df) > MAX_ROWS
    )

    result = analyze_dataframe(
        df.head(MAX_ROWS),
        filename,
        truncated,
    )

    return _maybe_save(
        result,
        save,
    )


def _saved_v2(run_id: int):

    record = get_analysis(run_id)

    if record is None:
        raise HTTPException(
            404,
            "Saved analysis not found.",
        )

    if record.get("analysis_type") != "v2_dataset":
        raise HTTPException(
            400,
            "This entry is not a V2 dataset analysis.",
        )

    return record


@router.get(
    "/history/{run_id}/report.pdf"
)
def download_pdf(run_id: int):

    data = create_v2_report_pdf(
        _saved_v2(run_id)
    )

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",

        headers={
            "Content-Disposition": (
                "attachment; filename="
                f'"CyberSentinel_V2_{run_id}.pdf"'
            ),
        },
    )


@router.get(
    "/history/{run_id}/predictions.csv"
)
def download_csv(run_id: int):

    record = _saved_v2(run_id)

    output = io.StringIO(
        newline=""
    )

    columns = [
        "row",
        "proto",
        "service",
        "state",
        "pc1",
        "pc2",
        "anomaly_score",
        "predicted_anomaly",
        "actual_attack",
        "attack_cat",
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        extrasaction="ignore",
    )

    writer.writeheader()

    for row in record.get("rows", []):

        safe_row = {}

        for field in columns:

            value = row.get(
                field,
                "",
            )

            if (
                isinstance(value, str)
                and value.lstrip().startswith(
                    ("=", "+", "-", "@")
                )
            ):
                value = "'" + value

            safe_row[field] = value

        writer.writerow(
            safe_row
        )

    return StreamingResponse(
        io.BytesIO(
            output.getvalue().encode(
                "utf-8-sig"
            )
        ),

        media_type=(
            "text/csv; charset=utf-8"
        ),

        headers={
            "Content-Disposition": (
                "attachment; filename="
                f'"CyberSentinel_V2_{run_id}.csv"'
            ),
        },
    )
