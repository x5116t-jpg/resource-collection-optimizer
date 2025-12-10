"""In-process cache helpers for expensive computations."""

from __future__ import annotations

from typing import Any, Callable, Hashable

import networkx as nx

_graph_cache: dict[Hashable, nx.Graph] = {}
_distance_cache: dict[Hashable, Any] = {}


def _normalise_key(key: Any) -> Hashable:
    if isinstance(key, (tuple, list)):
        return tuple(round(float(v), 6) if isinstance(v, (int, float)) else v for v in key)
    return key


def cached_graph(key: Any, builder: Callable[[], nx.Graph]) -> nx.Graph:
    """Return a cached graph, building it via *builder* when missing."""

    cache_key = _normalise_key(key)
    if cache_key not in _graph_cache:
        _graph_cache[cache_key] = builder()
    return _graph_cache[cache_key]


def cached_distance_matrix(key: Any, builder: Callable[[], Any]) -> Any:
    """Return a cached distance matrix for the given key."""

    cache_key = _normalise_key(key)
    if cache_key not in _distance_cache:
        _distance_cache[cache_key] = builder()
    return _distance_cache[cache_key]


def clear() -> None:
    """Clear all cached objects (primarily for testing)."""

    _graph_cache.clear()
    _distance_cache.clear()
