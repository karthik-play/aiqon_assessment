"""Generate repeatable sample shipments with varied route options."""

import random
from typing import Any

from src.core.config import (
    BASE_COST_RANGE_USD,
    BASE_TRANSIT_RANGE_DAYS,
    COST_SAVER_BUDGET_FACTOR,
    DEFAULT_BUDGET_FACTOR,
    DEFAULT_SHIPMENT_COUNT,
    DEFAULT_MAX_RISK_INDEX,
    DEFAULT_ROUTE_MODE,
    DEFAULT_SEED,
    DESTINATIONS,
    HUBS,
    LEG_SPLIT_WEIGHT_RANGE,
    ORIGINS,
    PRIORITY_PROFILES,
    ROUTE_PROFILES,
    SYNTHETIC_LEG_DELAY_BOUNDS,
    SYNTHETIC_LEG_DELAY_VARIATION_RANGE,
    SYNTHETIC_RISK_BOUNDS,
    SYNTHETIC_RISK_SPREAD,
    SYNTHETIC_TOTAL_VARIATION_RANGE,
    TIME_CRITICAL_DEADLINE_FACTOR,
    DEFAULT_DEADLINE_FACTOR,
)
from src.core.logger import get_logger


logger = get_logger(__name__)


def split_values(total: float, count: int, rng: random.Random) -> list[float]:
    weights = [rng.uniform(*LEG_SPLIT_WEIGHT_RANGE) for _ in range(count)]
    denominator = sum(weights)
    return [total * weight / denominator for weight in weights]


def calculate_risk_value(center: float, rng: random.Random, spread: float = SYNTHETIC_RISK_SPREAD) -> float:
    minimum, maximum = SYNTHETIC_RISK_BOUNDS
    return max(minimum, min(maximum, center + rng.uniform(-spread, spread)))


def build_route(
    shipment_id: str,
    origin: str,
    destination: str,
    base_cost: float,
    base_days: float,
    profile: dict[str, Any],
    route_number: int,
    rng: random.Random,
):
    try:
        leg_count = int(profile["legs"])
        via = rng.sample(HUBS, leg_count - 1)
        stops = [origin, *via, destination]
        cost_variation = rng.uniform(*SYNTHETIC_TOTAL_VARIATION_RANGE)
        time_variation = rng.uniform(*SYNTHETIC_TOTAL_VARIATION_RANGE)
        total_cost = base_cost * float(profile["cost_factor"]) * cost_variation
        total_days = base_days * float(profile["time_factor"]) * time_variation
        costs = split_values(total_cost, leg_count, rng)
        days = split_values(total_days, leg_count, rng)

        target_delay = float(profile["delay"])
        base_leg_delay = 1.0 - (1.0 - target_delay) ** (1.0 / leg_count)
        legs = []
        for index in range(leg_count):
            delay_minimum, delay_maximum = SYNTHETIC_LEG_DELAY_BOUNDS
            leg_delay = max(
                delay_minimum,
                min(
                    delay_maximum,
                    base_leg_delay * rng.uniform(*SYNTHETIC_LEG_DELAY_VARIATION_RANGE),
                ),
            )
            legs.append(
                {
                    "leg_id": f"{shipment_id}-R{route_number}-L{index + 1}",
                    "origin": stops[index],
                    "destination": stops[index + 1],
                    "mode": DEFAULT_ROUTE_MODE,
                    "cost_usd": round(costs[index], 2),
                    "transit_days": round(days[index], 2),
                    "delay_probability": round(leg_delay, 4),
                    "congestion_risk": round(
                        calculate_risk_value(float(profile["congestion"]), rng), 4
                    ),
                    "geopolitical_risk": round(
                        calculate_risk_value(float(profile["geopolitical"]), rng), 4
                    ),
                }
            )

        return {
            "route_id": f"{shipment_id}-R{route_number}",
            "name": str(profile["name"]),
            "legs": legs,
        }
    except Exception as e:
        logger.error("")
        raise


def generate_shipments(shipment_count: int = DEFAULT_SHIPMENT_COUNT, seed: int = DEFAULT_SEED):
    if shipment_count <= 0:
        logger.warning(f"Cannot generate a dataset with shipment_count={shipment_count}")
        raise ValueError("shipment_count must be positive.")
    logger.info(f"Generating {shipment_count} synthetic shipment(s) with seed {seed}")
    rng = random.Random(seed)
    profile_names = tuple(PRIORITY_PROFILES)
    shipments = []

    for index in range(shipment_count):
        shipment_id = f"SHP-{index + 1:03d}"
        origin = ORIGINS[index % len(ORIGINS)]
        destination = DESTINATIONS[(index * 2 + index // len(ORIGINS)) % len(DESTINATIONS)]
        while destination == origin:
            destination = DESTINATIONS[(DESTINATIONS.index(destination) + 1) % len(DESTINATIONS)]

        priority_profile = profile_names[index % len(profile_names)]
        base_cost = rng.uniform(*BASE_COST_RANGE_USD)
        base_days = rng.uniform(*BASE_TRANSIT_RANGE_DAYS)
        routes = [
            build_route(
                shipment_id,
                origin,
                destination,
                base_cost,
                base_days,
                route_profile,
                route_number + 1,
                rng,
            )
            for route_number, route_profile in enumerate(ROUTE_PROFILES)
        ]

        # Tighten the budget or deadline for the matching priority profile.
        budget_factor = (
            COST_SAVER_BUDGET_FACTOR
            if priority_profile == "cost_saver"
            else DEFAULT_BUDGET_FACTOR
        )
        deadline_factor = (
            TIME_CRITICAL_DEADLINE_FACTOR
            if priority_profile == "time_critical"
            else DEFAULT_DEADLINE_FACTOR
        )
        shipments.append(
            {
                "shipment_id": shipment_id,
                "origin": origin,
                "destination": destination,
                "priority_profile": priority_profile,
                "weights": PRIORITY_PROFILES[priority_profile],
                "constraints": {
                    "max_cost_usd": round(base_cost * budget_factor, 2),
                    "max_transit_days": round(base_days * deadline_factor, 2),
                    "max_risk_index": DEFAULT_MAX_RISK_INDEX,
                },
                "routes": routes,
            }
        )

    logger.info(f"Generated {len(shipments)} synthetic shipment(s)")
    return shipments


