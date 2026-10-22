import math
from src.core.config import COMPARISON_TOLERANCE, OBJECTIVES
from src.core.schemas import (
    PriorityWeights,
    RouteMetrics,
    RouteOption,
    ScoredRoute,
    ShipmentRequest,
)
from src.core.logger import get_logger


logger = get_logger(__name__)


def aggregate_route_metrics(route: RouteOption):
    cost = sum(leg.cost_usd for leg in route.legs)
    transit = sum(leg.transit_days for leg in route.legs)
    no_delay_probability = math.prod(1.0 - leg.delay_probability for leg in route.legs)
    delay_probability = 1.0 - no_delay_probability

    if transit > 0.0:
        congestion = sum(leg.congestion_risk * leg.transit_days for leg in route.legs) / transit
        geopolitical = sum(leg.geopolitical_risk * leg.transit_days for leg in route.legs) / transit
    else:
        congestion = sum(leg.congestion_risk for leg in route.legs) / len(route.legs)
        geopolitical = sum(leg.geopolitical_risk for leg in route.legs) / len(route.legs)

    return RouteMetrics(
        cost_usd=cost,
        transit_days=transit,
        delay_probability=delay_probability,
        congestion_risk=congestion,
        geopolitical_risk=geopolitical,
        risk_index=(congestion + geopolitical) / 2.0,
    )


def constraint_violations(shipment: ShipmentRequest, metrics: RouteMetrics):
    limits = shipment.constraints
    violations = []
    if limits.max_cost_usd is not None and metrics.cost_usd > limits.max_cost_usd + COMPARISON_TOLERANCE:
        violations.append(f"cost ${metrics.cost_usd:,.0f} exceeds ${limits.max_cost_usd:,.0f} budget")
    if limits.max_transit_days is not None and metrics.transit_days > limits.max_transit_days + COMPARISON_TOLERANCE:
        violations.append(f"transit time {metrics.transit_days:.1f} days exceeds {limits.max_transit_days:.1f}-day limit")
    if limits.max_risk_index is not None and metrics.risk_index > limits.max_risk_index + COMPARISON_TOLERANCE:
        violations.append(f"risk index {metrics.risk_index:.3f} exceeds {limits.max_risk_index:.3f} limit")
    return tuple(violations)


def score_route(shipment: ShipmentRequest, route: RouteOption, weights: PriorityWeights | None = None):
    metrics = aggregate_route_metrics(route)
    weights = weights or shipment.weights
    normalized = metrics.normalized()
    components = {
        metric: getattr(weights, metric) * normalized[metric]
        for metric in OBJECTIVES
    }
    scored = ScoredRoute(
        route=route,
        metrics=metrics,
        score=sum(components.values()),
        score_components=components,
        violations=constraint_violations(shipment, metrics),
    )
    logger.info(f"Scored route {route.route_id} for shipment {shipment.shipment_id}: feasible={scored.feasible} score={scored.score:.4f}")
    return scored


def score_shipment(shipment: ShipmentRequest, weights: PriorityWeights | None = None):
    scored = [score_route(shipment, route, weights) for route in shipment.routes]
    ranked = sorted(
        scored,
        key=lambda item: (
            not item.feasible,
            item.score if item.feasible else float("inf"),
            item.score,
            item.route.route_id,
        ),
    )
    feasible_count = sum(route.feasible for route in ranked)
    logger.info(f"Ranked {len(ranked)} route option(s) for shipment {shipment.shipment_id} {feasible_count} are feasible")
    return ranked


def dominates(left: ScoredRoute, right: ScoredRoute, tolerance: float = COMPARISON_TOLERANCE) -> bool:
    left_values = left.metrics.normalized()
    right_values = right.metrics.normalized()
    keys = OBJECTIVES
    no_worse = all(left_values[key] <= right_values[key] + tolerance for key in keys)
    strictly_better = any(left_values[key] < right_values[key] - tolerance for key in keys)
    return no_worse and strictly_better


def pareto_frontier(routes: list[ScoredRoute]) -> list[ScoredRoute]:
    feasible = [route for route in routes if route.feasible]
    frontier = [
        candidate
        for candidate in feasible
        if not any(other is not candidate and dominates(other, candidate) for other in feasible)
    ]
    logger.info(f"Identified {len(frontier)} Pareto-efficient route(s) from {len(feasible)} feasible option(s)")
    return frontier
