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
