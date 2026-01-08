"""
Debug script to compare:
- total fixed/variable costs (unit_cost_total * distance, rounded)
- sum of detailed items (each item rounded, then summed)

This helps diagnose why "内訳の合計" does not match "固定費計/変動費計".
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Tuple


def round_yen(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def d(value) -> Decimal:
    return Decimal(str(value))


def compute_fixed_details(
    fixed_breakdown_manyen_per_year: Dict[str, float],
    distance_km: Decimal,
    annual_distance_km: Decimal,
) -> Dict[str, int]:
    details: Dict[str, int] = {}
    for item, manyen in fixed_breakdown_manyen_per_year.items():
        annual_yen = d(manyen) * Decimal("10000")
        per_km = annual_yen / annual_distance_km if annual_distance_km != 0 else Decimal("0")
        details[item] = round_yen(per_km * distance_km)
    return details


def compute_variable_details(
    variable_breakdown_yen_per_km: Dict[str, float],
    distance_km: Decimal,
) -> Dict[str, int]:
    details: Dict[str, int] = {}
    for item, yen_per_km in variable_breakdown_yen_per_km.items():
        details[item] = round_yen(d(yen_per_km) * distance_km)
    return details


def main() -> None:
    vehicles_path = Path("data/processed/vehicles.json")
    payload = json.loads(vehicles_path.read_text(encoding="utf-8"))
    vehicles = payload["vehicles"]

    # Pick one vehicle and a representative distance.
    vehicle = vehicles[0]
    distance_km = Decimal("45.5")

    annual_distance = d(vehicle.get("annual_distance_km") or 0)
    fixed_km = d(vehicle.get("fixed_cost_per_km") or 0)
    var_km = d(vehicle.get("variable_cost_per_km") or 0)

    fixed_total = round_yen(fixed_km * distance_km)
    var_total = round_yen(var_km * distance_km)

    fixed_details = compute_fixed_details(vehicle.get("fixed_cost_breakdown") or {}, distance_km, annual_distance)
    var_details = compute_variable_details(vehicle.get("variable_cost_breakdown") or {}, distance_km)

    fixed_sum = sum(fixed_details.values())
    var_sum = sum(var_details.values())

    print(f"vehicle={vehicle.get('name')}")
    print(f"distance_km={distance_km}")
    print(f"fixed_total={fixed_total}  sum(details)={fixed_sum}  diff={fixed_total - fixed_sum}")
    print(f"var_total={var_total}    sum(details)={var_sum}    diff={var_total - var_sum}")

    if fixed_total != fixed_sum:
        print("\n[fixed] top 5 items:")
        for k, v in sorted(fixed_details.items(), key=lambda kv: kv[1], reverse=True)[:5]:
            print(f"  {k}: {v}")
    if var_total != var_sum:
        print("\n[variable] top 5 items:")
        for k, v in sorted(var_details.items(), key=lambda kv: kv[1], reverse=True)[:5]:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()


