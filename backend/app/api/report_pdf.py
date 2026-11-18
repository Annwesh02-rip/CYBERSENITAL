"""PDF report generation for CyberSentinel."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.units import mm

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)


INK = colors.HexColor("#233444")
TEAL = colors.HexColor("#167580")
MUTED = colors.HexColor("#617180")
PAPER = colors.HexColor("#F4F2EC")
LINE = colors.HexColor("#DDE4E7")


def safe_text(value):
    if value is None:
        return "-"
    return escape(str(value))


def format_percent(value):
    if value is None:
        return "N/A"

    return f"{float(value) * 100:.2f}%"


def format_metric(field, value):
    if value is None:
        return "N/A"

    if field in ("roc_auc", "pr_auc"):
        return f"{float(value):.4f}"

    return format_percent(value)


def create_table(rows, widths, header=True):
    table = Table(
        rows,
        colWidths=widths,
        repeatRows=1 if header else 0,
        hAlign="LEFT"
    )

    styles = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        (
            "LINEBELOW",
            (0, -1),
            (-1, -1),
            0.4,
            LINE
        ),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, PAPER]
        )
    ]

    if header:
        styles.extend([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                INK
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
            )
        ])

    table.setStyle(TableStyle(styles))

    return table


def create_report_pdf(run):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=19 * mm,
        title=(
            "CyberSentinel Analysis "
            f"#{run['history_id']}"
        ),
        author="CyberSentinel"
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CS_Title",
            parent=styles["Title"],
            textColor=INK,
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            alignment=TA_LEFT,
            spaceAfter=7
        )
    )

    styles.add(
        ParagraphStyle(
            name="CS_Section",
            parent=styles["Heading2"],
            textColor=INK,
            fontSize=12,
            leading=16,
            spaceBefore=15,
            spaceAfter=8
        )
    )

    styles.add(
        ParagraphStyle(
            name="CS_Body",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=14,
            textColor=INK,
            spaceAfter=6
        )
    )

    styles.add(
        ParagraphStyle(
            name="CS_Muted",
            parent=styles["BodyText"],
            fontSize=8.3,
            leading=12,
            textColor=MUTED,
            spaceAfter=7
        )
    )

    story = []

    story.append(
        Paragraph(
            "CYBERSENTINEL",
            styles["CS_Muted"]
        )
    )

    story.append(
        Paragraph(
            "Network Anomaly Analysis Report",
            styles["CS_Title"]
        )
    )

    story.append(
        Paragraph(
            "Unsupervised Machine Learning | "
            "PCA | Isolation Forest",
            styles["CS_Muted"]
        )
    )

    story.append(Spacer(1, 6))

    # ---------------------------------------
    # DATASET SUMMARY
    # ---------------------------------------

    story.append(
        Paragraph(
            "Analysis Summary",
            styles["CS_Section"]
        )
    )

    summary = [
        [
            "Report ID",
            f"#{run['history_id']}",
            "Date (UTC)",
            run["created_at"]
        ],
        [
            "Source",
            safe_text(
                run.get("source", "-")
            )[:27],
            "Records",
            str(
                run.get("rows_analyzed", 0)
            )
        ],
        [
            "Features",
            f"{run.get('encoded_features', '-')} encoded",
            "PCA",
            f"{run.get('pca_features', '-')} components"
        ],
        [
            "Flagged (original)",
            str(
                run.get("flagged_original", 0)
            ),
            "Flagged (PCA)",
            str(
                run.get("flagged_pca", 0)
            )
        ]
    ]

    story.append(
        create_table(
            summary,
            [91, 145, 87, 169],
            header=False
        )
    )

    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "Anomaly flags indicate statistical "
            "unusualness, not verified cyberattacks. "
            "These models are experimental.",
            styles["CS_Muted"]
        )
    )

    # ---------------------------------------
    # MODEL COMPARISON
    # ---------------------------------------

    story.append(
        Paragraph(
            "Model Comparison",
            styles["CS_Section"]
        )
    )

    original = run.get("original_metrics") or {}
    pca = run.get("pca_metrics") or {}

    if original or pca:
        metrics = [
            [
                "Metric",
                "Original Isolation Forest",
                "PCA + Isolation Forest"
            ]
        ]

        metric_fields = [
            ("Accuracy", "accuracy"),
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("F1-score", "f1"),
            ("ROC-AUC", "roc_auc"),
            ("PR-AUC", "pr_auc")
        ]

        for label, field in metric_fields:
            metrics.append([
                label,
                format_metric(
                    field,
                    original.get(field)
                ),
                format_metric(
                    field,
                    pca.get(field)
                )
            ])

        story.append(
            create_table(
                metrics,
                [112, 186, 194]
            )
        )

    else:
        story.append(
            Paragraph(
                "Ground-truth labels were not "
                "available. Classification metrics "
                "could not be calculated.",
                styles["CS_Body"]
            )
        )

    # ---------------------------------------
    # PROTOCOL DISTRIBUTION
    # ---------------------------------------

    story.append(
        Paragraph(
            "Protocol Distribution",
            styles["CS_Section"]
        )
    )

    protocols = run.get(
        "protocol_distribution", []
    )[:8]

    if protocols:
        protocol_rows = [
            ["Protocol", "Flows"]
        ]

        for item in protocols:
            protocol_rows.append([
                safe_text(
                    item.get("name")
                )[:18],
                str(
                    item.get("value", 0)
                )
            ])

        story.append(
            create_table(
                protocol_rows,
                [246, 246]
            )
        )

    # ---------------------------------------
    # RECOMMENDATIONS
    # ---------------------------------------

    story.append(
        Paragraph(
            "Recommended Follow-up",
            styles["CS_Section"]
        )
    )

    for index, recommendation in enumerate(
        run.get("recommendations", []),
        1
    ):
        story.append(
            Paragraph(
                f"{index}. {safe_text(recommendation)}",
                styles["CS_Body"]
            )
        )

    # ---------------------------------------
    # SECOND PAGE
    # ---------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Flagged Traffic Sample",
            styles["CS_Section"]
        )
    )

    story.append(
        Paragraph(
            "Up to 20 records flagged by the "
            "PCA-based model. Anomaly scores "
            "are not attack probabilities.",
            styles["CS_Muted"]
        )
    )

    selected = [
        row
        for row in run.get("rows", [])
        if row.get("pca_flag")
    ][:20]

    if selected:
        record_rows = [
            [
                "Row",
                "Protocol",
                "Service",
                "Duration (s)",
                "Score",
                "Label"
            ]
        ]

        for row in selected:
            label = row.get(
                "actual_attack"
            )

            if label is None:
                label_text = "Unknown"
            elif label == 1:
                label_text = "Attack"
            else:
                label_text = "Normal"

            record_rows.append([
                str(
                    row.get("row", "-")
                ),
                safe_text(
                    row.get("proto", "-")
                )[:13],
                safe_text(
                    row.get("service", "-")
                )[:12],
                (
                    f"{float(row.get('duration', 0)):.3f}"
                ),
                (
                    f"{float(row.get('pca_score', 0)):.4f}"
                ),
                label_text
            ])

        story.append(
            create_table(
                record_rows,
                [48, 84, 91, 95, 84, 90]
            )
        )

    else:
        story.append(
            Paragraph(
                "No records were flagged by the "
                "PCA-based model.",
                styles["CS_Body"]
            )
        )

    # ---------------------------------------
    # METHODOLOGY AND LIMITATIONS
    # ---------------------------------------

    story.append(Spacer(1, 16))

    story.append(
        Paragraph(
            "Method and Limitations",
            styles["CS_Section"]
        )
    )

    notes = [
        (
            "Network records were preprocessed using "
            "the saved training transformer. PCA and "
            "Isolation Forest were then applied "
            "without retraining."
        ),
        (
            "UNSW-NB15 is analyzed as an offline "
            "network traffic dataset. These reports "
            "do not represent live traffic monitoring."
        ),
        (
            "Where labels were present, they were "
            "used for evaluation only, not as "
            "input features during inference."
        ),
        (
            "The model is a research prototype. "
            "Flagged traffic requires manual "
            "verification before it can be "
            "classified as malicious."
        )
    ]

    for note in notes:
        story.append(
            Paragraph(
                safe_text(note),
                styles["CS_Body"]
            )
        )

    # ---------------------------------------
    # PAGE FOOTER
    # ---------------------------------------

    def footer(canvas, doc):
        canvas.saveState()

        canvas.setStrokeColor(LINE)

        canvas.line(
            18 * mm,
            16 * mm,
            A4[0] - 18 * mm,
            16 * mm
        )

        canvas.setFont(
            "Helvetica",
            8
        )

        canvas.setFillColor(MUTED)

        canvas.drawString(
            18 * mm,
            11 * mm,
            "CyberSentinel | Offline Network Analysis"
        )

        canvas.drawRightString(
            A4[0] - 18 * mm,
            11 * mm,
            f"Page {doc.page}"
        )

        canvas.restoreState()

    document.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer
    )

    return buffer.getvalue()