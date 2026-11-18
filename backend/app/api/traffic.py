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
