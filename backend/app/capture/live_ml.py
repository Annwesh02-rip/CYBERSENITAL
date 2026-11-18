
"""
Separate live-flow anomaly detection baseline.

This model does not use the UNSW-NB15 feature set.

Train with authorized, ordinary network traffic.
Results are unsupervised outlier flags,
not confirmed attacks or measured accuracy.
"""

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = (
    ROOT / "models" / "live_flow_baseline.joblib"
)

MIN_BASELINE_FLOWS = 25


def eligible(flows):
    return [
        flow
        for flow in flows
        if int(flow.get("packets", 0)) >= 2
    ]


def feature_matrix(flows):
    """
    Nine metadata-derived features.

    IP addresses are not used as ML inputs.
    """

    rows = []

    for flow in flows:
        packets = max(
            1,
            int(flow["packets"])
        )

        size = max(
            0,
            float(flow["bytes"])
        )

        duration = max(
            0.5,
            float(flow["last_seen_epoch"])
            - float(flow["first_seen_epoch"])
        )

        protocol = str(
            flow["protocol"]
        ).upper()

        rows.append([
            np.log1p(packets),
            np.log1p(size),
            np.log1p(duration),
            np.log1p(size / packets),
            np.log1p(packets / duration),
            np.log1p(size / duration),
            float(protocol == "TCP"),
            float(protocol == "UDP"),
            float(
                protocol not in {"TCP", "UDP"}
            )
        ])

    return np.asarray(
        rows,
        dtype=np.float64
    ).reshape(-1, 9)


def load_baseline():
    if not MODEL_PATH.is_file():
        return None

    # Load only locally generated trusted models.
    return joblib.load(MODEL_PATH)


def train_baseline(flows, session_id):
    samples = eligible(flows)

    if len(samples) < MIN_BASELINE_FLOWS:
        raise ValueError(
            f"Need at least {MIN_BASELINE_FLOWS} "
            f"flows with >=2 packets to train; "
            f"currently {len(samples)}. "
            "Capture more ordinary traffic."
        )

    matrix = feature_matrix(samples)

    scaler = StandardScaler()

    scaled = scaler.fit_transform(matrix)

    pca = PCA(
        n_components=0.95,
        svd_solver="full"
    )

    reduced = pca.fit_transform(scaled)

    forest = IsolationForest(
        n_estimators=100,
        contamination=0.10,
        random_state=42,
        n_jobs=-1
    )

    forest.fit(reduced)

    artifact = {
        "scaler": scaler,
        "pca": pca,
        "model": forest,
        "trained_session_id": session_id,

        "trained_at": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),

        "training_flows": len(samples),
        "input_dimensions": matrix.shape[1],
        "pca_dimensions": reduced.shape[1]
    }

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        artifact,
        MODEL_PATH
    )

    return {
        "trained": True,
        "training_flows": len(samples),
        "pca_dimensions": int(
            reduced.shape[1]
        ),
        "trained_at": artifact["trained_at"],
        "next_step": (
            "Start a NEW capture session "
            "to score live flows."
        )
    }


def score_live_flows(flows, session_id):
    artifact = load_baseline()

    result = {
        "trained": artifact is not None,
        "state": "not_trained",
        "training_flows": 0,
        "eligible_flows": len(eligible(flows)),
        "scored_flows": 0,
        "flagged_flows": 0,
        "anomalies": [],
        "trained_at": None,
        "pca_dimensions": None,

        "message": (
            "Capture ordinary traffic, stop, "
            "and click Train Live Baseline."
        )
    }

    if artifact is None:
        return result

    result["training_flows"] = int(
        artifact["training_flows"]
    )

    result["trained_at"] = artifact["trained_at"]

    result["pca_dimensions"] = int(
        artifact["pca_dimensions"]
    )

    if not session_id:
        result["state"] = "awaiting_capture"
        result["message"] = (
            "Start a capture session to detect "
            "unusual live flows."
        )

        return result

    # Do not evaluate the same session
    # used to train the baseline.
    if session_id == artifact["trained_session_id"]:
        result["state"] = "baseline_session"

        result["message"] = (
            "Baseline trained. Start a NEW "
            "capture session before scoring."
        )

        return result

    samples = eligible(flows)

    if not samples:
        result["state"] = "collecting"

        result["message"] = (
            "Waiting for live flows "
            "with at least two packets."
        )

        return result

    matrix = feature_matrix(samples)

    transformed = artifact["scaler"].transform(
        matrix
    )

    reduced = artifact["pca"].transform(
        transformed
    )

    model = artifact["model"]

    predictions = (
        model.predict(reduced) == -1
    )

    unusualness = -model.decision_function(
        reduced
    )

    anomalies = []

    for index, (flow, flagged) in enumerate(
        zip(samples, predictions)
    ):
        if flagged:
            anomalies.append({
                "source": flow["source"],
                "destination": flow["destination"],

                "source_port": flow.get(
                    "source_port"
                ),

                "destination_port": flow.get(
                    "destination_port"
                ),

                "protocol": flow["protocol"],
                "packets": int(flow["packets"]),
                "bytes": int(flow["bytes"]),

                "score": round(
                    float(unusualness[index]),
                    5
                )
            })

    anomalies.sort(
        key=lambda flow: flow["score"],
        reverse=True
    )

    result.update({
        "state": "scoring",
        "scored_flows": len(samples),
        "flagged_flows": len(anomalies),
        "anomalies": anomalies[:20],

        "message": (
            "Outlier flags are not verified "
            "security attacks. No labels or "
            "measured accuracy are available."
        )
    })

    return result
