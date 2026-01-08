#!/usr/bin/env python3
"""
Enrich processed vehicles master with:
- purchase_price_manyen (avg from raw range)
- useful_life_years (derived from purchase_price_manyen / depreciation_manyen_per_year)

This script does NOT change cost breakdown values yet; it only adds fields so that
later we can switch depreciation to be auto-calculated with clear provenance.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _parse_range_to_avg_manyen(value: object) -> Optional[float]:
    """
    Parse strings like "100-150" / "2.5-3.5" / "100〜150" into an average float.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    # normalise separators
    s = s.replace("〜", "-").replace("–", "-").replace("—", "-")
    # collect numbers (do NOT treat range hyphen as minus sign)
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    if not nums:
        return None
    if len(nums) == 1:
        return float(nums[0])
    # if the string contains a range, take the average of the first two numbers
    return float((nums[0] + nums[1]) / 2.0)


@dataclass(frozen=True)
class Diff:
    name: str
    purchase_price_manyen: Optional[float]
    useful_life_years: Optional[float]


def enrich_vehicle(vehicle: Dict[str, Any]) -> Diff:
    name = str(vehicle.get("name") or "")
    raw = vehicle.get("raw") or {}
    if not isinstance(raw, dict):
        raw = {}

    # If user already set a manual override, keep it.
    existing_purchase = vehicle.get("purchase_price_manyen")
    existing_source = str(vehicle.get("purchase_price_source") or "")
    if existing_purchase is not None and existing_source.startswith("manual:"):
        purchase_avg = float(existing_purchase)
    else:
        raw_purchase = raw.get("車両購入費_万円")
        purchase_avg = _parse_range_to_avg_manyen(raw_purchase)

    # Use processed depreciation (万円/年) if present; else try raw range.
    fb = vehicle.get("fixed_cost_breakdown") or {}
    if not isinstance(fb, dict):
        fb = {}
    dep_manyen_per_year = fb.get("減価償却費_万円_per_年")
    if dep_manyen_per_year is None:
        dep_manyen_per_year = _parse_range_to_avg_manyen(raw.get("減価償却費_万円_per_年"))
    try:
        dep_manyen_per_year_f = float(dep_manyen_per_year) if dep_manyen_per_year is not None else None
    except (TypeError, ValueError):
        dep_manyen_per_year_f = None

    residual_rate = vehicle.get("residual_value_rate")
    if residual_rate is None:
        residual_rate = 0.0
    try:
        residual_rate_f = float(residual_rate)
    except (TypeError, ValueError):
        residual_rate_f = 0.0

    useful_life = None
    if purchase_avg and dep_manyen_per_year_f and dep_manyen_per_year_f > 0:
        # (purchase - residual) / years = depreciation  => years = (purchase*(1-residual))/depreciation
        useful_life = (purchase_avg * (1.0 - residual_rate_f)) / dep_manyen_per_year_f
        # sanity guard: accept only plausible range, else leave None
        if useful_life < 1.0 or useful_life > 30.0:
            useful_life = None

    # Write fields
    vehicle["purchase_price_manyen"] = purchase_avg
    vehicle["useful_life_years"] = round(useful_life, 2) if useful_life is not None else None
    vehicle["residual_value_rate"] = residual_rate_f
    if existing_source.startswith("manual:"):
        vehicle["purchase_price_source"] = existing_source
    else:
        vehicle["purchase_price_source"] = "raw:車両購入費_万円(avg)" if purchase_avg is not None else "missing"
    vehicle["useful_life_source"] = "derived: purchase/depreciation" if useful_life is not None else "missing"
    return Diff(name=name, purchase_price_manyen=purchase_avg, useful_life_years=vehicle["useful_life_years"])


def main() -> int:
    path = Path("data/processed/vehicles.json")
    backup = path.parent / f"vehicles_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy(path, backup)

    payload = json.loads(path.read_text(encoding="utf-8"))
    vehicles: List[Dict[str, Any]] = list(payload.get("vehicles") or [])
    diffs: List[Diff] = []
    for v in vehicles:
        diffs.append(enrich_vehicle(v))

    path.write_text(json.dumps({"vehicles": vehicles}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"backup: {backup}")
    print(f"written: {path}")
    for d in diffs:
        print(f"- {d.name}: purchase_price_manyen={d.purchase_price_manyen}, useful_life_years={d.useful_life_years}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

