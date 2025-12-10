"""Distance matrix construction utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

import networkx as nx

from .spatial_index import SpatialIndex

# Sentinel value for unreachable pairs.
UNREACHABLE_COST = 1e9


class DistanceMatrixError(RuntimeError):
    """Raised when distance matrix construction fails."""


@dataclass(frozen=True)
class SnappedPoint:
    """Represents a point snapped onto a graph node."""

    point_id: str
    node_id: Union[int, str]
    distance_m: float = 0.0
    connector_distance_m: float = 0.0
    original_latlon: Optional[Tuple[float, float]] = None

    def __post_init__(self) -> None:
        # Maintain backwards compatibility where *distance_m* held the connector distance.
        if self.connector_distance_m == 0.0 and self.distance_m != 0.0:
            object.__setattr__(self, "connector_distance_m", float(self.distance_m))
        elif self.distance_m == 0.0 and self.connector_distance_m != 0.0:
            object.__setattr__(self, "distance_m", float(self.connector_distance_m))


@dataclass
class DistanceMatrix:
    """Holds a dense distance matrix with helper lookups."""

    matrix: List[List[float]]
    index_map: Dict[str, int]
    node_lookup: Dict[str, Union[int, str]]
    connector_offsets: Dict[str, float]

    def distance(self, from_id: str, to_id: str) -> float:
        """Return the distance in metres between two points."""

        i = self._index(from_id)
        j = self._index(to_id)
        if i == j:
            return 0.0
        base = float(self.matrix[i][j])
        if base >= UNREACHABLE_COST:
            return base
        return base + self.connector_offsets.get(from_id, 0.0) + self.connector_offsets.get(to_id, 0.0)

    def _index(self, point_id: str) -> int:
        try:
            return self.index_map[point_id]
        except KeyError as exc:
            raise KeyError(f"Unknown point id: {point_id}") from exc

    def as_numpy(self):  # pragma: no cover - optional dependency
        """Return the matrix as a ``numpy.ndarray`` if numpy is available."""

        try:
            import numpy as np  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("numpy is required for ndarray conversion") from exc
        arr = np.array(self.matrix, copy=True)
        ordered: List[str] = [""] * len(self.index_map)
        for point_id, idx in self.index_map.items():
            ordered[idx] = point_id
        for i, from_id in enumerate(ordered):
            for j, to_id in enumerate(ordered):
                if i == j:
                    arr[i][j] = 0.0
                    continue
                if arr[i][j] >= UNREACHABLE_COST:
                    continue
                arr[i][j] = (
                    arr[i][j]
                    + self.connector_offsets.get(from_id, 0.0)
                    + self.connector_offsets.get(to_id, 0.0)
                )
        return arr

    def is_reachable(self, from_id: str, to_id: str) -> bool:
        """True if the pair is considered reachable."""

        return self.distance(from_id, to_id) < UNREACHABLE_COST


PointInput = Union[SnappedPoint, Mapping[str, object]]


def _normalise_point(point: PointInput) -> SnappedPoint:
    if isinstance(point, SnappedPoint):
        return point
    point_id = str(point.get("id") or point.get("point_id") or point.get("osmid") or point.get("node_id"))
    node_id = point.get("osmid") or point.get("node_id")
    if node_id is None:
        raise DistanceMatrixError("Point input requires 'osmid/node_id' or 'lat/lon'")
    connector = float(point.get("connector_distance_m") or point.get("distance_m") or 0.0)
    original_latlon = None
    lat = point.get("lat")
    lon = point.get("lon")
    if lat is not None and lon is not None:
        original_latlon = (float(lat), float(lon))
    return SnappedPoint(
        point_id=point_id,
        node_id=node_id,
        distance_m=float(point.get("distance_m") or connector),
        connector_distance_m=connector,
        original_latlon=original_latlon,
    )


def snap_to_graph(graph: nx.Graph, point: Mapping[str, object]) -> SnappedPoint:
    """Snap an arbitrary point to the nearest graph node.

    Accepts either a pre-associated ``osmid``/``node_id`` or raw ``lat``/``lon``
    coordinates. When snapping from coordinates, the nearest node is resolved
    using a lightweight spatial index and the connector距離を保持する。
    """

    if isinstance(point, SnappedPoint):
        return point

    if point.get("osmid") or point.get("node_id"):
        return _normalise_point(point)

    lat = point.get("lat")
    lon = point.get("lon")
    if lat is None or lon is None:
        raise DistanceMatrixError("Point input requires 'lat'/'lon' when node id is absent")

    lat_f = float(lat)
    lon_f = float(lon)

    coords: List[Dict[str, object]] = []
    node_iter = graph.nodes(data=True) if callable(getattr(graph, "nodes", None)) else graph.nodes.items()  # type: ignore[attr-defined]
    for node_id, data in node_iter:
        node_lat = data.get("lat") or data.get("y")
        node_lon = data.get("lon") or data.get("x")
        if node_lat is None or node_lon is None:
            continue
        coords.append({"id": str(node_id), "lat": float(node_lat), "lon": float(node_lon)})

    if not coords:
        raise DistanceMatrixError("Graph nodes do not contain coordinate attributes")

    index = SpatialIndex.from_iterable(coords, prefer_vectorised=False)
    result = index.nearest(lat_f, lon_f)

    point_id = str(point.get("id") or point.get("point_id") or result.node_id)
    return SnappedPoint(
        point_id=point_id,
        node_id=result.node_id,
        connector_distance_m=float(result.distance_m),
        original_latlon=(lat_f, lon_f),
    )


def build_distance_matrix(graph: nx.Graph, points: Sequence[PointInput]) -> DistanceMatrix:
    """Construct a dense distance matrix for the supplied points."""

    snapped: List[SnappedPoint] = [_normalise_point(p) for p in points]
    if not snapped:
        raise DistanceMatrixError("At least one point is required")

    n = len(snapped)
    matrix = [[float(UNREACHABLE_COST) for _ in range(n)] for _ in range(n)]
    index_map: Dict[str, int] = {}
    node_lookup: Dict[str, Union[int, str]] = {}
    connector_offsets: Dict[str, float] = {}

    for idx, sp in enumerate(snapped):
        index_map[sp.point_id] = idx
        node_lookup[sp.point_id] = sp.node_id
        connector_offsets[sp.point_id] = float(sp.connector_distance_m)
        matrix[idx][idx] = 0.0

    for idx, source in enumerate(snapped):
        try:
            lengths = nx.single_source_dijkstra_path_length(
                graph, source.node_id, weight="length"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
            raise DistanceMatrixError(str(exc)) from exc

        for jdx, target in enumerate(snapped):
            if target.node_id == source.node_id:
                matrix[idx][jdx] = 0.0
                continue
            length = lengths.get(target.node_id)
            if length is not None:
                matrix[idx][jdx] = float(length)

    return DistanceMatrix(
        matrix=matrix,
        index_map=index_map,
        node_lookup=node_lookup,
        connector_offsets=connector_offsets,
    )
