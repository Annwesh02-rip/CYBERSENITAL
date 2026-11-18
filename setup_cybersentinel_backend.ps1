# CyberSentinel backend starter: creates backend and training script source files.
# CAUTION: Re-running overwrites the listed source files in this folder.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Files = @{}

$Files['backend\app\__init__.py'] = @'
"""CyberSentinel backend package."""
'@

$Files['backend\app\analysis\__init__.py'] = @'
"""analysis package."""
'@

$Files['backend\app\analysis\anomaly_analysis.py'] = @'
from collections import Counter
from app.database.models import TrafficFlow


def summarize_flows(flows: list[TrafficFlow]) -> dict:
    anomalies = [f for f in flows if f.is_anomaly]
    protocols = Counter(flow.protocol for flow in flows)
    top_sources = Counter(flow.src_ip for flow in anomalies)
    return {
        "total_flows": len(flows),
        "anomaly_count": len(anomalies),
        "anomaly_rate": round(100 * len(anomalies) / len(flows), 2) if flows else 0,
        "total_bytes": sum(f.bytes for f in flows),
        "protocol_distribution": [
            {"name": proto, "value": count}
            for proto, count in protocols.most_common()
        ],
        "top_anomalous_sources": [
            {"ip": ip, "count": count} for ip, count in top_sources.most_common(5)
        ],
        "latest_timestamp": max((f.timestamp for f in flows), default=None),
    }
'@

$Files['backend\app\analysis\congestion_analysis.py'] = @'
import numpy as np
from app.database.models import TrafficFlow


def analyze_bursts(flows: list[TrafficFlow]) -> dict:
    """High throughput is a burst INDICATOR, not evidence of congestion."""
    if not flows:
        return {"threshold_bytes_per_second": 0, "high_throughput_flows": [], "note": "No data."}
    rates = np.array([f.bytes / max(f.duration, 0.001) for f in flows], dtype=float)
    threshold = float(np.percentile(rates, 90))
    indices = np.argsort(rates)[::-1][:10]
    return {
        "threshold_bytes_per_second": round(threshold, 2),
        "high_throughput_flows": [
            {"id": flows[int(i)].id, "src_ip": flows[int(i)].src_ip,
             "dst_ip": flows[int(i)].dst_ip,
             "bytes_per_second": round(float(rates[int(i)]), 2),
             "is_anomaly": flows[int(i)].is_anomaly}
            for i in indices if rates[int(i)] >= threshold
        ],
        "note": "Top-decile flow rates indicate bursts only. Confirm congestion using interface capacity, delay, drops and utilization.",
    }
'@

$Files['backend\app\analysis\optimization.py'] = @'
from app.database.models import TrafficFlow


def recommendations(flows: list[TrafficFlow]) -> list[dict]:
    if not flows:
        return [{"priority": "Info", "title": "Load a dataset", "detail": "Run the preprocessing and training scripts to populate the dashboard."}]
    alerts = sum(f.is_anomaly for f in flows)
    anomaly_pct = 100 * alerts / len(flows)
    advice = []
    if alerts:
        advice.append({
            "priority": "High" if anomaly_pct >= 10 else "Medium",
            "title": "Review flagged network flows",
            "detail": f"{alerts} of {len(flows)} flows were flagged ({anomaly_pct:.1f}%). Investigate source addresses, destinations and ports before making security decisions.",
        })
    risky_ports = sum(f.dst_port in (21, 22, 23, 3389, 445) for f in flows)
    if risky_ports:
        advice.append({
            "priority": "Medium", "title": "Validate exposure of administrative services",
            "detail": f"{risky_ports} flows target selected administration/file-sharing ports. Check access controls and expected usage; port use alone does not establish malicious activity.",
        })
    advice.append({
        "priority": "Info", "title": "Measure link health before tuning throughput",
        "detail": "Correlate flow bursts with measured interface utilization, latency and packet loss. No changes are applied automatically.",
    })
    advice.append({
        "priority": "Info", "title": "Validate on a real labeled test set",
        "detail": "Synthetic-demo metrics are not representative of operational detection accuracy. Test using a separate held-out public network dataset.",
    })
    return advice
'@

$Files['backend\app\api\__init__.py'] = @'
"""api package."""
'@

$Files['backend\app\api\analysis.py'] = @'
from fastapi import APIRouter, Query
from sqlalchemy import select
from app.analysis.congestion_analysis import analyze_bursts
from app.analysis.optimization import recommendations
from app.database.connection import SessionLocal
from app.database.models import TrafficFlow

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/projection")
def projection(limit: int = Query(500, ge=1, le=2000)):
    with SessionLocal() as db:
        rows = db.scalars(select(TrafficFlow).order_by(TrafficFlow.id).limit(limit)).all()
    return [{"id": r.id, "x": r.pc1, "y": r.pc2, "anomaly": r.is_anomaly} for r in rows]


@router.get("/congestion")
def congestion():
    with SessionLocal() as db:
        rows = db.scalars(select(TrafficFlow)).all()
    return analyze_bursts(list(rows))


@router.get("/optimization")
def optimization():
    with SessionLocal() as db:
        rows = db.scalars(select(TrafficFlow)).all()
    return recommendations(list(rows))
'@

$Files['backend\app\api\dashboard.py'] = @'
import json
from fastapi import APIRouter
from app.config import REPORT_PATH
from sqlalchemy import select
from app.analysis.anomaly_analysis import summarize_flows
from app.database.connection import SessionLocal
from app.database.models import TrafficFlow

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
def summary():
    with SessionLocal() as db:
        rows = db.scalars(select(TrafficFlow)).all()
        result = summarize_flows(list(rows))
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.exists() else {}
        source = report.get("source", "")
        result["data_mode"] = (
            "Synthetic demo dataset / offline analysis" if not source or "demo" in source
            else "Supplied dataset / offline analysis"
        )
        return result
'@

$Files['backend\app\api\traffic.py'] = @'
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Query
from sqlalchemy import select
from app.database.connection import SessionLocal
from app.database.models import TrafficFlow

router = APIRouter(prefix="/api/traffic", tags=["Traffic"])


def as_dict(row: TrafficFlow) -> dict:
    return {
        "id": row.id, "timestamp": row.timestamp, "src_ip": row.src_ip,
        "dst_ip": row.dst_ip, "protocol": row.protocol,
        "src_port": row.src_port, "dst_port": row.dst_port,
        "duration": row.duration, "packets": row.packets, "bytes": row.bytes,
        "anomaly_score": row.anomaly_score, "is_anomaly": row.is_anomaly,
        "pc1": row.pc1, "pc2": row.pc2,
    }


@router.get("/flows")
def flows(limit: int = Query(100, ge=1, le=1000), anomalies_only: bool = False):
    with SessionLocal() as db:
        query = select(TrafficFlow)
        if anomalies_only:
            query = query.where(TrafficFlow.is_anomaly.is_(True))
        rows = db.scalars(query.order_by(TrafficFlow.timestamp.desc()).limit(limit)).all()
        return [as_dict(row) for row in rows]


@router.get("/trends")
def trends():
    with SessionLocal() as db:
        rows = db.scalars(select(TrafficFlow).order_by(TrafficFlow.timestamp)).all()
    counts = defaultdict(lambda: {"flows": 0, "anomalies": 0, "bytes": 0})
    for row in rows:
        hour = datetime.fromisoformat(row.timestamp).strftime("%m-%d %H:00")
        counts[hour]["flows"] += 1
        counts[hour]["anomalies"] += int(row.is_anomaly)
        counts[hour]["bytes"] += row.bytes
    return [{"hour": hour, **values} for hour, values in sorted(counts.items())]
'@

$Files['backend\app\capture\__init__.py'] = @'
"""capture package."""
'@

$Files['backend\app\capture\flow_extractor.py'] = @'
from collections import defaultdict
from datetime import datetime, timezone


def packets_to_flows(packets) -> list[dict]:
    """Aggregate IPv4 TCP/UDP/ICMP packets into unidirectional 5-tuple flows."""
    from scapy.layers.inet import IP, TCP, UDP, ICMP

    groups = defaultdict(list)
    for packet in packets:
        if IP not in packet:
            continue
        ip = packet[IP]
        protocol = "TCP" if TCP in packet else "UDP" if UDP in packet else "ICMP" if ICMP in packet else "OTHER"
        transport = packet[TCP] if TCP in packet else packet[UDP] if UDP in packet else None
        sport = int(transport.sport) if transport is not None else 0
        dport = int(transport.dport) if transport is not None else 0
        key = (ip.src, ip.dst, protocol, sport, dport)
        groups[key].append(packet)

    flows = []
    for key, members in groups.items():
        times = [float(p.time) for p in members]
        duration = max(max(times) - min(times), 0.001)
        flows.append({
            "timestamp": datetime.fromtimestamp(min(times), tz=timezone.utc).isoformat(),
            "src_ip": key[0], "dst_ip": key[1], "protocol": key[2],
            "src_port": key[3], "dst_port": key[4],
            "duration": round(duration, 4), "packets": len(members),
            "bytes": sum(len(p) for p in members),
        })
    return flows
'@

$Files['backend\app\capture\packet_capture.py'] = @'
def capture_packets(interface: str | None = None, count: int = 100, timeout: int = 15):
    """Explicit, local-only capture. Never starts automatically.

    Requires Scapy, capture privileges and usually Npcap on Windows.
    Capture only on interfaces and networks you are authorized to monitor.
    """
    if not 1 <= count <= 5000:
        raise ValueError("count must be between 1 and 5000")
    if not 1 <= timeout <= 120:
        raise ValueError("timeout must be between 1 and 120 seconds")
    from scapy.all import sniff

    return sniff(iface=interface, count=count, timeout=timeout, store=True)
'@

$Files['backend\app\config.py'] = @'
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = PROJECT_ROOT / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DB_PATH = DATASETS_DIR / "cybersentinel.db"
MODEL_PATH = MODELS_DIR / "cybersentinel.joblib"
REPORT_PATH = MODELS_DIR / "training_report.json"

for directory in (RAW_DIR, PROCESSED_DIR, MODELS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
'@

$Files['backend\app\database\__init__.py'] = @'
"""database package."""
'@

$Files['backend\app\database\connection.py'] = @'
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_database() -> None:
    from app.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
'@

$Files['backend\app\database\models.py'] = @'
from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.connection import Base


class TrafficFlow(Base):
    __tablename__ = "traffic_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True)
    src_ip: Mapped[str] = mapped_column(String(64))
    dst_ip: Mapped[str] = mapped_column(String(64))
    protocol: Mapped[str] = mapped_column(String(15))
    src_port: Mapped[int] = mapped_column(Integer)
    dst_port: Mapped[int] = mapped_column(Integer)
    duration: Mapped[float] = mapped_column(Float)
    packets: Mapped[int] = mapped_column(Integer)
    bytes: Mapped[int] = mapped_column(Integer)
    anomaly_score: Mapped[float] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, index=True)
    pc1: Mapped[float] = mapped_column(Float)
    pc2: Mapped[float] = mapped_column(Float)
    label: Mapped[int | None] = mapped_column(Integer, nullable=True)
'@

$Files['backend\app\main.py'] = @'
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import init_database
from app.api import dashboard, traffic, analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(title="CyberSentinel API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(dashboard.router)
app.include_router(traffic.router)
app.include_router(analysis.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "CyberSentinel"}
'@

$Files['backend\app\ml\__init__.py'] = @'
"""ml package."""
'@

$Files['backend\app\ml\clustering.py'] = @'
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest


def fit_isolation_forest(features, contamination: float = 0.10):
    detector = IsolationForest(
        n_estimators=150, contamination=contamination, random_state=42
    )
    detector.fit(features)
    return detector


def dbscan_summary(projected_features, eps: float = 0.85, min_samples: int = 6):
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(projected_features)
    return {
        "clusters": int(len(set(labels) - {-1})),
        "noise_points": int(np.sum(labels == -1)),
    }
'@

$Files['backend\app\ml\dimensionality_reduction.py'] = @'
from sklearn.decomposition import PCA


def fit_pca(scaled_features, n_components: int = 2):
    pca = PCA(n_components=n_components, random_state=42)
    projected = pca.fit_transform(scaled_features)
    return pca, projected
'@

$Files['backend\app\ml\evaluation.py'] = @'
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def evaluate_predictions(true_labels, predicted_anomaly):
    """Use labels ONLY for post-training evaluation; 1 denotes an anomaly."""
    return {
        "accuracy": round(float(accuracy_score(true_labels, predicted_anomaly)), 4),
        "precision": round(float(precision_score(true_labels, predicted_anomaly, zero_division=0)), 4),
        "recall": round(float(recall_score(true_labels, predicted_anomaly, zero_division=0)), 4),
        "f1": round(float(f1_score(true_labels, predicted_anomaly, zero_division=0)), 4),
    }
'@

$Files['backend\app\preprocessing\__init__.py'] = @'
"""preprocessing package."""
'@

$Files['backend\app\preprocessing\cleaner.py'] = @'
import pandas as pd

REQUIRED_COLUMNS = [
    "timestamp", "src_ip", "dst_ip", "protocol", "src_port",
    "dst_port", "duration", "packets", "bytes",
]
NUMERIC_COLUMNS = ["src_port", "dst_port", "duration", "packets", "bytes"]


def clean_traffic(df: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    cleaned = df.copy()
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], errors="coerce", utc=True)
    for col in NUMERIC_COLUMNS:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    cleaned = cleaned.dropna(subset=REQUIRED_COLUMNS)
    cleaned = cleaned[
        (cleaned["duration"] >= 0)
        & (cleaned["packets"] >= 1)
        & (cleaned["bytes"] >= 0)
        & (cleaned["src_port"].between(0, 65535))
        & (cleaned["dst_port"].between(0, 65535))
    ].copy()
    cleaned["protocol"] = cleaned["protocol"].astype(str).str.upper().str.strip()
    cleaned["src_port"] = cleaned["src_port"].astype(int)
    cleaned["dst_port"] = cleaned["dst_port"].astype(int)
    cleaned["packets"] = cleaned["packets"].astype(int)
    cleaned["bytes"] = cleaned["bytes"].astype(int)
    if "label" in cleaned.columns:
        cleaned["label"] = pd.to_numeric(cleaned["label"], errors="coerce").fillna(0).astype(int)
    return cleaned.sort_values("timestamp").reset_index(drop=True)
'@

$Files['backend\app\preprocessing\feature_engineering.py'] = @'
import numpy as np
import pandas as pd

MODEL_FEATURES = [
    "duration", "src_port", "dst_port", "packets", "bytes",
    "packets_per_second", "bytes_per_second", "avg_packet_size",
    "proto_tcp", "proto_udp", "proto_icmp", "proto_other",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Produce exactly the same numeric feature order at training and inference."""
    result = pd.DataFrame(index=df.index)
    for col in ("duration", "src_port", "dst_port", "packets", "bytes"):
        result[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)
    safe_duration = np.maximum(result["duration"].to_numpy(), 0.001)
    safe_packets = np.maximum(result["packets"].to_numpy(), 1)
    result["packets_per_second"] = result["packets"].to_numpy() / safe_duration
    result["bytes_per_second"] = result["bytes"].to_numpy() / safe_duration
    result["avg_packet_size"] = result["bytes"].to_numpy() / safe_packets
    protocol = df["protocol"].fillna("OTHER").astype(str).str.upper()
    for name in ("TCP", "UDP", "ICMP"):
        result[f"proto_{name.lower()}"] = (protocol == name).astype(float)
    result["proto_other"] = (~protocol.isin(["TCP", "UDP", "ICMP"])).astype(float)
    return result[MODEL_FEATURES].replace([np.inf, -np.inf], 0).fillna(0)
'@

$Files['backend\requirements.txt'] = @'
fastapi>=0.115,<1
uvicorn[standard]>=0.30,<1
pandas>=2.2,<4
numpy>=2.0,<3
scikit-learn>=1.5,<2
sqlalchemy>=2.0,<3
joblib>=1.4,<2
scapy>=2.6,<3
pytest>=8,<10
httpx>=0.27,<1
'@

$Files['backend\tests\test_api.py'] = @'
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app


def test_health_and_api_shapes():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        res = client.get("/api/dashboard/summary")
        assert res.status_code == 200
        assert "total_flows" in res.json()
        assert client.get("/api/traffic/flows?limit=5").status_code == 200
'@

$Files['backend\tests\test_cleaner.py'] = @'
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
'@

$Files['scripts\preprocess.py'] = @'
"""Build deterministic synthetic demo traffic, or clean a user-supplied CSV.

Run from project root: python scripts/preprocess.py
Or: python scripts/preprocess.py --input datasets/raw/traffic.csv
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import RAW_DIR, PROCESSED_DIR  # noqa: E402
from app.preprocessing.cleaner import clean_traffic  # noqa: E402


def make_demo_dataset(normal_count: int = 450, anomaly_count: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=16)
    for i in range(normal_count + anomaly_count):
        abnormal = i >= normal_count
        protocol = str(rng.choice(["TCP", "UDP", "ICMP"], p=[0.78, 0.18, 0.04]))
        if abnormal:
            duration = float(rng.uniform(0.01, 3.0))
            packets = int(rng.integers(1200, 11000))
            bytes_count = int(packets * rng.integers(550, 1400))
            dst_port = int(rng.choice([22, 23, 445, 3389, 8080, 6553]))
            src_ip = f"10.1.9.{int(rng.integers(1, 50))}"
        else:
            duration = float(rng.uniform(0.5, 35.0))
            packets = int(rng.integers(2, 240))
            bytes_count = int(packets * rng.integers(60, 950))
            dst_port = int(rng.choice([53, 80, 443, 22, 123]))
            src_ip = f"10.0.0.{int(rng.integers(1, 240))}"
        rows.append({
            "timestamp": (start + timedelta(seconds=round(i * 90 + int(rng.integers(0, 30))))).isoformat(),
            "src_ip": src_ip, "dst_ip": f"10.0.2.{int(rng.integers(1, 200))}",
            "protocol": protocol, "src_port": int(rng.integers(1024, 65535)),
            "dst_port": dst_port, "duration": round(duration, 4),
            "packets": packets, "bytes": bytes_count, "label": int(abnormal),
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="CSV with CyberSentinel traffic schema")
    args = parser.parse_args()
    if args.input:
        source = Path(args.input)
        if not source.is_absolute():
            source = ROOT / source
        df = pd.read_csv(source)
        print(f"Reading supplied dataset: {source}")
    else:
        df = make_demo_dataset()
        source = RAW_DIR / "demo_traffic.csv"
        df.to_csv(source, index=False)
        print(f"Created synthetic demo dataset: {source}")
    cleaned = clean_traffic(df)
    if len(cleaned) < 30:
        raise ValueError("At least 30 valid flows are required to train this example.")
    target = PROCESSED_DIR / "traffic_clean.csv"
    cleaned.to_csv(target, index=False)
    print(f"Saved {len(cleaned)} clean flows: {target}")


if __name__ == "__main__":
    main()
'@

$Files['scripts\train.py'] = @'
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
'@

$Files['.gitignore'] = @'
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.env
.DS_Store
frontend/node_modules/
frontend/dist/
*.db
*.sqlite3
models/*.joblib
models/*report.json
datasets/raw/*.csv
datasets/processed/*.csv
'@

foreach ($Relative in $Files.Keys) {
    $Path = Join-Path $ProjectRoot $Relative
    $Parent = Split-Path -Parent $Path
    if (-not (Test-Path $Parent)) { New-Item -ItemType Directory -Force -Path $Parent | Out-Null }
    [System.IO.File]::WriteAllText($Path, $Files[$Relative] + "`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Wrote $Relative"
}
foreach ($Relative in @("datasets\raw","datasets\processed","models")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot $Relative) | Out-Null
}
Write-Host "Backend setup complete."
