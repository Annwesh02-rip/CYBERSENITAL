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
