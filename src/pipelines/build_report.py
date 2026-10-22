"""Build a PDF summary of shipment recommendations."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.components.recommendation import recommend
from src.core.config import (
    PRIORITY_PROFILES,
    REPORT_COLORS,
    REPORT_OUTPUT_PATH,
)
from src.core.logger import get_logger
from src.core.schemas import Recommendation, ShipmentRequest
from src.pipelines.evaluate import run_evaluation


logger = get_logger(__name__)


def get_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    palette = {
        name: colors.HexColor(value) for name, value in REPORT_COLORS.items()
    }
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
            leading=23, textColor=palette["navy"], alignment=TA_CENTER, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=9,
            leading=12, textColor=palette["muted"], alignment=TA_CENTER, spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "SectionHeading", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=palette["navy"], spaceBefore=5, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "ReportBody", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5,
            leading=11.2, textColor=palette["ink"], spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "SmallBody", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5,
            leading=9.5, textColor=palette["ink"], spaceAfter=2,
        ),
        "table_header": ParagraphStyle(
            "TableHeader", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=9, textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5,
            leading=9.2, textColor=palette["ink"],
        ),
        "callout": ParagraphStyle(
            "Callout", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=9,
            leading=12, textColor=palette["navy"], alignment=TA_CENTER,
        ),
        "code": ParagraphStyle(
            "CodeBlock", parent=base["Code"], fontName="Courier", fontSize=7.2,
            leading=9.2, textColor=palette["ink"], leftIndent=4, rightIndent=4,
        ),
    }


def make_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def build_table(rows: list[list[Paragraph]], widths: list[float], header: bool = False) -> Table:
    table = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor(REPORT_COLORS["border"])),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(REPORT_COLORS["navy"])),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor(REPORT_COLORS["pale_gray"])],
                ),
            ]
        )
    else:
        commands.append(
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(REPORT_COLORS["pale_blue"]))
        )
    table.setStyle(TableStyle(commands))
    return table


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(REPORT_COLORS["border"]))
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 0.48 * inch, letter[0] - doc.rightMargin, 0.48 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor(REPORT_COLORS["muted"]))
    canvas.drawString(doc.leftMargin, 0.31 * inch, "Aiqon shipment route recommendation · decision-support report")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.31 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_report(
    output_path: str | Path = REPORT_OUTPUT_PATH,
    shipments: list[ShipmentRequest] | None = None,
    dataset_name: str | None = None,
    recommendation: Recommendation | None = None,
) -> Path:
    logger.info(f"Building technical report at {output_path}")
    if shipments is None:
        raise ValueError("Shipment data is required to build a report.")
    dataset_label = dataset_name or "provided dataset"
    summary = run_evaluation(shipments)
    first = shipments[0]
    example = recommendation or recommend(first)
    first = example.shipment
    selected = example.selected
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=letter,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.52 * inch,
        bottomMargin=0.68 * inch,
        title="Aiqon Shipment Route Optimization - Technical Report",
        author="Aiqon Route Recommender",
    )
    styles = get_styles()
    profile_rows = [
        [
            make_paragraph("Profile", styles["table_header"]),
            make_paragraph("Weights (cost / time / reliability / risk)", styles["table_header"]),
        ],
    ]
    for profile_name, profile_weights in PRIORITY_PROFILES.items():
        values = ", ".join(
            f"{profile_weights[key]:.0%}" for key in ("cost", "time", "delay", "risk")
        )
        profile_rows.append(
            [
                make_paragraph(escape(profile_name.replace("_", " ")), styles["table_cell"]),
                make_paragraph(values, styles["table_cell"]),
            ]
        )
    story = [
        make_paragraph("Shipment Route Recommendation", styles["title"]),
        make_paragraph("A transparent decision model for balancing cost, transit time, reliability, and risk", styles["subtitle"]),
        build_table(
            [[make_paragraph(
                "Recommendation: apply operational limits first, then rank feasible routes with a documented Weighted Sum Model.",
                styles["callout"],
            )]],
            [7.25 * inch],
        ),
        Spacer(1, 7),
        make_paragraph("Problem and assumptions", styles["heading"]),
        make_paragraph(
            "The system accepts a shipment and its candidate multi-leg routes, then returns a route an operator can compare and explain. No universal definition of optimality is assumed, so preferences are explicit. Generated values are illustrative; uploaded values must be validated for their operating context.",
            styles["body"],
        ),
        make_paragraph(
            f"The selected dataset ({escape(dataset_label)}) contains {summary['shipment_count']} shipments and {summary['route_option_count']} route options. The synthetic generator uses four route archetypes to create deliberate tradeoffs: economy (lower cost, longer transit), balanced, express (faster, higher cost), and resilient (higher cost, lower delay and risk). A fixed seed makes each generated dataset repeatable.",
            styles["body"],
        ),
        make_paragraph("AI decision method: weighted-sum MCDA", styles["heading"]),
    ]

    objective_rows = [
        [make_paragraph("Objective", styles["table_header"]), make_paragraph("Metric and fixed reference", styles["table_header"]), make_paragraph("Interpretation", styles["table_header"])],
        [make_paragraph("Cost", styles["table_cell"]), make_paragraph("Route cost / USD 10,000", styles["table_cell"]), make_paragraph("Lower spend is preferred.", styles["table_cell"])],
        [make_paragraph("Time", styles["table_cell"]), make_paragraph("Planned transit days / 45", styles["table_cell"]), make_paragraph("Shorter planned transit is preferred.", styles["table_cell"])],
        [make_paragraph("Reliability", styles["table_cell"]), make_paragraph("Delay probability / 0.30", styles["table_cell"]), make_paragraph("Lower modeled delay likelihood is preferred.", styles["table_cell"])],
        [make_paragraph("Operational risk", styles["table_cell"]), make_paragraph("Risk index / 0.50", styles["table_cell"]), make_paragraph("Index is the mean of congestion and geopolitical risk.", styles["table_cell"])],
    ]
    story.append(build_table(objective_rows, [1.02 * inch, 2.13 * inch, 4.10 * inch], header=True))
    story.extend(
        [
            Spacer(1, 5),
            make_paragraph(
                "The named method is the Weighted Sum Model (WSM), a multi-criteria decision analysis (MCDA) approach. For a feasible route, score = w_cost * cost_norm + w_time * time_norm + w_delay * delay_norm + w_risk * risk_norm. Weights are non-negative and sum to 1; lower scores are preferred. Pareto-dominance analysis identifies non-dominated options. The deterministic model makes the decision reproducible; its values are example parameters, not learned or industry-calibrated values.",
                styles["body"],
            ),
            make_paragraph(
                "Feasibility is checked first against the shipment's optional cost, transit-time, and risk limits. Route cost and planned time are summed from legs. Route delay probability is 1 - product(1 - leg probability), assuming independent leg delays. Congestion and geopolitical scores are transit-time-weighted averages across legs.",
                styles["body"],
            ),
            make_paragraph("Implementation", styles["heading"]),
            make_paragraph(
                "The schema module turns JSON records into data objects. The scoring module aggregates leg values, checks service limits, and ranks feasible routes. The Streamlit app supports data generation, JSON upload, shipment selection, and route recommendations. Evaluation and PDF reporting are available as separate pipelines.",
                styles["body"],
            ),
            make_paragraph("Example priority presets", styles["heading"]),
            build_table(profile_rows, [1.65 * inch, 5.60 * inch], header=True),
            PageBreak(),
            make_paragraph("Evaluation and limitations", styles["title"]),
            make_paragraph(f"Decision metrics below were calculated from {escape(dataset_label)}.", styles["subtitle"]),
            make_paragraph("Evaluation snapshot", styles["heading"]),
        ]
    )

    metrics = summary["average_selected_metrics"]
    regrets = summary["average_normalized_regret_vs_single_objective_best"]
    mean_selected_text = (
        f"${metrics['cost_usd']:,.0f}; {metrics['transit_days']:.1f} days; "
        f"{metrics['delay_probability']:.1%} delay; risk {metrics['risk_index']:.3f}"
        if metrics["cost_usd"] is not None
        else "No feasible recommendations."
    )
    regret_text = "; ".join(
        f"{name} {value:.3f}" for name, value in regrets.items() if value is not None
    ) or "No feasible recommendations."
    evaluation_rows = [
        [make_paragraph("Measure", styles["table_header"]), make_paragraph("Result", styles["table_header"]), make_paragraph("What it says", styles["table_header"])],
        [make_paragraph("Recommendation coverage", styles["table_cell"]), make_paragraph(f"{summary['recommendations_made']} / {summary['shipment_count']} ({summary['feasibility_rate']:.0%})", styles["table_cell"]), make_paragraph("Share of shipments with at least one feasible recommendation.", styles["table_cell"])],
        [make_paragraph("Pareto-frontier selection", styles["table_cell"]), make_paragraph(f"{summary['pareto_selection_rate']:.0%}", styles["table_cell"]), make_paragraph("Share of selected routes not dominated on all four objectives.", styles["table_cell"])],
        [make_paragraph("Mean selected route", styles["table_cell"]), make_paragraph(mean_selected_text, styles["table_cell"]), make_paragraph("Average across each shipment's weighted recommendation.", styles["table_cell"])],
        [make_paragraph("Mean normalized gap from single-objective best", styles["table_cell"]), make_paragraph(regret_text, styles["table_cell"]), make_paragraph("Cost of balancing objectives versus each feasible per-shipment extreme; smaller is closer to that extreme.", styles["table_cell"])],
    ]
    story.append(build_table(evaluation_rows, [1.53 * inch, 1.72 * inch, 4.00 * inch], header=True))

    story.extend(
        [
            Spacer(1, 6),
            make_paragraph("Preference sensitivity", styles["heading"]),
            make_paragraph(
                f"The evaluation also re-runs each shipment under all four priority profiles "
                f"({summary['priority_scenarios_evaluated']} shipment-profile scenarios). "
                f"{summary['shipments_with_alternative_winner']} of {summary['shipment_count']} "
                "shipments change route family across those profiles. This shows that the stated "
                "preferences affect the decision on the selected dataset; it is not evidence "
                "that the profiles represent real operator behavior.",
                styles["small"],
            ),
        ]
    )
    family_names = ("economy", "balanced", "express", "resilient")
    sensitivity_rows = [
        [make_paragraph("Priority", styles["table_header"])]
        + [make_paragraph(family.title(), styles["table_header"]) for family in family_names]
    ]
    for profile_name, family_counts in summary["route_family_by_priority_profile"].items():
        sensitivity_rows.append(
            [make_paragraph(escape(profile_name.replace("_", " ")), styles["table_cell"])]
            + [
                make_paragraph(str(family_counts.get(family, 0)), styles["table_cell"])
                for family in family_names
            ]
        )
    story.append(
        build_table(
            sensitivity_rows,
            [1.65 * inch, 1.40 * inch, 1.40 * inch, 1.40 * inch, 1.40 * inch],
            header=True,
        )
    )

    if selected is not None:
        runner = example.feasible_routes[1] if len(example.feasible_routes) > 1 else None
        if runner:
            example_text = (
                f"For {first.shipment_id} ({first.origin} to {first.destination}), the model selects "
                f"{selected.route.route_id} ({selected.route.name}) at score {selected.score:.3f}: "
                f"${selected.metrics.cost_usd:,.0f}, {selected.metrics.transit_days:.1f} days, "
                f"{selected.metrics.delay_probability:.1%} delay probability, risk {selected.metrics.risk_index:.3f}. "
                f"Its runner-up is {runner.route.route_id} at {runner.score:.3f}."
            )
        else:
            example_text = (
                f"For {first.shipment_id}, the selected route is {selected.route.route_id} "
                f"({selected.route.name}) at score {selected.score:.3f}; it is the only feasible option."
            )
        story.extend([Spacer(1, 6), make_paragraph("Example decision", styles["heading"]), make_paragraph(example_text, styles["body"])])

    profile_summary = ", ".join(
        f"{name.replace('_', ' ')}: {count}" for name, count in summary["priority_profile_counts"].items()
    )
    story.extend(
        [
            make_paragraph("Limitations", styles["heading"]),
            make_paragraph(
                "Generated synthetic values are not calibrated to carriers, ports, current conditions, or observed outcomes; uploaded data also needs validation for its operating context. The independent-delay assumption can understate correlated disruptions. Composite risk hides differences between its two components unless the explanation is inspected. Weights and fixed reference scales encode a policy choice; stakeholders must approve them for operational use. The model recommends one shipment at a time and does not optimize fleet capacity or network interactions.",
                styles["body"],
            ),
            make_paragraph(f"The selected dataset covers these preference profiles: {escape(profile_summary)}.", styles["small"]),
            make_paragraph("Reproduction", styles["heading"]),
            make_paragraph(
                "Open the Streamlit app with <font name='Courier'>python -m streamlit run src/ui/app.py</font> to generate shipment data and get route recommendations. Run it with Docker using <font name='Courier'>docker compose up --build -d</font> on port 8501. The assessment context document is in the static folder.",
                styles["body"],
            ),
        ]
    )

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    logger.info(f"Technical report created at {target}")
    return target


