
"""Live capture, local baseline training, scoring and saved snapshots."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.capture.packet_capture import capture_service

from app.capture.live_ml import (
    train_baseline,
    score_live_flows
)

from app.database.history_store import save_analysis


router = APIRouter(
    prefix="/api/live",
    tags=["Live Monitoring"]
)


class StartCapture(BaseModel):
    interface: str | None = None


def full_status():
    snapshot = capture_service.status()

    session = snapshot.get("started_at")

    try:
        snapshot["ml"] = score_live_flows(
            capture_service.model_flows(),
            session
        )

    except Exception as exc:
        snapshot["ml"] = {
            "state": "error",
            "trained": False,
            "message": str(exc),
            "anomalies": [],
            "flagged_flows": 0,
            "scored_flows": 0
        }

    seconds = max(
        1,
        int(snapshot.get("elapsed_seconds", 0))
    )

    snapshot["average_packets_per_second"] = round(
        snapshot["total_packets"] / seconds,
        2
    )

    snapshot["average_bytes_per_second"] = round(
        snapshot["total_bytes"] / seconds,
        2
    )

    return snapshot


@router.get("/interfaces")
def interfaces():
    try:
        return capture_service.interfaces()

    except Exception as exc:
        raise HTTPException(
            503,
            f"Cannot list interfaces: {exc}"
        ) from exc


@router.get("/status")
def status():
    return full_status()


@router.post("/start")
def start(payload: StartCapture):
    try:
        capture_service.start(
            payload.interface
        )

        return full_status()

    except ValueError as exc:
        raise HTTPException(
            409,
            str(exc)
        ) from exc

    except Exception as exc:
        raise HTTPException(
            503,
            f"Capture could not start: {exc}"
        ) from exc


@router.post("/stop")
def stop():
    capture_service.stop()

    return full_status()


@router.post("/model/train")
def train_live_model():
    snapshot = capture_service.status()

    if (
        snapshot.get("running")
        or snapshot.get("stopping")
    ):
        raise HTTPException(
            409,
            "Stop capture before training the baseline."
        )

    if snapshot.get("started_at") is None:
        raise HTTPException(
            409,
            "Capture ordinary network traffic first."
        )

    try:
        return train_baseline(
            capture_service.model_flows(),
            snapshot["started_at"]
        )

    except ValueError as exc:
        raise HTTPException(
            422,
            str(exc)
        ) from exc


@router.post("/save")
def save_capture():
    snapshot = full_status()

    if not snapshot.get("started_at"):
        raise HTTPException(
            409,
            "Start a capture session before saving."
        )

    if int(snapshot.get("total_packets", 0)) < 1:
        raise HTTPException(
            409,
            "No packets have been captured yet."
        )

    live = {
        "captured_at": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),

        "interface": snapshot.get("interface"),
        "started_at": snapshot.get("started_at"),

        "elapsed_seconds": int(
            snapshot["elapsed_seconds"]
        ),

        "total_packets": int(
            snapshot["total_packets"]
        ),

        "total_bytes": int(
            snapshot["total_bytes"]
        ),

        "packets_per_second": float(
            snapshot["packets_per_second"]
        ),

        "bytes_per_second": float(
            snapshot["bytes_per_second"]
        ),

        "average_packets_per_second": float(
            snapshot["average_packets_per_second"]
        ),

        "average_bytes_per_second": float(
            snapshot["average_bytes_per_second"]
        ),

        "active_flows": int(
            snapshot["active_flows"]
        ),

        "protocols": snapshot["protocols"],
        "timeline": snapshot["timeline"],
        "flows": snapshot["flows"],
        "ml": snapshot["ml"],

        "flow_scope": (
            "Up to 30 top-volume directed flows; "
            "no packet payloads stored."
        )
    }

    result = {
        "analysis_type": "live_capture",

        "source": (
            "Live Capture - "
            f"{snapshot.get('interface') or 'default interface'}"
        ),

        "rows_analyzed": live["total_packets"],

        # These fields belong to the offline ML models.
        "flagged_original": 0,
        "flagged_pca": 0,

        "has_labels": False,
        "original_metrics": None,
        "pca_metrics": None,

        "encoded_features": None,
        "pca_features": None,

        "protocol_distribution": [
            {
                "name": item["name"],
                "value": item["packets"]
            }
            for item in live["protocols"]
        ],

        "rows": [],

        "recommendations": [
            (
                "Review flows flagged as unusual; "
                "outlier detection alone does not "
                "prove an attack."
            ),
            (
                "Compare activity over time and check "
                "network logs if spikes persist."
            ),
            (
                "Captured traffic is a local metadata-only "
                "snapshot, not complete network forensics."
            )
        ],

        "live": live,

        "note": (
            "Separate live-flow baseline; "
            "UNSW-NB15 classifier is not used "
            "on captured packets."
        )
    }

    saved = save_analysis(result)

    run_id = saved["history_id"]

    return {
        "history_id": run_id,
        "created_at": saved["created_at"],
        "source": saved["source"],

        "captured_packets": live["total_packets"],
        "captured_bytes": live["total_bytes"],

        "report_url": (
            f"/api/history/runs/{run_id}/report.pdf"
        ),

        "csv_url": (
            f"/api/history/runs/{run_id}/flows.csv"
        )
    }
