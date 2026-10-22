"""Generate reproducible synthetic shipment data for the Streamlit app."""

from src.components.synthetic_data import generate_shipments
from src.core.config import DEFAULT_SEED, DEFAULT_SHIPMENT_COUNT


def generate_dataset(
    shipment_count: int = DEFAULT_SHIPMENT_COUNT,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, object]]:
    """Generate shipments with the selected count and seed."""
    return generate_shipments(shipment_count, seed)
