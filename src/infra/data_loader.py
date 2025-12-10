"""Master data loader and cleaning utilities."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


_RANGE_SEPARATORS = {
    "〜": "-",
    "～": "-",
    "–": "-",
    "—": "-",
    "−": "-",
}


def _clean_text(value: Optional[str | Iterable[str]]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        joined = " ".join(str(part) for part in value if part not in {None, ""})
        value = joined
    cleaned = str(value).strip()
    if not cleaned or cleaned in {"-", "NA", "N/A"}:
        return None
    cleaned = cleaned.replace("\ufeff", "").replace("\\xEF\\xBB\\xBF", "").strip()
    return cleaned or None


def _split_numeric_unit(text: str) -> Tuple[str, Optional[str]]:
    if not text:
        return "", None
    normalized = text
    for old, new in _RANGE_SEPARATORS.items():
        normalized = normalized.replace(old, new)
    idx = 0
    allowed = set("0123456789.,+-") | {"-"}
    while idx < len(normalized):
        char = normalized[idx]
        if char in allowed:
            idx += 1
            continue
        break
    numeric_part = normalized[:idx].strip()
    unit_part = normalized[idx:].strip() or None
    return numeric_part, unit_part


def _extract_numbers(text: str) -> List[float]:
    tokens = re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))
    numbers: List[float] = []
    for token in tokens:
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    return numbers


@dataclass(frozen=True)
class RangeValue:
    minimum: float
    maximum: float
    average: float


@dataclass(frozen=True)
class NumericValue:
    raw: Optional[str]
    value: Optional[float]
    range: Optional[RangeValue]
    unit: Optional[str]


def parse_numeric_value(value: Optional[str]) -> NumericValue:
    cleaned = _clean_text(value)
    if cleaned is None:
        return NumericValue(raw=None, value=None, range=None, unit=None)
    numeric_text, unit = _split_numeric_unit(cleaned)
    numbers = _extract_numbers(numeric_text)
    if not numbers:
        return NumericValue(raw=cleaned, value=None, range=None, unit=unit)
    if len(numbers) == 1:
        number = numbers[0]
        range_value = RangeValue(number, number, number)
        return NumericValue(raw=cleaned, value=number, range=range_value, unit=unit)
    minimum = numbers[0]
    maximum = numbers[-1]
    average = (minimum + maximum) / 2.0
    range_value = RangeValue(minimum, maximum, average)
    return NumericValue(raw=cleaned, value=average, range=range_value, unit=unit)


def _read_csv(path: Path) -> Tuple[List[str], List[Dict[str, Optional[str]]]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [
            (name or "").replace("\ufeff", "").replace("\\xEF\\xBB\\xBF", "").strip()
            for name in reader.fieldnames or []
        ]
        rows: List[Dict[str, Optional[str]]] = []
        for raw_row in reader:
            cleaned_row: Dict[str, Optional[str]] = {}
            for key, value in raw_row.items():
                clean_key = (key or "").replace("\ufeff", "").replace("\\xEF\\xBB\\xBF", "").strip()
                cleaned_row[clean_key] = _clean_text(value)
            rows.append(cleaned_row)
        return fieldnames, rows


@dataclass(frozen=True)
class VehicleSpec:
    name: str
    load_volume_m3: NumericValue
    max_payload_t: NumericValue
    fuel_efficiency_kmpl: NumericValue
    fuel_type: Optional[str]
    license: Optional[str]
    metrics: Dict[str, NumericValue]
    remarks: Optional[str]
    raw: Dict[str, Optional[str]]


def _load_vehicle_specs(path: Path) -> Dict[str, VehicleSpec]:
    _, rows = _read_csv(path)
    vehicles: Dict[str, VehicleSpec] = {}
    for row in rows:
        name = row.get("車両タイプ")
        if not name:
            continue
        metrics: Dict[str, NumericValue] = {}
        for key, value in row.items():
            if key in {"車両タイプ", "燃料タイプ", "運転免許", "備考"}:
                continue
            metrics[key] = parse_numeric_value(value)
        spec = VehicleSpec(
            name=name,
            load_volume_m3=parse_numeric_value(row.get("積載容積_m3")),
            max_payload_t=parse_numeric_value(row.get("最大積載量_t")),
            fuel_efficiency_kmpl=parse_numeric_value(row.get("燃費_km_per_L")),
            fuel_type=row.get("燃料タイプ"),
            license=row.get("運転免許"),
            metrics=metrics,
            remarks=row.get("備考"),
            raw=row,
        )
        vehicles[name] = spec
    return vehicles


@dataclass(frozen=True)
class CompatibilityInfo:
    vehicle_type: str
    supported_resources: Dict[str, Optional[bool]]
    requirements: Dict[str, Optional[str]]


def _parse_bool_token(token: Optional[str]) -> Optional[bool]:
    if token is None:
        return None
    if token in {"1", "true", "TRUE", "yes"}:
        return True
    if token in {"0", "false", "FALSE", "no"}:
        return False
    return None


def _load_compatibility(path: Path) -> Dict[str, CompatibilityInfo]:
    fieldnames, rows = _read_csv(path)
    base_columns = [name for name in fieldnames if not name.startswith("条件付き適合_") and name != "車両タイプ"]
    compatibility: Dict[str, CompatibilityInfo] = {}
    for row in rows:
        vehicle = row.get("車両タイプ")
        if not vehicle:
            continue
        supported: Dict[str, Optional[bool]] = {}
        requirements: Dict[str, Optional[str]] = {}
        for column in base_columns:
            if column == "車両タイプ":
                continue
            supported[column] = _parse_bool_token(row.get(column))
        for key, value in row.items():
            if key.startswith("条件付き適合_"):
                resource = key.replace("条件付き適合_", "")
                requirements[resource] = value
        compatibility[vehicle] = CompatibilityInfo(vehicle_type=vehicle, supported_resources=supported, requirements=requirements)
    return compatibility


@dataclass(frozen=True)
class ResourceTrait:
    name: str
    bulk_density_t_per_m3: Optional[RangeValue]
    constraint_type: Optional[str]
    appearance: Optional[str]
    moisture: Optional[str]
    source: Optional[str]
    reuse: Optional[str]
    treatment: Optional[str]
    gate_fee_range: Optional[RangeValue]
    notes: Optional[str]
    raw: Dict[str, Optional[str]]


def _build_range_from_columns(row: Dict[str, Optional[str]], min_key: str, max_key: str) -> Optional[RangeValue]:
    min_value = parse_numeric_value(row.get(min_key))
    max_value = parse_numeric_value(row.get(max_key))
    if min_value.range and max_value.range:
        minimum = min_value.range.minimum
        maximum = max_value.range.maximum
        average = (minimum + maximum) / 2.0
        return RangeValue(minimum, maximum, average)
    if min_value.value is not None and max_value.value is not None:
        minimum = min_value.value
        maximum = max_value.value
        average = (minimum + maximum) / 2.0
        return RangeValue(minimum, maximum, average)
    if min_value.value is not None:
        value = min_value.value
        return RangeValue(value, value, value)
    if max_value.value is not None:
        value = max_value.value
        return RangeValue(value, value, value)
    return None


def _load_resource_traits(path: Path) -> Dict[str, ResourceTrait]:
    _, rows = _read_csv(path)
    traits: Dict[str, ResourceTrait] = {}
    for row in rows:
        name = row.get("資源名")
        if not name:
            continue
        density = _build_range_from_columns(row, "嵩密度_t_per_m3_min", "嵩密度_t_per_m3_max")
        gate_fee = _build_range_from_columns(row, "ゲート料_円_per_t_min", "ゲート料_円_per_t_max")
        trait = ResourceTrait(
            name=name,
            bulk_density_t_per_m3=density,
            constraint_type=row.get("制約タイプ"),
            appearance=row.get("性状"),
            moisture=row.get("水分含有率"),
            source=row.get("主な発生源"),
            reuse=row.get("リサイクル用途"),
            treatment=row.get("処理方法"),
            gate_fee_range=gate_fee,
            notes=row.get("特記事項"),
            raw=row,
        )
        traits[name] = trait
    return traits


@dataclass(frozen=True)
class SupplementEntry:
    category: str
    item: Optional[str]
    values: Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]
    description: Optional[str]
    raw: Dict[str, Optional[str]]


@dataclass(frozen=True)
class SupplementData:
    entries_by_category: Dict[str, List[SupplementEntry]] = field(default_factory=dict)
    notes: List[SupplementEntry] = field(default_factory=list)


def _load_supplement(path: Path) -> SupplementData:
    _, rows = _read_csv(path)
    entries: Dict[str, List[SupplementEntry]] = {}
    notes: List[SupplementEntry] = []
    for row in rows:
        category = row.get("データ種別")
        item = row.get("項目")
        entry = SupplementEntry(
            category=category or "",
            item=item,
            values=(row.get("値1"), row.get("値2"), row.get("値3"), row.get("値4")),
            description=row.get("説明"),
            raw=row,
        )
        if category and not category.startswith(tuple(str(num) + "." for num in range(1, 10))) and not category.startswith("注記"):
            entries.setdefault(category, []).append(entry)
        else:
            notes.append(entry)
    return SupplementData(entries_by_category=entries, notes=notes)


@dataclass(frozen=True)
class MasterData:
    vehicles: Dict[str, VehicleSpec]
    compatibility: Dict[str, CompatibilityInfo]
    resource_traits: Dict[str, ResourceTrait]
    supplement: SupplementData

    @classmethod
    def load(cls, base_dir: Path) -> "MasterData":
        vehicles = _load_vehicle_specs(base_dir / "車両諸元表.csv")
        compatibility = _load_compatibility(base_dir / "車両資源適合性マトリックス.csv")
        resource_traits = _load_resource_traits(base_dir / "未利用資源特性表.csv")
        supplement = _load_supplement(base_dir / "補足データ集.csv")
        return cls(
            vehicles=vehicles,
            compatibility=compatibility,
            resource_traits=resource_traits,
            supplement=supplement,
        )


__all__ = [
    "MasterData",
    "VehicleSpec",
    "CompatibilityInfo",
    "ResourceTrait",
    "SupplementData",
    "SupplementEntry",
    "NumericValue",
    "RangeValue",
]
