"""Utilities for reconstructing OSN polylines from routing output."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Union

import networkx as nx

from .distance_matrix import SnappedPoint

LatLon = Tuple[float, float]
RoutePoint = Union[SnappedPoint, int, str]


def _node_coordinates(graph: nx.Graph, node: Union[int, str]) -> LatLon:
    data = graph.nodes[node]
    lat = data.get("y") or data.get("lat")
    lon = data.get("x") or data.get("lon")
    if lat is None or lon is None:
        raise KeyError(f"Node {node} missing coordinate attributes")
    return float(lat), float(lon)


def _resolve_node_id(point: RoutePoint) -> Union[int, str]:
    if isinstance(point, SnappedPoint):
        return point.node_id
    return point


def reconstruct_paths(
    graph: nx.Graph,
    snapped_route: Sequence[RoutePoint],
    *,
    include_endpoints: bool = True,
) -> List[List[LatLon]]:
    """Reconstruct coordinate polylines for each consecutive route segment."""

    polylines: List[List[LatLon]] = []
    points: List[Union[int, str]] = [_resolve_node_id(pt) for pt in snapped_route]

    for start, end in zip(points[:-1], points[1:]):
        if start == end:
            try:
                polylines.append([_node_coordinates(graph, start)])
            except KeyError:
                polylines.append([])
            continue
        path_nodes = nx.shortest_path(graph, start, end, weight="length")
        coords: List[LatLon] = []
        for node in path_nodes:
            try:
                coords.append(_node_coordinates(graph, node))
            except KeyError:
                continue
        if not include_endpoints and coords:
            coords = coords[1:-1]
        polylines.append(coords)
    return polylines
