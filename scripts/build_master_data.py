#!/usr/bin/env python3
"""Convert master CSV files into processed JSON artefacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infra.data_loader import (
    CompatibilityInfo,
    MasterData,
    NumericValue,
    RangeValue,
    ResourceTrait,
    SupplementData,
    SupplementEntry,
    VehicleSpec,
)


def _range_to_dict(value: RangeValue | None) -> Dict[str, float] | None:
    if value is None:
        return None
    return {
        "min": value.minimum,
        "max": value.maximum,
        "avg": value.average,
    }


def _numeric_to_float(value: NumericValue | None) -> float | None:
    if value is None:
        return None
    return value.value


def _convert_vehicle(spec: VehicleSpec) -> Dict[str, Any]:
    metrics = spec.metrics

    DEFAULT_ANNUAL_DISTANCE = 20000.0

    def _metric_value(key: str) -> float | None:
        numeric = metrics.get(key)
        return _numeric_to_float(numeric)

    capacity_kg = None
    if spec.max_payload_t and spec.max_payload_t.value is not None:
        capacity_kg = spec.max_payload_t.value * 1000.0

    load_volume = _numeric_to_float(spec.load_volume_m3)
    fuel_efficiency = _numeric_to_float(spec.fuel_efficiency_kmpl)

    annual_distance = _metric_value("年間走行距離_km")
    if not annual_distance or annual_distance <= 0:
        annual_distance = DEFAULT_ANNUAL_DISTANCE

    distance_for_fixed = annual_distance or DEFAULT_ANNUAL_DISTANCE

    variable_breakdown: Dict[str, float] = {}
    fixed_breakdown: Dict[str, float] = {}

    for key, numeric in metrics.items():
        if numeric is None:
            continue
        value = _numeric_to_float(numeric)
        if value is None:
            continue
        if key.endswith("_円_per_km"):
            variable_breakdown[key] = value
        elif key.endswith("_万円_per_年"):
            # NOTE:
            # - fixed_cost_breakdown は「万円/年」を保持する（キーサフィックスと意味を一致させる）
            # - km当たりへの換算や丸めは CostCalculator 側で一元的に行う
            fixed_breakdown[key] = value

    variable_cost = sum(variable_breakdown.values())
    annual_fixed_cost = sum((fixed_breakdown[key] or 0.0) * 10000.0 for key in fixed_breakdown)
    fixed_cost_per_km = annual_fixed_cost / distance_for_fixed if distance_for_fixed else 0.0

    record = {
        "name": spec.name,
        "fuel_type": spec.fuel_type,
        "license": spec.license,
        "capacity_kg": capacity_kg,
        "load_volume_m3": load_volume,
        "fuel_efficiency_km_per_l": fuel_efficiency,
        "annual_distance_km": distance_for_fixed,
        "variable_cost_per_km": variable_cost,
        "variable_cost_breakdown": variable_breakdown,
        "annual_fixed_cost": annual_fixed_cost,
        "fixed_cost_per_km": fixed_cost_per_km,
        "fixed_cost_breakdown": fixed_breakdown,
        "remarks": spec.remarks,
        "raw": spec.raw,
    }
    return record


def _convert_compatibility(data: Dict[str, CompatibilityInfo]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for vehicle, info in data.items():
        supports = {resource: value for resource, value in info.supported_resources.items()}
        requirements = {resource: value for resource, value in info.requirements.items()}
        result[vehicle] = {"supports": supports, "requirements": requirements}
    return result


def _convert_resource(trait: ResourceTrait) -> Dict[str, Any]:
    record = {
        "name": trait.name,
        "bulk_density_t_per_m3": _range_to_dict(trait.bulk_density_t_per_m3),
        "constraint_type": trait.constraint_type,
        "appearance": trait.appearance,
        "moisture": trait.moisture,
        "source": trait.source,
        "reuse": trait.reuse,
        "treatment": trait.treatment,
        "gate_fee_yen_per_t": _range_to_dict(trait.gate_fee_range),
        "notes": trait.notes,
        "raw": trait.raw,
    }
    return record


def _convert_supplement(data: SupplementData) -> Dict[str, Any]:
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for category, entries in data.entries_by_category.items():
        categories[category] = [
            {
                "item": entry.item,
                "values": list(entry.values),
                "description": entry.description,
                "raw": entry.raw,
            }
            for entry in entries
        ]
    notes = [
        {
            "category": entry.category,
            "item": entry.item,
            "values": list(entry.values),
            "description": entry.description,
            "raw": entry.raw,
        }
        for entry in data.notes
    ]
    return {"categories": categories, "notes": notes}


def _write_json(path: Path, payload: Any, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if pretty:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        else:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))


def _summarise(vehicles: List[Dict[str, Any]], resources: List[Dict[str, Any]], compatibility: Dict[str, Any]) -> str:
    lines = [
        f"車種: {len(vehicles)}件",
        f"資源: {len(resources)}件",
        f"適合性: {len(compatibility)}車種",
    ]
    return ", ".join(lines)


def build_processed_data(input_dir: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    master = MasterData.load(input_dir)
    vehicles: List[Dict[str, Any]] = []
    for spec in master.vehicles.values():
        record = _convert_vehicle(spec)
        if record.get("capacity_kg") is None:
            # CSV の備考行など車種パラメータが空のレコードは出力対象外
            continue
        vehicles.append(record)
    resources: List[Dict[str, Any]] = []
    for trait in master.resource_traits.values():
        record = _convert_resource(trait)
        if (
            record.get("bulk_density_t_per_m3") is None
            and record.get("constraint_type") is None
            and record.get("appearance") is None
            and record.get("moisture") is None
            and record.get("source") is None
            and record.get("reuse") is None
            and record.get("treatment") is None
            and record.get("gate_fee_yen_per_t") is None
            and record.get("notes") is None
        ):
            # 資源パラメータが空の備考行は除外
            continue
        resources.append(record)
    compatibility = _convert_compatibility(master.compatibility)
    supplement = _convert_supplement(master.supplement)
    return vehicles, compatibility, resources, supplement


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build processed master JSON files.")
    parser.add_argument("--input", type=Path, default=Path("data"), help="Input directory containing CSV files")
    parser.add_argument("--output", type=Path, default=Path("data/processed"), help="Output directory for JSON files")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--summary", action="store_true", help="Print summary information")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        vehicles, compatibility, resources, supplement = build_processed_data(args.input)
    except FileNotFoundError as exc:
        print(f"入力ファイルが見つかりません: {exc}", file=sys.stderr)
        return 1

    _write_json(args.output / "vehicles.json", {"vehicles": vehicles}, args.pretty)
    _write_json(args.output / "compatibility.json", {"compatibility": compatibility}, args.pretty)
    _write_json(args.output / "resources.json", {"resources": resources}, args.pretty)
    _write_json(args.output / "supplement.json", supplement, args.pretty)

    if args.summary:
        print(_summarise(vehicles, resources, compatibility))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
