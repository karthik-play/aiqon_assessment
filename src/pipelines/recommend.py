"""Recommend a route using the shipment's stored weights and limits."""

from src.components.recommendation import recommend
from src.core.schemas import PriorityWeights, Recommendation, ShipmentRequest


def recommend_shipment(
    shipment: ShipmentRequest,
    weights: PriorityWeights | None = None,
    priority_profile: str | None = None,
) -> Recommendation:
    """Recommend a route using the shipment's stored weights and limits."""
    return recommend(shipment, weights, priority_profile)
