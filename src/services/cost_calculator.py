"""Shared cost calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, Optional

from .vehicle_catalog import VehicleType
from .master_repository import VehicleCandidate


def _to_decimal(value: float) -> Decimal:
    """Safely convert floats (or float-like values) to ``Decimal`` for currency math."""

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):  # pragma: no cover - defensive
        return Decimal(0)


@dataclass(frozen=True)
class CostComponents:
    """Structured representation of cost calculation results."""

    fixed_cost: int
    distance_cost: int
    total_cost: int
    distance_km: float
    energy_kwh: Optional[float] = None
    # NOTE: details contains both currency amounts (yen, integer-ish) and reference values (e.g. yen/kg).
    details: Dict[str, float] = field(default_factory=dict)


class CostCalculator:
    """Centralised component that evaluates vehicle costs consistently."""

    def __init__(self, rounding=ROUND_HALF_UP) -> None:
        self.rounding = rounding

    def _round_currency(self, value: Decimal) -> int:
        return int(value.quantize(Decimal("1"), rounding=self.rounding))

    def _distance_km(self, distance_m: float) -> Decimal:
        return _to_decimal(distance_m) / Decimal("1000")

    def evaluate(
        self,
        vehicle: VehicleType,
        distance_m: float,
        metadata: Optional[VehicleCandidate] = None,
        total_demand_kg: int = 0,
    ) -> CostComponents:
        """Compute cost components for a vehicle travelling ``distance_m`` metres."""

        distance_km_dec = self._distance_km(distance_m)
        details: Dict[str, float] = {}

        if metadata:
            # 詳細内訳がある場合は「合計と内訳の合計が必ず一致する」ことを優先する。
            # 端数処理の順序が異なると、(単価合計×距離) と (各項目×距離の丸め後合計) が数円ずれるため。
            variable_details: Dict[str, int] = {}
            variable_refs: Dict[str, float] = {}
            fixed_details: Dict[str, int] = {}
            self._append_variable_details(
                variable_details,
                variable_refs,
                metadata,
                distance_km_dec,
                total_demand_kg=max(0, int(total_demand_kg)),
            )
            self._append_fixed_details(fixed_details, metadata, distance_km_dec)

            # 車両定義の fixed_cost は「距離に依らない固定費（1回あたり）」として扱う。
            base_fixed_cost = self._round_currency(_to_decimal(vehicle.fixed_cost))
            if base_fixed_cost != 0:
                fixed_details["固定費_基本固定費"] = base_fixed_cost

            details.update({k: float(v) for k, v in variable_details.items()})
            details.update(variable_refs)
            details.update({k: float(v) for k, v in fixed_details.items()})

            # 内訳が存在するカテゴリは内訳合計を採用（表示/検証の一貫性を担保）
            if variable_details:
                distance_cost = int(sum(int(v) for v in variable_details.values()))
            else:
                distance_cost = self._round_currency(_to_decimal(vehicle.per_km_cost) * distance_km_dec)

            if fixed_details:
                fixed_cost = int(sum(int(v) for v in fixed_details.values()))
            else:
                fixed_cost = self._round_currency(
                    _to_decimal(vehicle.fixed_cost) + _to_decimal(vehicle.fixed_cost_per_km) * distance_km_dec
                )
        else:
            fixed_cost = self._round_currency(
                _to_decimal(vehicle.fixed_cost) + _to_decimal(vehicle.fixed_cost_per_km) * distance_km_dec
            )
            distance_cost = self._round_currency(_to_decimal(vehicle.per_km_cost) * distance_km_dec)

        total_cost = int(fixed_cost) + int(distance_cost)

        energy_kwh = None
        if vehicle.energy_consumption_kwh_per_km > 0:
            energy_kwh = round(float(vehicle.energy_consumption_kwh_per_km) * float(distance_km_dec), 3)

        return CostComponents(
            fixed_cost=fixed_cost,
            distance_cost=distance_cost,
            total_cost=total_cost,
            distance_km=float(distance_km_dec),
            energy_kwh=energy_kwh,
            details=details,
        )

    def _append_variable_details(
        self,
        details: Dict[str, int],
        refs: Dict[str, float],
        metadata: VehicleCandidate,
        distance_km_dec: Decimal,
        total_demand_kg: int,
    ) -> None:
        # 変動費は必要最小項目に限定する:
        # - 燃料費(円/km)
        # - 損料(円/km) ※タイヤ+修理を集約したもの
        # - 運転手人件費(円/h) -> 距離/平均速度で計算
        # - 作業時間人件費(円/kg) -> 総重量×作業効率で計算
        breakdown = metadata.variable_cost_breakdown or {}

        # fuel / damage (yen per km)
        for item_name in ("燃料費_円_per_km", "損料_円_per_km"):
            if item_name not in breakdown:
                continue
            unit_cost = breakdown.get(item_name) or 0.0
            item_key = f"変動費_{item_name}"
            try:
                amount = self._round_currency(_to_decimal(unit_cost) * distance_km_dec)
            except InvalidOperation:  # pragma: no cover - defensive
                continue
            details[item_key] = amount

        # driver labor cost (yen per hour)
        hourly_wage = float(metadata.hourly_wage or 0.0)
        average_speed = float(metadata.average_speed_km_per_h or 0.0)
        if hourly_wage > 0 and average_speed > 0 and float(distance_km_dec) > 0:
            hours = _to_decimal(float(distance_km_dec)) / _to_decimal(average_speed)
            details["変動費_運転手人件費"] = self._round_currency(_to_decimal(hourly_wage) * hours)

        # loading labor cost (yen per kg)
        loading_sec_per_kg = float(metadata.loading_time_per_kg or 0.0)
        if hourly_wage > 0 and loading_sec_per_kg > 0 and total_demand_kg > 0:
            hours = (_to_decimal(total_demand_kg) * _to_decimal(loading_sec_per_kg)) / Decimal("3600")
            details["変動費_作業時間人件費"] = self._round_currency(_to_decimal(hourly_wage) * hours)
            # Reference key for UI display (not counted in distance_cost)
            unit_yen_per_kg = (_to_decimal(hourly_wage) * _to_decimal(loading_sec_per_kg)) / Decimal("3600")
            refs["変動費_作業時間人件費_円_per_kg"] = float(unit_yen_per_kg)

    def _append_fixed_details(
        self,
        details: Dict[str, int],
        metadata: VehicleCandidate,
        distance_km_dec: Decimal,
    ) -> None:
        breakdown = metadata.fixed_cost_breakdown or {}
        annual_distance = metadata.annual_distance_km or 0
        if annual_distance <= 0:
            return
        annual_distance_dec = _to_decimal(annual_distance)
        for item_name, manyen_value in breakdown.items():
            item_key = f"固定費_{item_name}"
            try:
                annual_yen = _to_decimal(manyen_value) * Decimal("10000")
                per_km = annual_yen / annual_distance_dec
                amount = self._round_currency(per_km * distance_km_dec)
            except (InvalidOperation, ZeroDivisionError):  # pragma: no cover - defensive
                continue
            details[item_key] = amount


def cost_components_to_breakdown(components: CostComponents) -> Dict[str, float]:
    """Convert ``CostComponents`` to the legacy ``cost_breakdown`` dict format."""

    breakdown: Dict[str, float] = {
        "fixed_cost": components.fixed_cost,
        "distance_cost": components.distance_cost,
        "total_cost": components.total_cost,
        "distance_km": components.distance_km,
    }
    if components.energy_kwh is not None:
        breakdown["energy_consumption_kwh"] = components.energy_kwh
    breakdown.update(components.details)
    return breakdown


__all__ = [
    "CostCalculator",
    "CostComponents",
    "cost_components_to_breakdown",
]
