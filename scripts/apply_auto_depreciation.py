#!/usr/bin/env python3
"""
Apply auto depreciation based on purchase price and useful life.

For each vehicle in data/processed/vehicles.json:
- If purchase_price_manyen and useful_life_years are present and > 0:
  depreciation_manyen_per_year = purchase_price_manyen * (1 - residual_value_rate) / useful_life_years
  -> write to fixed_cost_breakdown["減価償却費_万円_per_年"]
- Recompute annual_fixed_cost and fixed_cost_per_km from fixed_cost_breakdown and annual_distance_km

This implements docs/20260108_140500_減価償却費の自動算出_車両購入費と耐用年数_設計.md
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


KEY_DEPR = "減価償却費_万円_per_年"


def _f(x: object, default: float = 0.0) -> float:
    try:
        return float(x) if x is not None else default
    except (TypeError, ValueError):
        return default


def apply_one(vehicle: Dict[str, Any]) -> Tuple[bool, float, float]:
    """
    Returns:
      (applied, old_dep, new_dep)
    """
    fb = vehicle.get("fixed_cost_breakdown") or {}
    if not isinstance(fb, dict):
        fb = {}

    old_dep = _f(fb.get(KEY_DEPR), 0.0)
    purchase = _f(vehicle.get("purchase_price_manyen"), 0.0)
    life = _f(vehicle.get("useful_life_years"), 0.0)
    residual = _f(vehicle.get("residual_value_rate"), 0.0)

    if purchase <= 0 or life <= 0:
        return False, old_dep, old_dep

    new_dep = (purchase * (1.0 - residual)) / life
    fb[KEY_DEPR] = float(round(new_dep, 6))
    vehicle["fixed_cost_breakdown"] = fb
    vehicle["depreciation_source"] = "auto:purchase/life"

    # Recompute aggregates
    annual_distance = _f(vehicle.get("annual_distance_km"), 0.0)
    annual_fixed_cost = float(sum(_f(v, 0.0) for v in fb.values()) * 10000.0)
    vehicle["annual_fixed_cost"] = annual_fixed_cost
    vehicle["fixed_cost_per_km"] = (annual_fixed_cost / annual_distance) if annual_distance > 0 else 0.0

    return True, old_dep, float(round(new_dep, 6))


def main() -> int:
    path = Path("data/processed/vehicles.json")
    backup = path.parent / f"vehicles_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy(path, backup)

    payload = json.loads(path.read_text(encoding="utf-8"))
    vehicles: List[Dict[str, Any]] = list(payload.get("vehicles") or [])

    applied = 0
    for v in vehicles:
        ok, old_dep, new_dep = apply_one(v)
        if ok:
            applied += 1
        name = v.get("name")
        if ok and abs(old_dep - new_dep) > 1e-9:
            print(f"- {name}: {KEY_DEPR} {old_dep} -> {new_dep} (purchase={v.get('purchase_price_manyen')}, life={v.get('useful_life_years')})")

    path.write_text(json.dumps({"vehicles": vehicles}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"backup: {backup}")
    print(f"written: {path}")
    print(f"applied: {applied}/{len(vehicles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

