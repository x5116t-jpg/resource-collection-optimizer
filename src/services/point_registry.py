"""Point registry handling user-selected locations and attributes."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional


class PointType(str, Enum):
    """Classification for user-selected points."""

    DEPOT = "depot"
    PICKUP = "pickup"
    SINK = "sink"


@dataclass(frozen=True)
class Point:
    """Represents a geographic point supplied by the user."""

    id: str
    lat: float
    lon: float
    type: PointType
    name: Optional[str] = None
    node_id: Optional[str] = None
    connector_distance_m: float = 0.0


@dataclass(frozen=True)
class PickupAttr:
    """Additional attributes associated with pickup points."""

    point_id: str
    qty_kg: int
    kind: str


@dataclass
class PointRegistry:
    """In-memory store for user-selected points and related attributes."""

    _points: Dict[str, Point] = field(default_factory=dict)
    _pickup_attrs: Dict[str, PickupAttr] = field(default_factory=dict)
    _id_counter: itertools.count = field(default_factory=lambda: itertools.count(1), repr=False)

    def add_point(
        self,
        lat: float,
        lon: float,
        point_type: PointType,
        name: Optional[str] = None,
        point_id: Optional[str] = None,
        node_id: Optional[str] = None,
        connector_distance_m: float = 0.0,
    ) -> Point:
        """Register a new point and return the created record."""

        assigned_id = point_id or f"pt_{next(self._id_counter)}"
        point = Point(
            id=assigned_id,
            lat=lat,
            lon=lon,
            type=point_type,
            name=name,
            node_id=node_id,
            connector_distance_m=float(connector_distance_m),
        )
        self._points[assigned_id] = point
        if point_type is not PointType.PICKUP:
            self._pickup_attrs.pop(assigned_id, None)
        return point

    def set_pickup_attr(self, point_id: str, qty: int, kind: str) -> PickupAttr:
        """Attach pickup attributes to an existing pickup point."""

        point = self._points.get(point_id)
        if point is None:
            raise KeyError(f"Unknown point id: {point_id}")
        if point.type is not PointType.PICKUP:
            raise ValueError("Attributes can only be set for pickup points")
        attr = PickupAttr(point_id=point_id, qty_kg=max(0, int(qty)), kind=kind)
        self._pickup_attrs[point_id] = attr
        return attr

    def list_points(self, point_type: Optional[PointType] = None) -> List[Point]:
        """Return points filtered by type (if provided) preserving insertion order."""

        items: Iterable[Point] = self._points.values()
        if point_type is not None:
            items = (p for p in items if p.type is point_type)
        return list(items)

    def get_point(self, point_id: str) -> Point:
        """Retrieve a point by identifier."""

        try:
            return self._points[point_id]
        except KeyError as exc:
            raise KeyError(f"Unknown point id: {point_id}") from exc

    def get_pickup_attr(self, point_id: str) -> Optional[PickupAttr]:
        """Return pickup attributes if registered."""

        return self._pickup_attrs.get(point_id)

    def total_pickup_demand(self) -> int:
        """Aggregate the registered pickup demand."""

        return sum(attr.qty_kg for attr in self._pickup_attrs.values())

    def clear(self) -> None:
        """Reset the registry."""

        self._points.clear()
        self._pickup_attrs.clear()
        self._id_counter = itertools.count(1)
