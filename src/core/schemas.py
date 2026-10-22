from typing import Any, Mapping
from dataclasses import dataclass
from src.core.config import DEFAULT_ROUTE_MODE, PRIORITY_PROFILES, REFERENCE_SCALES


@dataclass(frozen=True)
class PriorityWeights:

    cost: float
    time: float
    delay: float
    risk: float

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "PriorityWeights":
        return cls(
            cost=float(values["cost"]),
            time=float(values["time"]),
            delay=float(values["delay"]),
            risk=float(values["risk"]),
        )

    @classmethod
    def for_profile(cls, name: str) -> "PriorityWeights":
        return cls.from_mapping(PRIORITY_PROFILES[name])


@dataclass(frozen=True)
class ShipmentConstraints:
    max_cost_usd: float | None = None
    max_transit_days: float | None = None
    max_risk_index: float | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "ShipmentConstraints":
        values = values or {}
        return cls(
            max_cost_usd=( float(values["max_cost_usd"]) if values.get("max_cost_usd") is not None else None),
            max_transit_days=( float(values["max_transit_days"]) if values.get("max_transit_days") is not None else None),
            max_risk_index=( float(values["max_risk_index"]) if values.get("max_risk_index") is not None else None),
        )


@dataclass(frozen=True)
class RouteLeg:
    leg_id: str
    origin: str
    destination: str
    mode: str
    cost_usd: float
    transit_days: float
    delay_probability: float
    congestion_risk: float
    geopolitical_risk: float

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "RouteLeg":
        return cls(
            leg_id=str(values["leg_id"]),
            origin=str(values["origin"]),
            destination=str(values["destination"]),
            mode=str(values.get("mode", DEFAULT_ROUTE_MODE)),
            cost_usd=float(values["cost_usd"]),
            transit_days=float(values["transit_days"]),
            delay_probability=float(values["delay_probability"]),
            congestion_risk=float(values["congestion_risk"]),
            geopolitical_risk=float(values["geopolitical_risk"]),
        )


@dataclass(frozen=True)
class RouteOption:
    route_id: str
    name: str
    legs: tuple[RouteLeg, ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "RouteOption":
        route_id = str(values["route_id"])
        legs = tuple(RouteLeg.from_mapping(leg) for leg in values["legs"])
        if not legs:
            raise ValueError(f"Route {route_id} must have at least one leg.")
        return cls(route_id=route_id, name=str(values.get("name", route_id)), legs=legs)


@dataclass(frozen=True)
class ShipmentRequest:
    shipment_id: str
    origin: str
    destination: str
    priority_profile: str
    weights: PriorityWeights
    constraints: ShipmentConstraints
    routes: tuple[RouteOption, ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "ShipmentRequest":
        profile = str(values.get("priority_profile", "balanced"))
        raw_weights = values.get("weights")
        return cls(
            shipment_id=str(values["shipment_id"]),
            origin=str(values["origin"]),
            destination=str(values["destination"]),
            priority_profile=profile,
            weights=(PriorityWeights.from_mapping(raw_weights) if raw_weights is not None else PriorityWeights.for_profile(profile)),
            constraints=ShipmentConstraints.from_mapping(values.get("constraints")),
            routes=tuple(RouteOption.from_mapping(route) for route in values["routes"]),
        )


@dataclass(frozen=True)
class RouteMetrics:
    cost_usd: float
    transit_days: float
    delay_probability: float
    congestion_risk: float
    geopolitical_risk: float
    risk_index: float

    def normalized(self) -> dict[str, float]:
        return {
            "cost": self.cost_usd / REFERENCE_SCALES["cost"],
            "time": self.transit_days / REFERENCE_SCALES["time"],
            "delay": self.delay_probability / REFERENCE_SCALES["delay"],
            "risk": self.risk_index / REFERENCE_SCALES["risk"],
        }


@dataclass(frozen=True)
class ScoredRoute:
    route: RouteOption
    metrics: RouteMetrics
    score: float
    score_components: dict[str, float]
    violations: tuple[str, ...]

    @property
    def feasible(self) -> bool:
        return not self.violations


@dataclass(frozen=True)
class Recommendation:
    shipment: ShipmentRequest
    weights: PriorityWeights
    priority_profile: str
    ranked_routes: tuple[ScoredRoute, ...]

    @property
    def feasible_routes(self) -> tuple[ScoredRoute, ...]:
        return tuple(route for route in self.ranked_routes if route.feasible)

    @property
    def selected(self) -> ScoredRoute | None:
        return self.feasible_routes[0] if self.feasible_routes else None