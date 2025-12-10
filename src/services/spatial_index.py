"""Lightweight spatial index for nearest-node queries without SciPy."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Mapping, MutableSequence, Optional, Sequence, Tuple

try:  # Optional dependency used for vectorised fallback
    import numpy as np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional
    np = None  # type: ignore

EARTH_RADIUS_M = 6_371_000.0
RAD = math.pi / 180.0

NodeCoord = Mapping[str, object]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = lat1 * RAD
    lat2_rad = lat2 * RAD
    dlat = (lat2 - lat1) * RAD
    dlon = (lon2 - lon1) * RAD
    sin_dlat = math.sin(dlat / 2.0)
    sin_dlon = math.sin(dlon / 2.0)
    a = sin_dlat * sin_dlat + math.cos(lat1_rad) * math.cos(lat2_rad) * sin_dlon * sin_dlon
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_M * c


@dataclass
class NearestResult:
    """Return value for nearest-node queries."""

    node_id: str
    distance_m: float
    index: int


class SpatialIndex:
    """Grid-based spatial index with optional NumPy vectorisation."""

    def __init__(
        self,
        node_coords: Sequence[NodeCoord],
        *,
        cell_size: float = 0.005,
        max_radius: int = 4,
        prefer_vectorised: bool = True,
    ) -> None:
        if not node_coords:
            raise ValueError("SpatialIndex requires at least one coordinate")
        self._cell_size = float(cell_size)
        self._max_radius = int(max(1, max_radius))
        self._node_ids: List[str] = []
        self._lats: List[float] = []
        self._lons: List[float] = []
        self._buckets: dict[Tuple[int, int], List[int]] = {}

        for idx, entry in enumerate(node_coords):
            try:
                lat = float(entry["lat"])  # type: ignore[index]
                lon = float(entry["lon"])  # type: ignore[index]
            except KeyError as exc:  # pragma: no cover - defensive
                raise KeyError("Node coordinate requires 'lat' and 'lon'") from exc
            node_id = str(entry.get("id") or entry.get("node_id") or idx)
            self._node_ids.append(node_id)
            self._lats.append(lat)
            self._lons.append(lon)
            cell = self._cell_key(lat, lon)
            self._buckets.setdefault(cell, []).append(idx)

        self._vector_enabled = bool(prefer_vectorised and np is not None)
        if self._vector_enabled:
            self._lat_array = np.array(self._lats) * RAD  # type: ignore[assignment]
            self._lon_array = np.array(self._lons) * RAD  # type: ignore[assignment]
            self._cos_lat_array = np.cos(self._lat_array)  # type: ignore[assignment]
        else:
            self._lat_array = None  # type: ignore[attr-defined]
            self._lon_array = None  # type: ignore[attr-defined]
            self._cos_lat_array = None  # type: ignore[attr-defined]

    @classmethod
    def from_iterable(
        cls,
        coords: Iterable[Mapping[str, object]],
        *,
        cell_size: float = 0.005,
        max_radius: int = 4,
        prefer_vectorised: bool = True,
    ) -> "SpatialIndex":
        return cls(list(coords), cell_size=cell_size, max_radius=max_radius, prefer_vectorised=prefer_vectorised)

    # Public API ---------------------------------------------------------
    def nearest(self, lat: float, lon: float) -> NearestResult:
        """Return the nearest node for the supplied coordinate."""

        if self._vector_enabled:
            return self._nearest_vectorised(lat, lon)
        return self._nearest_grid(lat, lon)

    # Internal helpers ---------------------------------------------------
    def _nearest_vectorised(self, lat: float, lon: float) -> NearestResult:
        assert np is not None  # for mypy
        lat_rad = lat * RAD
        lon_rad = lon * RAD
        dlat = self._lat_array - lat_rad  # type: ignore[operator]
        dlon = self._lon_array - lon_rad  # type: ignore[operator]
        sin_dlat = np.sin(dlat / 2.0)
        sin_dlon = np.sin(dlon / 2.0)
        a = sin_dlat * sin_dlat + math.cos(lat_rad) * self._cos_lat_array * sin_dlon * sin_dlon  # type: ignore[operator]
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(0.0, 1.0 - a)))
        distances = EARTH_RADIUS_M * c
        idx = int(np.argmin(distances))
        return NearestResult(self._node_ids[idx], float(distances[idx]), idx)

    def _nearest_grid(self, lat: float, lon: float) -> NearestResult:
        key = self._cell_key(lat, lon)
        visited: set[Tuple[int, int]] = set()
        best_idx: Optional[int] = None
        best_distance = float("inf")

        for radius in range(0, self._max_radius + 1):
            cells = self._cells_within_radius(key, radius)
            found_in_radius = False
            for cell in cells:
                if cell in visited:
                    continue
                visited.add(cell)
                indices = self._buckets.get(cell)
                if not indices:
                    continue
                found_in_radius = True
                for idx in indices:
                    distance = _haversine(lat, lon, self._lats[idx], self._lons[idx])
                    if distance < best_distance:
                        best_distance = distance
                        best_idx = idx
            if found_in_radius and best_idx is not None:
                break

        if best_idx is None:
            # Fallback to linear scan (should rarely trigger once grid populated)
            for idx, (node_lat, node_lon) in enumerate(zip(self._lats, self._lons)):
                distance = _haversine(lat, lon, node_lat, node_lon)
                if distance < best_distance:
                    best_distance = distance
                    best_idx = idx

        assert best_idx is not None, "SpatialIndex failed to locate a nearest node"
        return NearestResult(self._node_ids[best_idx], best_distance, best_idx)

    def _cell_key(self, lat: float, lon: float) -> Tuple[int, int]:
        return (int(math.floor(lat / self._cell_size)), int(math.floor(lon / self._cell_size)))

    def _cells_within_radius(self, key: Tuple[int, int], radius: int) -> List[Tuple[int, int]]:
        if radius <= 0:
            return [key]
        cx, cy = key
        cells: List[Tuple[int, int]] = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cells.append((cx + dx, cy + dy))
        return cells

    # Convenience accessors ---------------------------------------------
    @property
    def node_count(self) -> int:
        return len(self._node_ids)

    @property
    def mode(self) -> str:
        return "vectorised" if self._vector_enabled else "grid"


__all__ = ["SpatialIndex", "NearestResult"]
