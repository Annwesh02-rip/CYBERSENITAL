
"""Two-page graphical PDF of a saved V2 UNSW-NB15 analysis."""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

from reportlab.lib.utils import (
    ImageReader,
    simpleSplit,
)

from reportlab.pdfgen.canvas import Canvas


INK = colors.HexColor("#213B47")

TEAL = "#207A84"
CORAL = "#CB7761"


def _plot(draw, x, y, width, height):

    fig = Figure(
        figsize=(
            width / 105,
            height / 105,
        ),
        dpi=140,
        facecolor="white",
    )

    ax = fig.add_subplot(111)

    draw(ax)

    ax.spines[
        "top"
    ].set_visible(False)

    ax.spines[
        "right"
    ].set_visible(False)

    ax.tick_params(
        labelsize=8
    )

    fig.tight_layout(
        pad=1.2
    )

    output = BytesIO()

    fig.savefig(
        output,
        format="png",
        dpi=140,
    )

    output.seek(0)

    return ImageReader(output)


def _text(
    c,
    value,
    x,
    y,
    width=515,
    font="Helvetica",
    size=9,
    leading=13,
):

    c.setFont(
        font,
        size,
    )

    c.setFillColor(INK)

    lines = simpleSplit(
        str(value),
        font,
        size,
        width,
    )

    for line in lines:

        c.drawString(
            x,
            y,
            line,
        )

        y -= leading

    return y


def create_v2_report_pdf(run):

    if run.get("analysis_type") != "v2_dataset":
        raise ValueError(
            "Not a V2 dataset analysis"
        )

    output = BytesIO()

    c = Canvas(
        output,
        pagesize=A4,
    )

    width, height = A4

    left = 42

    records = (
        run.get("rows") or []
    )

    metrics = (
        run.get("metrics") or {}
    )

    protocols = (
        run.get("protocol_distribution") or []
    )

    flags = int(
        run.get("flagged", 0)
    )

    total = int(
        run.get(
            "rows_analyzed",
            len(records),
        )
    )

    def header(title, page):

        c.setFillColor(INK)

        c.setFont(
            "Helvetica-Bold",
            18,
        )

        c.drawString(
            left,
            height - 51,
            title,
        )

        c.setFont(
            "Helvetica",
            9,
        )

        c.setFillColor(
            colors.HexColor("#5F727D")
        )

        run_id = run.get(
            "history_id",
            run.get("id", "-"),
        )

        c.drawString(
            left,
            height - 70,
            (
                "CyberSentinel  |  UNSW-NB15  "
                f"|  Saved run #{run_id}"
            ),
        )

        c.setStrokeColor(
            colors.HexColor("#DDE6E9")
        )

        c.line(
            left,
            38,
            width - left,
            38,
        )

        c.setFont(
            "Helvetica",
            8,
        )

        c.drawString(
            left,
            25,
            (
                "Local research prototype  |  "
                "Predicted anomalies are not "
                "confirmed attacks"
            ),
        )

        c.drawRightString(
            width - left,
            25,
            f"Page {page} / 2",
        )

    def section(title, y):

        c.setFont(
            "Helvetica-Bold",
            11,
        )

        c.setFillColor(INK)

        c.drawString(
            left,
            y,
            title,
        )

        return y - 17

    # -------------------------------------------
    # PAGE 1 — ANALYSIS SUMMARY
    # -------------------------------------------

    header(
        "Network Anomaly Analysis",
        1,
    )

    y = height - 104

    y = section(
        "1. Analysis summary",
        y,
    )

    pairs = [
        (
            "Model",
            "V2 - Isolation Forest",
        ),

        (
            "Selected features",
            str(
                run.get(
                    "selected_model",
                    "-",
                )
            ),
        ),

        (
            "Analyzed records",
            f"{total:,}",
        ),

        (
            "Flagged anomalies",
            (
                f"{flags:,} "
                f"({flags / max(1, total) * 100:.1f}%)"
            ),
        ),

        (
            "Decision threshold",
            (
                f"{float(run.get('threshold', 0)):.5f}"
            ),
        ),

        (
            "Ground-truth labels",
            (
                "Available"
                if run.get("has_labels")
                else "Not available"
            ),
        ),
    ]

    for label, value in pairs:

        c.setFont(
            "Helvetica",
            9,
        )

        c.setFillColor(
            colors.HexColor("#52646D")
        )

        c.drawString(
            left + 5,
            y,
            label,
        )

        c.setFont(
            "Helvetica-Bold",
            9,
        )

        c.setFillColor(INK)

        c.drawString(
            left + 175,
            y,
            value,
        )

        y -= 19

    y -= 7

    y = section(
        "2. Observed protocol distribution",
        y,
    )

    # -------------------------------------------
    # GRAPH 1 — PROTOCOL DISTRIBUTION
    # -------------------------------------------

    if protocols:

        labels = [
            str(item.get("name", "?"))
            for item in protocols[:8]
        ][::-1]

        counts = [
            int(item.get("value", 0))
            for item in protocols[:8]
        ][::-1]

        def draw_protocol(ax):

            ax.barh(
                labels,
                counts,
                color=TEAL,
            )

            ax.set_xlabel(
                "Records",
                fontsize=9,
            )

            ax.grid(
                axis="x",
                alpha=0.15,
            )

        c.drawImage(
            _plot(
                draw_protocol,
                0,
                0,
                500,
                205,
            ),

            left + 7,
            y - 203,

            width=500,
            height=205,
        )

    else:

        _text(
            c,
            "Protocol distribution unavailable",
            left,
            y - 20,
        )

    y -= 224

    y = section(
        "3. Predicted class distribution",
        y,
    )

    # -------------------------------------------
    # GRAPH 2 — FLAGGED VS NOT FLAGGED
    # -------------------------------------------

    def draw_flags(ax):

        ax.barh(
            [
                "Not flagged",
                "Flagged",
            ],

            [
                max(total - flags, 0),
                flags,
            ],

            color=[
                TEAL,
                CORAL,
            ],
        )

        ax.set_xlabel(
            "Records",
            fontsize=9,
        )

        ax.grid(
            axis="x",
            alpha=0.12,
        )

    c.drawImage(
        _plot(
            draw_flags,
            0,
            0,
            500,
            124,
        ),

        left + 7,
        y - 113,

        width=500,
        height=115,
    )

    _text(
        c,
        (
            "Results summarize saved dataset "
            "records, not real-time packet capture."
        ),
        left,
        72,
        width=505,
        size=8,
    )

    c.showPage()

    # -------------------------------------------
    # PAGE 2 — VISUAL EVALUATION
    # -------------------------------------------

    header(
        "Visual Analysis & Evaluation",
        2,
    )

    y = height - 104

    y = section(
        "4. PCA projection (visualization only)",
        y,
    )

    # -------------------------------------------
    # GRAPH 3 — PCA SCATTER PLOT
    # -------------------------------------------

    if records:

        step = max(
            1,
            len(records) // 1200,
        )

        plotted = records[::step]

        def draw_pca(ax):

            for flagged, label, color in [
                (
                    False,
                    "Not flagged",
                    TEAL,
                ),
                (
                    True,
                    "Flagged",
                    CORAL,
                ),
            ]:

                points = [
                    record
                    for record in plotted
                    if bool(
                        record.get(
                            "predicted_anomaly"
                        )
                    ) == flagged
                ]

                if points:

                    ax.scatter(
                        [
                            float(
                                record.get(
                                    "pc1",
                                    0,
                                )
                            )
                            for record in points
                        ],

                        [
                            float(
                                record.get(
                                    "pc2",
                                    0,
                                )
                            )
                            for record in points
                        ],

                        s=8,
                        alpha=0.63,
                        c=color,
                        label=label,
                    )

            ax.set_xlabel(
                "PC1",
                fontsize=9,
            )

            ax.set_ylabel(
                "PC2",
                fontsize=9,
            )

            ax.legend(
                loc="best",
                fontsize=7,
            )

            ax.grid(
                alpha=0.15
            )

        c.drawImage(
            _plot(
                draw_pca,
                0,
                0,
                510,
                256,
            ),

            left + 4,
            y - 256,

            width=510,
            height=256,
        )

    else:

        _text(
            c,
            "PCA points unavailable",
            left,
            y - 20,
        )

    y -= 273

    y = section(
        "5. Anomaly score distribution",
        y,
    )

    # -------------------------------------------
    # GRAPH 4 — ANOMALY SCORE HISTOGRAM
    # -------------------------------------------

    if records:

        def draw_hist(ax):

            normal = [
                float(
                    record.get(
                        "anomaly_score",
                        0,
                    )
                )
                for record in records
                if not record.get(
                    "predicted_anomaly"
                )
            ]

            anomalous = [
                float(
                    record.get(
                        "anomaly_score",
                        0,
                    )
                )
                for record in records
                if record.get(
                    "predicted_anomaly"
                )
            ]

            if normal:

                ax.hist(
                    normal,
                    bins=25,
                    alpha=0.7,
                    color=TEAL,
                    label="Not flagged",
                )

            if anomalous:

                ax.hist(
                    anomalous,
                    bins=25,
                    alpha=0.7,
                    color=CORAL,
                    label="Flagged",
                )

            ax.axvline(
                float(
                    run.get(
                        "threshold",
                        0,
                    )
                ),
                color="#333333",
                linestyle="--",
                linewidth=1,
                label="Threshold",
            )

            ax.set_xlabel(
                (
                    "Anomaly score "
                    "(higher = more unusual)"
                ),
                fontsize=9,
            )

            ax.set_ylabel(
                "Records",
                fontsize=9,
            )

            ax.legend(
                fontsize=7
            )

        c.drawImage(
            _plot(
                draw_hist,
                0,
                0,
                510,
                180,
            ),

            left + 4,
            y - 180,

            width=510,
            height=180,
        )

    else:

        _text(
            c,
            "Anomaly scores unavailable",
            left,
            y - 20,
        )

    y -= 197

    y = section(
        "6. Evaluation and interpretation",
        y,
    )

    if metrics:

        msg = (
            f"Accuracy {metrics.get('accuracy', 0):.2%}  "
            f"|  Precision {metrics.get('precision', 0):.2%}  "
            f"|  Recall {metrics.get('recall', 0):.2%}  "
            f"|  F1 {metrics.get('f1', 0):.2%}"
        )

        y = _text(
            c,
            msg,
            left,
            y,
            width=510,
            size=9,
        )

        matrix = metrics.get(
            "confusion_matrix",
            [
                [0, 0],
                [0, 0],
            ],
        )

        y = _text(
            c,
            (
                "Confusion matrix: "
                f"TN {matrix[0][0]}, "
                f"FP {matrix[0][1]}, "
                f"FN {matrix[1][0]}, "
                f"TP {matrix[1][1]}"
            ),
            left,
            y - 2,
            width=510,
            size=8,
        )

    else:

        y = _text(
            c,
            (
                "No validated labels: accuracy "
                "and confusion matrix are unavailable."
            ),
            left,
            y,
            width=510,
            size=9,
        )

    _text(
        c,
        (
            "PCA is illustrative when the selected "
            "detector uses numeric-only features. "
            "Validation labels calibrated its threshold."
        ),
        left,
        y - 6,
        width=510,
        size=8,
        leading=11,
    )

    c.showPage()
    c.save()

    return output.getvalue()
