"""Persistence helpers for exporting application state."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .optimizer import Solution


def _ensure_path(path: Path, suffix: str) -> Path:
    if path.suffix != suffix:
        return path.with_suffix(suffix)
    return path


def export_to_json(state: Mapping[str, Any], solution: Solution, path: Path) -> Path:
    """Export scenario state and solution to a JSON file."""

    payload = {
        "state": dict(state),
        "solution": {
            "vehicle": solution.vehicle.name,
            "order": solution.order,
            "total_distance_m": solution.total_distance_m,
            "cost_breakdown": solution.cost_breakdown,
        },
    }
    path = _ensure_path(path, ".json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_to_csv(state: Mapping[str, Any], solution: Solution, path: Path) -> Path:
    """Export pickups, vehicles, and route sequence into CSV files."""

    base = path.with_suffix("")
    pickups = list(state.get("pickups", []))
    vehicles = list(state.get("vehicles", []))
    route_rows = [
        {"sequence": idx, "point_id": point_id}
        for idx, point_id in enumerate(solution.order)
    ]

    _write_csv(base.with_name(base.name + "_pickups.csv"), pickups)
    _write_csv(base.with_name(base.name + "_vehicles.csv"), vehicles)
    _write_csv(base.with_name(base.name + "_route.csv"), route_rows)
    return base
