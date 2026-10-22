"""Summarize route recommendation results for a dataset."""

from collections import Counter
from statistics import mean

from src.components.recommendation import recommend
from src.core.config import OBJECTIVES, PRIORITY_PROFILES
from src.core.logger import get_logger
from src.core.scoring import pareto_frontier, score_shipment
from src.core.schemas import PriorityWeights, ShipmentRequest


logger = get_logger(__name__)


def run_evaluation(shipments: list[ShipmentRequest]) -> dict[str, object]:
    selected_routes = []
    profile_counts = Counter()
    feasible_shipments = 0
    pareto_selected = 0
    regrets = {objective: [] for objective in OBJECTIVES}
    priority_route_counts = {
        profile: Counter() for profile in PRIORITY_PROFILES
    }
    shipments_with_alternative_winner = 0
    priority_scenario_count = 0

    for shipment in shipments:
        profile_counts[shipment.priority_profile] += 1
        candidates = score_shipment(shipment)
        feasible = [candidate for candidate in candidates if candidate.feasible]
        if not feasible:
            continue

        feasible_shipments += 1
        result = recommend(shipment)
        selected = result.selected
        if selected is None:
            continue
        selected_routes.append(selected)
        frontier_ids = {candidate.route.route_id for candidate in pareto_frontier(candidates)}
        if selected.route.route_id in frontier_ids:
            pareto_selected += 1

        selected_normalized = selected.metrics.normalized()
        best_by_objective = {
            objective: min(candidate.metrics.normalized()[objective] for candidate in feasible)
            for objective in OBJECTIVES
        }
        for objective in OBJECTIVES:
            regrets[objective].append(selected_normalized[objective] - best_by_objective[objective])

        winners_for_shipment = set()
        for profile in PRIORITY_PROFILES:
            priority_scenario_count += 1
            profile_result = recommend(
                shipment,
                PriorityWeights.for_profile(profile),
                profile,
            )
            profile_winner = profile_result.selected
            family = (
                profile_winner.route.name.split("/", 1)[0].strip().lower()
                if profile_winner is not None
                else "no_feasible_route"
            )
            priority_route_counts[profile][family] += 1
            winners_for_shipment.add(family)
        if len(winners_for_shipment) > 1:
            shipments_with_alternative_winner += 1

    count = len(shipments)
    selected_count = len(selected_routes)
    def mean_or_none(values: list[float]) -> float | None:
        return round(mean(values), 4) if values else None

    summary = {
        "shipment_count": count,
        "route_option_count": sum(len(shipment.routes) for shipment in shipments),
        "recommendations_made": selected_count,
        "feasibility_rate": round(feasible_shipments / count, 4) if count else 0.0,
        "pareto_selection_rate": round(pareto_selected / selected_count, 4) if selected_count else 0.0,
        "priority_profile_counts": dict(sorted(profile_counts.items())),
        "priority_scenarios_evaluated": priority_scenario_count,
        "shipments_with_alternative_winner": shipments_with_alternative_winner,
        "route_family_by_priority_profile": {
            profile: dict(sorted(families.items()))
            for profile, families in priority_route_counts.items()
        },
        "average_selected_metrics": {
            "cost_usd": mean_or_none([route.metrics.cost_usd for route in selected_routes]),
            "transit_days": mean_or_none([route.metrics.transit_days for route in selected_routes]),
            "delay_probability": mean_or_none(
                [route.metrics.delay_probability for route in selected_routes]
            ),
            "risk_index": mean_or_none([route.metrics.risk_index for route in selected_routes]),
        },
        "average_normalized_regret_vs_single_objective_best": {
            objective: mean_or_none(values) for objective, values in regrets.items()
        },
    }
    logger.info(
        f"Evaluation complete: {count} shipment(s), {selected_count} recommendations, "
        f"{summary['pareto_selection_rate'] * 100:.1f}% Pareto selection rate"
    )
    logger.info(
        f"Preference sensitivity: {shipments_with_alternative_winner} of {count} "
        "shipment(s) changed route family"
    )
    return summary


