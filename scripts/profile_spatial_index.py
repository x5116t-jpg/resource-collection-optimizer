"""Benchmark grid-based spatial index against linear search."""

from __future__ import annotations

import json
import math
import random
import statistics
import time
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.spatial_index import SpatialIndex

try:  # Optional dependency for vectorised mode detection
    import numpy as np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    np = None  # type: ignore

DATA_PATH = Path("data/road_network_20251017_154630.json")
SAMPLE_COUNT = 200


def load_nodes() -> List[Tuple[float, float, str]]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    nodes: List[Tuple[float, float, str]] = []
    for node_id, node in data["nodes"].items():
        nodes.append((float(node.get("lat", 0.0)), float(node.get("lon", 0.0)), str(node_id)))
    return nodes


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rad = math.pi / 180.0
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    lat1_rad = lat1 * rad
    lat2_rad = lat2 * rad
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return 6_371_000.0 * c


def linear_nearest(nodes: List[Tuple[float, float, str]], lat: float, lon: float) -> Tuple[str, float]:
    best_id = nodes[0][2]
    best_dist = float("inf")
    for node_lat, node_lon, node_id in nodes:
        distance = haversine(lat, lon, node_lat, node_lon)
        if distance < best_dist:
            best_dist = distance
            best_id = node_id
    return best_id, best_dist


def random_samples(nodes: List[Tuple[float, float, str]], count: int) -> Iterable[Tuple[float, float]]:
    lats = [lat for lat, *_ in nodes]
    lons = [lon for _, lon, _ in nodes]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    for _ in range(count):
        yield (random.uniform(lat_min, lat_max), random.uniform(lon_min, lon_max))


def profile(func, samples: Iterable[Tuple[float, float]]) -> Tuple[float, List[float]]:
    lat_lon = list(samples)
    durations: List[float] = []
    start = time.perf_counter()
    for lat, lon in lat_lon:
        tick = time.perf_counter()
        func(lat, lon)
        durations.append(time.perf_counter() - tick)
    total = time.perf_counter() - start
    return total, durations


def main() -> None:
    nodes = load_nodes()
    samples = list(random_samples(nodes, SAMPLE_COUNT))

    linear_total, linear_durations = profile(lambda lat, lon: linear_nearest(nodes, lat, lon), samples)
    print(f"Linear search: total={linear_total:.4f}s avg={linear_total / SAMPLE_COUNT * 1000:.3f}ms")

    index = SpatialIndex(
        [{"lat": lat, "lon": lon, "id": node_id} for lat, lon, node_id in nodes],
        prefer_vectorised=(np is not None),
    )
    index_total, index_durations = profile(lambda lat, lon: index.nearest(lat, lon), samples)
    avg_ms = index_total / SAMPLE_COUNT * 1000
    print(f"SpatialIndex ({index.mode}): total={index_total:.4f}s avg={avg_ms:.3f}ms")
    print(f"  P95 latency: {statistics.quantiles(index_durations, n=100)[94] * 1000:.3f}ms")

    if np is not None and index.mode != "vectorised":
        print("NumPy available but vectorised mode disabled")

    if avg_ms > 5.0:
        print("WARNING: Average latency exceeds 5ms target")


if __name__ == "__main__":
    main()
