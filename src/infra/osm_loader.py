"""OSM graph loading helpers."""

from __future__ import annotations

from typing import Iterable, Tuple

import networkx as nx

try:
    import osmnx as ox  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    ox = None  # type: ignore


BBox = Tuple[float, float, float, float]


def load_graph(bbox: BBox, network_type: str = "drive") -> nx.Graph:
    """Load a graph for the specified bounding box."""

    if ox is None:
        raise RuntimeError("osmnx is required to load OSM graphs")
    north, south, east, west = bbox[3], bbox[1], bbox[2], bbox[0]
    return ox.graph_from_bbox(north, south, east, west, network_type=network_type)
