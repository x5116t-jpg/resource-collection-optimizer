#!/usr/bin/env python3
"""
Normalize processed vehicles master cost fields.

Why this exists
---------------
`data/processed/vehicles.json` has three related fixed-cost fields:

- fixed_cost_breakdown: keys end with "_万円_per_年" and values are "万円/年"
- annual_fixed_cost: should be the annual total in "円/年"
- fixed_cost_per_km: should be "円/km" derived from annual totals / annual_distance_km

Historically, annual_fixed_cost became inconsistent (e.g. exactly 2x of the breakdown sum).
That creates multiple "cost routes" and makes fixed/variable totals disagree depending on
which field is used. This script makes the fields consistent by treating
`fixed_cost_breakdown` as the source of truth.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


YEN_PER_MANYEN = 10000.0


@dataclass(frozen=True)
class VehicleDiff:
    name: str
    old_annual_fixed_cost: float
    new_annual_fixed_cost: float
    old_fixed_cost_per_km: float
    new_fixed_cost_per_km: float
    annual_distance_km: float


def _sum_fixed_breakdown_yen_per_year(vehicle: Dict[str, Any]) -> float:
    fixed_breakdown = vehicle.get("fixed_cost_breakdown") or {}
    return float(sum(float(v or 0.0) for v in fixed_breakdown.values()) * YEN_PER_MANYEN)


def _sum_variable_breakdown_yen_per_km(vehicle: Dict[str, Any]) -> float:
    variable_breakdown = vehicle.get("variable_cost_breakdown") or {}
    return float(sum(float(v or 0.0) for v in variable_breakdown.values()))


def normalize_vehicle(vehicle: Dict[str, Any]) -> Tuple[Dict[str, Any], VehicleDiff | None]:
    name = str(vehicle.get("name") or "")
    annual_distance_km = float(vehicle.get("annual_distance_km") or 0.0)

    # Variable: keep as-is but (optionally) re-sync the aggregate.
    variable_sum = _sum_variable_breakdown_yen_per_km(vehicle)
    if "variable_cost_per_km" in vehicle:
        vehicle["variable_cost_per_km"] = float(variable_sum)

    # Fixed: source-of-truth is breakdown "万円/年".
    annual_fixed_cost_new = _sum_fixed_breakdown_yen_per_year(vehicle)
    fixed_cost_per_km_new = (annual_fixed_cost_new / annual_distance_km) if annual_distance_km > 0 else 0.0

    old_annual = float(vehicle.get("annual_fixed_cost") or 0.0)
    old_fpk = float(vehicle.get("fixed_cost_per_km") or 0.0)

    vehicle["annual_fixed_cost"] = float(annual_fixed_cost_new)
    vehicle["fixed_cost_per_km"] = float(fixed_cost_per_km_new)

    if abs(old_annual - annual_fixed_cost_new) > 1e-6 or abs(old_fpk - fixed_cost_per_km_new) > 1e-6:
        return vehicle, VehicleDiff(
            name=name,
            old_annual_fixed_cost=old_annual,
            new_annual_fixed_cost=float(annual_fixed_cost_new),
            old_fixed_cost_per_km=old_fpk,
            new_fixed_cost_per_km=float(fixed_cost_per_km_new),
            annual_distance_km=annual_distance_km,
        )

    return vehicle, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize data/processed/vehicles.json cost fields.")
    parser.add_argument("--path", type=Path, default=Path("data/processed/vehicles.json"))
    parser.add_argument("--write", action="store_true", help="Write normalized content back to file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON when writing")
    parser.add_argument("--show", type=int, default=20, help="Show first N diffs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path: Path = args.path
    payload = json.loads(path.read_text(encoding="utf-8"))
    vehicles: List[Dict[str, Any]] = list(payload.get("vehicles") or [])

    diffs: List[VehicleDiff] = []
    normalized: List[Dict[str, Any]] = []
    for vehicle in vehicles:
        updated, diff = normalize_vehicle(vehicle)
        normalized.append(updated)
        if diff is not None:
            diffs.append(diff)

    print(f"vehicles={len(vehicles)} diffs={len(diffs)}")
    for diff in diffs[: max(0, int(args.show))]:
        print(
            f"- {diff.name}: "
            f"annual_fixed_cost {diff.old_annual_fixed_cost:.0f} -> {diff.new_annual_fixed_cost:.0f}, "
            f"fixed_cost_per_km {diff.old_fixed_cost_per_km:.5g} -> {diff.new_fixed_cost_per_km:.5g} "
            f"(annual_distance_km={diff.annual_distance_km:g})"
        )

    if args.write:
        out = {"vehicles": normalized}
        if args.pretty:
            path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"written: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

