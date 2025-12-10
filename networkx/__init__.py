"""Lightweight subset of NetworkX tailored for unit testing."""

from __future__ import annotations

import heapq
from typing import Dict, Iterable, Iterator, MutableMapping, Optional, Tuple


class NetworkXError(Exception):
    pass


class NetworkXNoPath(NetworkXError):
    pass


class NodeNotFound(NetworkXError):
    pass


class _NodeMapping(MutableMapping):
    def __init__(self, backing: Dict):
        self._backing = backing

    def __getitem__(self, key):
        return self._backing[key]

    def __setitem__(self, key, value):
        self._backing[key] = value

    def __delitem__(self, key):
        del self._backing[key]

    def __iter__(self) -> Iterator:
        return iter(self._backing)

    def __len__(self) -> int:
        return len(self._backing)

    def get(self, key, default=None):
        return self._backing.get(key, default)


class DiGraph:
    """Minimal directed graph with weighted edges."""

    def __init__(self) -> None:
        self._succ: Dict = {}
        self._nodes: Dict = {}

    @property
    def nodes(self) -> _NodeMapping:
        return _NodeMapping(self._nodes)

    def add_node(self, node, **attrs) -> None:
        self._nodes.setdefault(node, {}).update(attrs)
        self._succ.setdefault(node, {})

    def add_edge(self, u, v, **attrs) -> None:
        self.add_node(u)
        self.add_node(v)
        self._succ[u][v] = dict(attrs)

    def successors(self, node) -> Iterable:
        if node not in self._succ:
            raise NodeNotFound(f"Node {node} not in graph")
        return self._succ[node].items()


def single_source_dijkstra_path_length(graph: DiGraph, source, weight: str = "length") -> Dict:
    if source not in graph.nodes:
        raise NodeNotFound(f"Node {source} not found")
    dist = {source: 0.0}
    heap: list[Tuple[float, object]] = [(0.0, source)]
    visited = set()

    while heap:
        current_dist, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        for succ, attrs in graph.successors(node):
            length = attrs.get(weight, 1.0)
            tentative = current_dist + float(length)
            if tentative < dist.get(succ, float("inf")):
                dist[succ] = tentative
                heapq.heappush(heap, (tentative, succ))
    return dist


def _dijkstra_predecessors(graph: DiGraph, source, target, weight: str) -> Dict:
    if source not in graph.nodes or target not in graph.nodes:
        raise NodeNotFound("Either source or target node not found")
    dist = {source: 0.0}
    pred: Dict = {source: None}
    heap: list[Tuple[float, object]] = [(0.0, source)]

    while heap:
        current_dist, node = heapq.heappop(heap)
        if node == target:
            break
        for succ, attrs in graph.successors(node):
            length = attrs.get(weight, 1.0)
            tentative = current_dist + float(length)
            if tentative < dist.get(succ, float("inf")):
                dist[succ] = tentative
                pred[succ] = node
                heapq.heappush(heap, (tentative, succ))
    if target not in dist:
        raise NetworkXNoPath(f"No path between {source} and {target}")
    return pred


def shortest_path(graph: DiGraph, source, target, weight: str = "length") -> list:
    predecessors = _dijkstra_predecessors(graph, source, target, weight)
    path = [target]
    current = target
    while predecessors.get(current) is not None:
        current = predecessors[current]
        path.append(current)
    if path[-1] != source:
        raise NetworkXNoPath(f"No path between {source} and {target}")
    path.reverse()
    return path


__all__ = [
    "DiGraph",
    "NetworkXError",
    "NetworkXNoPath",
    "NodeNotFound",
    "single_source_dijkstra_path_length",
    "shortest_path",
]
