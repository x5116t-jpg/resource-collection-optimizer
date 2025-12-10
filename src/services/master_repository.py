"""Loader for processed master JSON artefacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# 燃料エネルギー密度定数（kWh/L）
# 出典: 国際エネルギー機関（IEA）
FUEL_ENERGY_DENSITY_KWH_PER_L = {
    "ガソリン": 8.8,   # レギュラーガソリンの低位発熱量
    "軽油": 10.0,      # ディーゼル燃料の低位発熱量
    "電気": 1.0,       # 電気の場合は直接kWhで指定
}


@dataclass(frozen=True)
class VehicleCandidate:
    name: str
    capacity_kg: Optional[float]
    load_volume_m3: Optional[float]
    fuel_type: Optional[str]
    license: Optional[str]
    fuel_efficiency_km_per_l: Optional[float]
    annual_distance_km: Optional[float]
    variable_cost_per_km: float
    fixed_cost_per_km: float
    annual_fixed_cost: float
    variable_cost_breakdown: Dict[str, float]
    fixed_cost_breakdown: Dict[str, float]
    remarks: Optional[str]
    energy_consumption_kwh_per_km: Optional[float] = None  # エネルギー消費量 (kWh/km)


@dataclass(frozen=True)
class ResourceInfo:
    name: str
    constraint_type: Optional[str]
    appearance: Optional[str]
    moisture: Optional[str]
    source: Optional[str]
    reuse: Optional[str]
    treatment: Optional[str]
    bulk_density: Optional[Dict[str, float]]
    gate_fee: Optional[Dict[str, float]]
    notes: Optional[str]


@dataclass(frozen=True)
class CompatibilityInfoRecord:
    supports: Dict[str, Optional[bool]]
    requirements: Dict[str, Optional[str]]


@dataclass(frozen=True)
class SupplementInfo:
    categories: Dict[str, List[Dict[str, Any]]]
    notes: List[Dict[str, Any]]


@dataclass(frozen=True)
class ProcessedMasterData:
    vehicles: List[VehicleCandidate]
    compatibility: Dict[str, CompatibilityInfoRecord]
    resources: Dict[str, ResourceInfo]
    supplement: SupplementInfo


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_vehicles(path: Path) -> List[VehicleCandidate]:
    payload = _load_json(path)
    items = payload.get("vehicles", [])
    vehicles: List[VehicleCandidate] = []
    for entry in items:
        # エネルギー消費量の計算または取得
        energy_kwh_per_km = entry.get("energy_consumption_kwh_per_km")
        if energy_kwh_per_km is None:
            # JSONに明示的に指定されていない場合、燃費から計算
            fuel_type = entry.get("fuel_type")
            fuel_efficiency = entry.get("fuel_efficiency_km_per_l")
            if fuel_type and fuel_efficiency and fuel_efficiency > 0:
                fuel_l_per_km = 1.0 / fuel_efficiency
                energy_density = FUEL_ENERGY_DENSITY_KWH_PER_L.get(fuel_type, 0)
                energy_kwh_per_km = fuel_l_per_km * energy_density
            else:
                energy_kwh_per_km = 0.0

        # 負の値を防ぐ
        if energy_kwh_per_km < 0:
            energy_kwh_per_km = 0.0

        vehicles.append(
            VehicleCandidate(
                name=entry.get("name"),
                capacity_kg=entry.get("capacity_kg"),
                load_volume_m3=entry.get("load_volume_m3"),
                fuel_type=entry.get("fuel_type"),
                license=entry.get("license"),
                fuel_efficiency_km_per_l=entry.get("fuel_efficiency_km_per_l"),
                annual_distance_km=entry.get("annual_distance_km"),
                variable_cost_per_km=float(entry.get("variable_cost_per_km") or 0.0),
                fixed_cost_per_km=float(entry.get("fixed_cost_per_km") or 0.0),
                annual_fixed_cost=float(entry.get("annual_fixed_cost") or 0.0),
                variable_cost_breakdown={k: float(v) for k, v in (entry.get("variable_cost_breakdown") or {}).items()},
                fixed_cost_breakdown={k: float(v) for k, v in (entry.get("fixed_cost_breakdown") or {}).items()},
                remarks=entry.get("remarks"),
                energy_consumption_kwh_per_km=energy_kwh_per_km,
            )
        )
    return vehicles


def _load_resources(path: Path) -> Dict[str, ResourceInfo]:
    payload = _load_json(path)
    resources: Dict[str, ResourceInfo] = {}
    for entry in payload.get("resources", []):
        info = ResourceInfo(
            name=entry.get("name"),
            constraint_type=entry.get("constraint_type"),
            appearance=entry.get("appearance"),
            moisture=entry.get("moisture"),
            source=entry.get("source"),
            reuse=entry.get("reuse"),
            treatment=entry.get("treatment"),
            bulk_density=entry.get("bulk_density_t_per_m3"),
            gate_fee=entry.get("gate_fee_yen_per_t"),
            notes=entry.get("notes"),
        )
        resources[info.name] = info
    return resources


def _load_compatibility(path: Path) -> Dict[str, CompatibilityInfoRecord]:
    payload = _load_json(path)
    result: Dict[str, CompatibilityInfoRecord] = {}
    for vehicle, entry in payload.get("compatibility", {}).items():
        supports = entry.get("supports") or {}
        requirements = entry.get("requirements") or {}
        result[vehicle] = CompatibilityInfoRecord(
            supports={k: (None if v is None else bool(v)) for k, v in supports.items()},
            requirements={k: v for k, v in requirements.items()},
        )
    return result


def _load_supplement(path: Path) -> SupplementInfo:
    payload = _load_json(path)
    return SupplementInfo(
        categories=payload.get("categories", {}),
        notes=payload.get("notes", []),
    )


def load_processed_master(base_dir: Path) -> ProcessedMasterData:
    vehicles = _load_vehicles(base_dir / "vehicles.json")
    compatibility = _load_compatibility(base_dir / "compatibility.json")
    resources = _load_resources(base_dir / "resources.json")
    supplement = _load_supplement(base_dir / "supplement.json")
    return ProcessedMasterData(
        vehicles=vehicles,
        compatibility=compatibility,
        resources=resources,
        supplement=supplement,
    )


__all__ = [
    "ProcessedMasterData",
    "VehicleCandidate",
    "ResourceInfo",
    "CompatibilityInfoRecord",
    "SupplementInfo",
    "load_processed_master",
]
