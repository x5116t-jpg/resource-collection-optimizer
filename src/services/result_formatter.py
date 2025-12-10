"""Helpers to turn raw optimisation output into presentation structures."""

from __future__ import annotations

from typing import Dict, Sequence

from .optimizer import Solution
from .vehicle_catalog import VehicleType


def format_solution(
    route: Sequence[str],
    vehicle: VehicleType,
    total_distance_m: float,
    cost_breakdown: Dict[str, float],
) -> Solution:
    """Create a :class:`Solution` instance from primitive values."""

    total_cost = cost_breakdown.get("total_cost")
    if total_cost is None:
        total_cost = cost_breakdown.get("fixed_cost", 0.0) + cost_breakdown.get("distance_cost", 0.0)
        cost_breakdown = {**cost_breakdown, "total_cost": total_cost}
    return Solution(
        vehicle=vehicle,
        order=list(route),
        total_distance_m=float(total_distance_m),
        cost_breakdown=dict(cost_breakdown),
    )
