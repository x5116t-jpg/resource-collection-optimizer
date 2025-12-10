"""Service layer exposing optimisation and data utilities."""

from .point_registry import Point, PickupAttr, PointRegistry, PointType
from .vehicle_catalog import VehicleType, VehicleCatalog
from .distance_matrix import DistanceMatrix, DistanceMatrixError, build_distance_matrix, snap_to_graph
from .optimizer import (
    Solution,
    FleetSolution,
    VehicleRoute,
    NoSolution,
    NoSolutionReason,
    solve_routing,
    solve_fleet_routing,
)
from .master_repository import (
    ProcessedMasterData,
    VehicleCandidate,
    ResourceInfo,
    CompatibilityInfoRecord,
    SupplementInfo,
    load_processed_master,
)

__all__ = [
    "Point",
    "PickupAttr",
    "PointRegistry",
    "PointType",
    "VehicleType",
    "VehicleCatalog",
    "DistanceMatrix",
    "DistanceMatrixError",
    "build_distance_matrix",
    "snap_to_graph",
    "Solution",
    "FleetSolution",
    "VehicleRoute",
    "NoSolution",
    "NoSolutionReason",
    "solve_routing",
    "solve_fleet_routing",
    "ProcessedMasterData",
    "VehicleCandidate",
    "ResourceInfo",
    "CompatibilityInfoRecord",
    "SupplementInfo",
    "load_processed_master",
]
