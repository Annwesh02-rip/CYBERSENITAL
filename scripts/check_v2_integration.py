
"""
CyberSentinel V2 Integration Check

Requires the FastAPI backend to be running.

Tests:
- Saved V2 model files
- Real inference on 100 test records
- SQLite history persistence
- Graphical PDF generation
- Predictions CSV generation

Deletes its temporary analysis afterward.
"""

import json

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.request import (
    Request,
    urlopen,
)


BASE = "http://127.0.0.1:8000"


def request(
    path,
    method="GET",
):

    req = Request(
        BASE + path,
        method=method,
    )

    try:

        with urlopen(
            req,
            timeout=90,
        ) as response:

            return (
                response.read(),

                response.headers.get(
                    "Content-Type",
                    "",
                ),
            )

    except HTTPError as exc:

        details = exc.read().decode(
            "utf8",
            "replace",
        )

        raise RuntimeError(
            f"HTTP {exc.code} at {path}: "
            f"{details}"
        ) from exc


def main():

    run_id = None

    try:

        print(
            "1/6 Checking V2 model files..."
        )

        status = json.loads(
            request(
                "/api/model-v2/status"
            )[0]
        )

        assert (
            status["model_ready"]
            and status["report_ready"]
            and status["sample_ready"]
        ), status


        print(
            "2/6 Running actual V2 inference "
            "and saving 100 records..."
        )

        analysis = json.loads(
            request(
                (
                    "/api/model-v2/sample"
                    "?rows=100&save=true"
                ),
                "POST",
            )[0]
        )

        run_id = analysis[
            "history_id"
        ]

        assert (
            analysis["model_version"] == "V2"
            and analysis["rows_analyzed"] == 100
        )


        print(
            "3/6 Checking SQLite history..."
        )

        saved = json.loads(
            request(
                f"/api/history/runs/{run_id}"
            )[0]
        )

        assert (
            saved["analysis_type"] == "v2_dataset"
        )

        assert (
            saved["rows_analyzed"] == 100
        )


        print(
            "4/6 Checking graphical PDF..."
        )

        pdf, content_type = request(
            (
                f"/api/model-v2/history/"
                f"{run_id}/report.pdf"
            )
        )

        assert (
            pdf.startswith(b"%PDF")
            and len(pdf) > 5000
            and "pdf" in content_type
        )


        print(
            "5/6 Checking predictions CSV..."
        )

        csv_bytes, _ = request(
            (
                f"/api/model-v2/history/"
                f"{run_id}/predictions.csv"
            )
        )

        assert (
            b"anomaly_score" in csv_bytes
            and b"predicted_anomaly" in csv_bytes
        )


        print(
            "6/6 All V2 integration checks passed."
        )

    finally:

        if run_id is not None:

            try:

                request(
                    f"/api/history/runs/{run_id}",
                    "DELETE",
                )

                print(
                    f"Temporary test history "
                    f"#{run_id} removed."
                )

            except (
                RuntimeError,
                URLError,
            ) as exc:

                print(
                    "Could not clean temporary "
                    f"history #{run_id}: {exc}"
                )


if __name__ == "__main__":
    main()
