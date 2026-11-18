
"""Two-page illustrated live network analysis report."""

from io import BytesIO
from xml.sax.saxutils import escape

from matplotlib.figure import Figure

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet
)
from reportlab.lib.units import mm

from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle
)


NAVY = colors.HexColor("#193F50")
DARK = colors.HexColor("#233D48")
GRAY = colors.HexColor("#617780")
STRIPE = colors.HexColor("#F1F6F7")

TEAL = "#227C87"
ORANGE = "#CD7458"


# --------------------------------------------------
# CHART GENERATOR
# --------------------------------------------------

def chart_image(
    plotter,
    width_mm=174,
    height_mm=57
):
    fig = Figure(
        figsize=(9, 2.9),
        dpi=130,
        facecolor="white"
    )

    ax = fig.add_subplot(111)

    plotter(ax)

    ax.tick_params(
        labelsize=8,
        colors="#4B6470"
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(
        axis="y",
        alpha=0.16
    )

    fig.tight_layout(pad=1.3)

    buf = BytesIO()

    fig.savefig(
        buf,
        format="png",
        dpi=130,
        bbox_inches="tight"
    )

    buf.seek(0)

    return Image(
        buf,
        width=width_mm * mm,
        height=height_mm * mm
    )


# --------------------------------------------------
# PDF TABLE GENERATOR
# --------------------------------------------------

def report_table(rows, widths):
    table = Table(
        rows,
        colWidths=[
            width * mm
            for width in widths
        ],
        repeatRows=1,
        hAlign="LEFT"
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                NAVY
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, STRIPE]
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    return table


# --------------------------------------------------
# MAIN PDF GENERATOR
# --------------------------------------------------

def create_live_report_pdf(run: dict) -> bytes:

    if run.get("analysis_type") != "live_capture":
        raise ValueError(
            "The saved analysis is not a live capture."
        )

    live = run.get("live") or {}
    ml = live.get("ml") or {}

    elapsed = max(
        1,
        int(live.get("elapsed_seconds", 0))
    )

    # Supports previous saved reports which
    # did not explicitly store session averages.
    average_pps = float(
        live.get(
            "average_packets_per_second",
            live.get("total_packets", 0) / elapsed
        )
    )

    average_bps = float(
        live.get(
            "average_bytes_per_second",
            live.get("total_bytes", 0) / elapsed
        )
    )

    protocols = live.get("protocols") or []
    timeline = live.get("timeline") or []
    flows = live.get("flows") or []
    anomalies = ml.get("anomalies") or []

    buf = BytesIO()

    document = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,

        title=(
            "CyberSentinel Live Analysis "
            f"#{run.get('history_id', '-')}"
        ),

        author="CyberSentinel"
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CS_title",
            parent=styles["Title"],
            fontSize=19,
            leading=23,
            textColor=DARK,
            spaceAfter=4
        )
    )

    styles.add(
        ParagraphStyle(
            name="CS_head",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=DARK,
            spaceBefore=10,
            spaceAfter=6
        )
    )

    styles.add(
        ParagraphStyle(
            name="CS_body",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=12,
            textColor=GRAY,
            spaceAfter=6
        )
    )

    styles.add(
        ParagraphStyle(
            name="CS_small",
            parent=styles["BodyText"],
            fontSize=7.4,
            leading=10,
            textColor=DARK
        )
    )

    def body(text):
        return Paragraph(
            escape(str(text)),
            styles["CS_body"]
        )

    def title(text):
        return Paragraph(
            text,
            styles["CS_head"]
        )

    # --------------------------------------------------
    # PAGE 1: SUMMARY
    # --------------------------------------------------

    story = [
        Paragraph(
            "CyberSentinel | Live Network Analysis",
            styles["CS_title"]
        ),

        body(
            "Traffic metadata and optional "
            "unsupervised flow anomaly screening."
        ),

        report_table(
            [
                [
                    "CAPTURE SUMMARY",
                    "RECORDED VALUE"
                ],

                [
                    "Report ID / UTC time",
                    (
                        f"#{run.get('history_id')}  |  "
                        f"{run.get('created_at', '-')[:19]}"
                    )
                ],

                [
                    "Capture duration",
                    f"{live.get('elapsed_seconds', 0)} seconds"
                ],

                [
                    "Captured packets / bytes",
                    (
                        f"{live.get('total_packets', 0):,}  /  "
                        f"{live.get('total_bytes', 0):,} B"
                    )
                ],

                [
                    "Session avg. packets/sec",
                    f"{average_pps:.2f}"
                ],

                [
                    "Session avg. bytes/sec",
                    f"{average_bps:.2f}"
                ],

                [
                    "Observed active flows",
                    str(
                        live.get("active_flows", 0)
                    )
                ]
            ],
            [68, 106]
        ),

        title("1. Protocol distribution")
    ]

    # --------------------------------------------------
    # CHART 1: PROTOCOL DISTRIBUTION
    # --------------------------------------------------

    if protocols:

        def protocol_plot(ax):
            ordered = sorted(
                protocols,
                key=lambda item: item.get(
                    "packets", 0
                )
            )

            ax.barh(
                [
                    item["name"]
                    for item in ordered
                ],

                [
                    item["packets"]
                    for item in ordered
                ],

                color=TEAL
            )

            ax.set_xlabel(
                "Captured packets",
                fontsize=9
            )

        story.append(
            chart_image(
                protocol_plot,
                height_mm=51
            )
        )

    else:
        story.append(
            body(
                "No protocol data was stored "
                "for this capture."
            )
        )

    # --------------------------------------------------
    # CHART 2: TRAFFIC OVER TIME
    # --------------------------------------------------

    story.append(
        title(
            "2. Recent captured traffic "
            "(last 30 seconds)"
        )
    )

    if (
        timeline
        and any(
            float(
                point.get(
                    "bytes",
                    point.get("kbps", 0)
                )
            ) > 0
            for point in timeline
        )
    ):

        def timeline_plot(ax):
            x = list(range(len(timeline)))

            rates = [
                float(
                    point.get(
                        "kbps",
                        float(
                            point.get("bytes", 0)
                        ) / 1024
                    )
                )
                for point in timeline
            ]

            ax.plot(
                x,
                rates,
                color=TEAL,
                linewidth=2
            )

            ax.fill_between(
                x,
                rates,
                color=TEAL,
                alpha=0.10
            )

            ticks = sorted(
                set([
                    0,
                    len(x) // 4,
                    len(x) // 2,
                    3 * len(x) // 4,
                    len(x) - 1
                ])
            )

            ax.set_xticks(
                ticks,
                [
                    str(
                        timeline[i].get(
                            "time", ""
                        )
                    )
                    for i in ticks
                ],
                fontsize=8
            )

            ax.set_ylabel(
                "Captured KB/s",
                fontsize=9
            )

        story.append(
            chart_image(
                timeline_plot,
                height_mm=51
            )
        )

    else:
        story.append(
            body(
                "Per-second activity was not retained "
                "in this saved capture."
            )
        )

    story.append(
        body(
            "Average rates summarize the whole saved "
            "session; instantaneous rates may be zero "
            "after capture stops. This is not measured "
            "link utilization."
        )
    )

    # --------------------------------------------------
    # PAGE 2: ANALYSIS
    # --------------------------------------------------

    story.append(PageBreak())

    story.extend([
        Paragraph(
            "Flow Analysis & Outlier Screening",
            styles["CS_title"]
        ),

        body(
            "Directed flow statistics and optional "
            "inference using the locally trained "
            "live-flow baseline."
        ),

        title("3. Largest observed flows")
    ])

    # --------------------------------------------------
    # CHART 3: TOP NETWORK FLOWS
    # --------------------------------------------------

    if flows:
        top = sorted(
            flows,
            key=lambda flow: flow.get(
                "bytes", 0
            ),
            reverse=True
        )[:8]

        def top_flow_plot(ax):
            labels = [
                (
                    f"{flow.get('protocol', '')}  "
                    f"{flow.get('source', '')}"
                )[:32]
                for flow in reversed(top)
            ]

            values = [
                float(
                    flow.get("bytes", 0)
                ) / 1024
                for flow in reversed(top)
            ]

            ax.barh(
                labels,
                values,
                color=TEAL
            )

            ax.set_xlabel(
                "Observed KB",
                fontsize=9
            )

        story.append(
            chart_image(
                top_flow_plot,
                height_mm=67
            )
        )

    else:
        story.append(
            body(
                "No aggregated flow data was stored."
            )
        )

    # --------------------------------------------------
    # CHART 4: LIVE ANOMALY ANALYSIS
    # --------------------------------------------------

    story.append(
        title("4. Live-flow anomaly analysis")
    )

    if ml.get("state") == "scoring":

        story.append(
            body(
                f"Baseline: {ml.get('training_flows', 0)} "
                f"ordinary-traffic flows; "
                f"evaluated: {ml.get('scored_flows', 0)} "
                f"flows; flagged: "
                f"{ml.get('flagged_flows', 0)}."
            )
        )

        if anomalies:
            shortlisted = anomalies[:7]

            def anomaly_plot(ax):
                ordered = list(
                    reversed(shortlisted)
                )

                labels = [
                    (
                        f"{item.get('protocol', '')} "
                        f"{item.get('source', '')}"
                    )[:32]
                    for item in ordered
                ]

                ax.barh(
                    labels,
                    [
                        float(
                            item.get("score", 0)
                        )
                        for item in ordered
                    ],
                    color=ORANGE
                )

                ax.set_xlabel(
                    "Outlier score "
                    "(higher = more unusual)",
                    fontsize=9
                )

            story.append(
                chart_image(
                    anomaly_plot,
                    height_mm=56
                )
            )

        else:
            story.append(
                body(
                    "No eligible flows were flagged "
                    "as outliers by this baseline."
                )
            )

    else:
        story.append(
            body(
                "No live-flow scoring was available "
                "for this session. Status: "
                f"{ml.get('state', 'not recorded')}. "
                "Capture ordinary traffic, train a "
                "baseline, then begin a new session."
            )
        )

    # --------------------------------------------------
    # INTERPRETATION AND LIMITATIONS
    # --------------------------------------------------

    story.append(
        title(
            "5. Interpretation and limitations"
        )
    )

    story.append(
        KeepTogether([
            body(
                "Live outlier flags indicate deviation "
                "from the local baseline, not confirmed "
                "attacks. This live model is separate "
                "from the UNSW-NB15 classifier and "
                "has no measured classification accuracy "
                "without verified labels."
            ),

            body(
                "The flow graph shows a bounded set "
                "of top-volume directed flows, not "
                "reconstructed network sessions. "
                "IP/port metadata may be sensitive; "
                "share reports only with authorized people."
            )
        ])
    )

    # --------------------------------------------------
    # PAGE FOOTER
    # --------------------------------------------------

    def footer(canvas, doc):
        canvas.saveState()

        canvas.setStrokeColor(
            colors.HexColor("#D6E0E3")
        )

        canvas.line(
            17 * mm,
            13 * mm,
            A4[0] - 17 * mm,
            13 * mm
        )

        canvas.setFillColor(GRAY)

        canvas.setFont(
            "Helvetica",
            7.5
        )

        canvas.drawString(
            17 * mm,
            9 * mm,
            "CyberSentinel | Local research prototype"
        )

        canvas.drawRightString(
            A4[0] - 17 * mm,
            9 * mm,
            f"Page {doc.page}"
        )

        canvas.restoreState()

    document.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer
    )

    return buf.getvalue()
