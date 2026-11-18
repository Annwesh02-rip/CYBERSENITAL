
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import init_database
from app.database.history_store import init_history_db

from app.api import (
    dashboard,
    traffic,
    analysis,
    dataset,
    inspection,
    history,
    live,
    model_v2
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    init_database()
    init_history_db()

    yield

    from app.capture.packet_capture import capture_service

    capture_service.stop()


app = FastAPI(
    title="CyberSentinel API",
    description=(
        "Network Anomaly Detection Using "
        "Unsupervised Machine Learning "
        "and Dimensionality Reduction"
    ),
    version="1.5.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "DELETE"
    ],
    allow_headers=["*"]
)


app.include_router(dashboard.router)
app.include_router(traffic.router)
app.include_router(analysis.router)
app.include_router(dataset.router)
app.include_router(inspection.router)
app.include_router(history.router)
app.include_router(live.router)
app.include_router(model_v2.router)


@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "CyberSentinel",
        "version": "1.5.0"
    }
