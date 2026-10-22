"""Build a ranked route recommendation for one shipment."""

from src.core.schemas import PriorityWeights, Recommendation, ShipmentRequest
from src.core.scoring import score_shipment


def recommend(shipment: ShipmentRequest, weights: PriorityWeights | None = None, priority_profile: str | None = None):
    """Score the shipment's routes and return them in rank order."""
    effective_weights = weights if weights is not None else shipment.weights
    effective_profile = priority_profile if priority_profile is not None else shipment.priority_profile
    ranked_routes = score_shipment(shipment, effective_weights)
    return Recommendation(
        shipment=shipment,
        weights=effective_weights,
        priority_profile=effective_profile,
        ranked_routes=tuple(ranked_routes),
    )
