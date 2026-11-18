
"""CyberSentinel analysis and live-capture history API."""

import csv

from io import BytesIO, StringIO

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile
)

from fastapi.responses import StreamingResponse

from app.api import inspection

from app.api.report_pdf import create_report_pdf
from app.api.live_report import create_live_report_pdf

from app.database.history_store import (
    delete_analysis,
    get_analysis,
    list_analyses,
    save_analysis
)


router = APIRouter(
    prefix="/api/history",
    tags=["Analysis History"]
)


@router.post("/sample")
def analyze_and_save_sample(
    rows: int = Query(
        default=1500,
        ge=100,
        le=5000
    )
):
    result = inspection.analyze_sample(rows=rows)

    return save_analysis(result)


@router.post("/upload")
async def analyze_and_save_upload(
    file: UploadFile = File(...)
):
    result = await inspection.analyze_uploaded_csv(
        file=file
    )

    return save_analysis(result)


@router.get("/runs")
def get_runs(
    limit: int = Query(
        default=30,
        ge=1,
        le=100
    )
):
    return list_analyses(limit=limit)


@router.get("/runs/{run_id}")
def get_run(run_id: int):

    result = get_analysis(run_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found."
        )

    return result


@router.get("/runs/{run_id}/report.pdf")
def download_report(run_id: int):

    result = get_run(run_id)

    if result.get("analysis_type") == "live_capture":
        pdf_bytes = create_live_report_pdf(result)
    else:
        pdf_bytes = create_report_pdf(result)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; filename="
                f'"CyberSentinel_Report_{run_id}.pdf"'
            )
        }
    )


@router.get("/runs/{run_id}/flows.csv")
def download_live_flows(run_id: int):

    result = get_run(run_id)

    if result.get("analysis_type") != "live_capture":
        raise HTTPException(
            status_code=400,
            detail=(
                "Flow CSV export is available "
                "only for live captures."
            )
        )

    fields = [
        "source",
        "destination",
        "source_port",
        "destination_port",
        "protocol",
        "packets",
        "bytes",
        "last_seen"
    ]

    output = StringIO(newline="")

    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        extrasaction="ignore"
    )

    writer.writeheader()

    live = result.get("live") or {}

    for row in live.get("flows", []):
        safe = {}

        for field in fields:
            value = row.get(field, "")

            if (
                isinstance(value, str)
                and value.lstrip().startswith(
                    ("=", "+", "-", "@")
                )
            ):
                value = "'" + value

            safe[field] = value

        writer.writerow(safe)

    return StreamingResponse(
        BytesIO(
            output.getvalue().encode("utf-8-sig")
        ),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; filename="
                f'"CyberSentinel_Live_Flows_{run_id}.csv"'
            )
        }
    )


@router.delete("/runs/{run_id}")
def remove_run(run_id: int):

    if not delete_analysis(run_id):
        raise HTTPException(
            status_code=404,
            detail="Analysis not found."
        )

    return {
        "deleted": True,
        "id": run_id
    }
