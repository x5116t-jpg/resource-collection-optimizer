#!/usr/bin/env python3
"""
Migrate processed vehicles master to the minimal cost item set.

Target items
------------
Variable (yen/km):
- 燃料費_円_per_km
- 損料_円_per_km  (= タイヤ交換費_円_per_km + 修理費_円_per_km)

Fixed (万円/年):
- 減価償却費_万円_per_年
- 自動車税_万円_per_年
- 重量税_万円_per_年
- 自賠責保険_万円_per_年
- 任意保険_万円_per_年
- 車検費用_万円_per_年
- 定期点検費用_万円_per_年
- 車庫賃料_万円_per_年

Everything else is removed from breakdowns.
Aggregates (variable_cost_per_km / annual_fixed_cost / fixed_cost_per_km) are recalculated.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


VARIABLE_KEEP = ("燃料費_円_per_km",)
FIXED_KEEP = (
    "減価償却費_万円_per_年",
    "自動車税_万円_per_年",
    "重量税_万円_per_年",
    "自賠責保険_万円_per_年",
    "任意保険_万円_per_年",
    "車検費用_万円_per_年",
    "定期点検費用_万円_per_年",
    "車庫賃料_万円_per_年",
)


@dataclass(frozen=True)
class Summary:
    updated: int
    vehicles: int


def migrate_one(vehicle: Dict[str, Any]) -> None:
    vb = dict(vehicle.get("variable_cost_breakdown") or {})
    fb = dict(vehicle.get("fixed_cost_breakdown") or {})

    # Variable: keep fuel and create damage
    fuel = float(vb.get("燃料費_円_per_km") or 0.0)
    tire = float(vb.get("タイヤ交換費_円_per_km") or 0.0)
    repair = float(vb.get("修理費_円_per_km") or 0.0)
    damage = tire + repair
    new_vb: Dict[str, float] = {}
    if fuel:
        new_vb["燃料費_円_per_km"] = float(fuel)
    if damage:
        new_vb["損料_円_per_km"] = float(damage)
    vehicle["variable_cost_breakdown"] = new_vb
    vehicle["variable_cost_per_km"] = float(sum(new_vb.values()))

    # Fixed: keep minimal items (values are 万円/年)
    new_fb: Dict[str, float] = {}
    for k in FIXED_KEEP:
        v = float(fb.get(k) or 0.0)
        if v:
            new_fb[k] = v
    vehicle["fixed_cost_breakdown"] = new_fb

    annual_distance = float(vehicle.get("annual_distance_km") or 0.0)
    annual_fixed_cost = float(sum(new_fb.values()) * 10000.0)
    vehicle["annual_fixed_cost"] = annual_fixed_cost
    vehicle["fixed_cost_per_km"] = (annual_fixed_cost / annual_distance) if annual_distance > 0 else 0.0


def main() -> int:
    path = Path("data/processed/vehicles.json")
    backup = path.parent / f"vehicles_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy(path, backup)

    payload = json.loads(path.read_text(encoding="utf-8"))
    vehicles: List[Dict[str, Any]] = list(payload.get("vehicles") or [])

    for v in vehicles:
        migrate_one(v)

    path.write_text(json.dumps({"vehicles": vehicles}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"backup: {backup}")
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

