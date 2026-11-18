
import csv
import json

from fastapi import APIRouter, HTTPException, Query

from app.config import MODELS_DIR, PROCESSED_DIR


router = APIRouter(
    prefix="/api/dataset",
    tags=["Real Dataset Lab"]
)

REPORT_FILE = MODELS_DIR / "unsw_nb15_report.json"

SAMPLE_FILE = (
    PROCESSED_DIR / "unsw_nb15_predictions.csv"
)


@router.get("/report")
def get_report():

    if not REPORT_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Train the UNSW-NB15 model first."
        )

    with open(REPORT_FILE, "r", encoding="utf-8") as file:
        report = json.load(file)

    return report


@router.get("/samples")
def get_samples(
    limit: int = Query(default=700, ge=1, le=1000)
):

    if not SAMPLE_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Prediction CSV not found."
        )

    results = []

    with open(
        SAMPLE_FILE,
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            results.append({
                "pc1": float(row["pc1"]),
                "pc2": float(row["pc2"]),
                "predicted_anomaly": bool(
                    int(row["predicted_anomaly"])
                ),
                "actual_attack": bool(
                    int(row["actual_attack"])
                ),
                "anomaly_score": float(
                    row["anomaly_score"]
                ),
                "proto": row.get("proto", ""),
                "service": row.get("service", ""),
                "attack_cat": row.get("attack_cat", "")
            })

            if len(results) >= limit:
                break

    return results
