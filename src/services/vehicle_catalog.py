"""Vehicle catalog management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class VehicleType:
    """Definition of a candidate vehicle."""

    name: str
    capacity_kg: int
    fixed_cost: float
    per_km_cost: float
    fixed_cost_per_km: float = 0.0
    energy_consumption_kwh_per_km: float = 0.0  # エネルギー消費量 (kWh/km)

    def distance_cost(self, distance_m: float) -> float:
        """Compute variable cost for a given distance in metres."""

        return self.per_km_cost * (distance_m / 1000.0)

    def fixed_cost_for_distance(self, distance_m: float) -> float:
        """Return fixed cost that scales with travelled distance."""

        return self.fixed_cost + self.fixed_cost_per_km * (distance_m / 1000.0)

    def energy_consumption_kwh(self, distance_m: float) -> float:
        """
        走行距離からエネルギー消費量を計算

        Args:
            distance_m: 走行距離（メートル）

        Returns:
            エネルギー消費量（kWh）
        """
        distance_km = distance_m / 1000.0
        return self.energy_consumption_kwh_per_km * distance_km


@dataclass
class VehicleCatalog:
    """Stores vehicle candidates and provides helper queries."""

    _vehicles: Dict[str, VehicleType] = field(default_factory=dict)
    _order: List[str] = field(default_factory=list)

    def add_vehicle(
        self,
        name: str,
        capacity: int,
        fixed_cost: float,
        per_km_cost: float,
        fixed_cost_per_km: float = 0.0,
        energy_consumption_kwh_per_km: float = 0.0,
    ) -> VehicleType:
        """Add or replace a vehicle definition."""

        vehicle = VehicleType(
            name=name,
            capacity_kg=max(0, int(capacity)),
            fixed_cost=float(fixed_cost),
            per_km_cost=float(per_km_cost),
            fixed_cost_per_km=float(fixed_cost_per_km),
            energy_consumption_kwh_per_km=float(energy_consumption_kwh_per_km),
        )
        if name not in self._vehicles:
            self._order.append(name)
        self._vehicles[name] = vehicle
        return vehicle

    def remove_vehicle(self, name: str) -> None:
        """Remove a vehicle from the catalog."""

        if name in self._vehicles:
            self._vehicles.pop(name)
            self._order = [n for n in self._order if n != name]

    def get_vehicle(self, name: str) -> VehicleType:
        """Retrieve a vehicle by name."""

        try:
            return self._vehicles[name]
        except KeyError as exc:
            raise KeyError(f"Unknown vehicle: {name}") from exc

    def list_vehicles(self) -> List[VehicleType]:
        """Return vehicles preserving insertion order."""

        return [self._vehicles[name] for name in self._order]

    def valid_vehicles(self, total_demand: int) -> List[VehicleType]:
        """Return vehicles whose capacity can cover the given demand."""

        demand = max(0, int(total_demand))
        return [v for v in self.list_vehicles() if v.capacity_kg >= demand]

    def __iter__(self) -> Iterable[VehicleType]:
        return iter(self.list_vehicles())

    def clear(self) -> None:
        self._vehicles.clear()
        self._order.clear()
