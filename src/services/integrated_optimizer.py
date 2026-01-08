"""Integrated optimisation (multi-trip, multi-vehicle).

This module is intentionally a scaffold to support the design documented in:
`docs/20260108_113500_統合最適化設計.md`

Goal
----
- Max physical vehicles: up to 4
- Max trips (sink unload events): up to 5
- Mixed loads allowed within capacity
- Depot is only used at the very beginning and the very end (no mid-depot)
- Cost calculation must go through CostCalculator (single source of truth)

Implementation is planned as a two-stage optimisation:
- Stage A: generate up to 5 "trips" (virtual vehicles) via VRP
- Stage B: assign trips to up to 4 physical vehicles (small combinatorial search),
           and re-optimise the second trip with start=sink when chaining
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .distance_matrix import DistanceMatrix, UNREACHABLE_COST
from .master_repository import ProcessedMasterData, VehicleCandidate
from .optimizer import (
    FleetSolution,
    NoSolution,
    NoSolutionReason,
    PickupInput,
    Solution,
    VehicleRoute,
    solve_path_routing,
)
from .vehicle_catalog import VehicleType
from .cost_calculator import CostCalculator, cost_components_to_breakdown

try:  # pragma: no cover - optional dependency
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2  # type: ignore

    ORTOOLS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    ORTOOLS_AVAILABLE = False


_COST_CALCULATOR = CostCalculator()


@dataclass(frozen=True)
class TripRoute:
    """A single 'trip' (depot/sink -> pickups -> sink) before physical-vehicle chaining."""

    vehicle: VehicleType
    pickup_ids: List[str]
    order: List[str]
    total_distance_m: float
    cost_breakdown: Dict[str, float]


@dataclass(frozen=True)
class IntegratedFleetSolution:
    """Result that keeps FleetSolution compatibility + trip-level details."""

    fleet: FleetSolution
    trips: List[TripRoute]
    vehicle_count: int
    trip_count: int


def _vehicle_supports_resource(
    vehicle_name: str,
    resource: str,
    master: Optional[ProcessedMasterData],
) -> bool:
    if not resource:
        return True
    if master is None or not master.compatibility or resource not in master.resources:
        return True
    compat = master.compatibility.get(vehicle_name)
    if compat is None:
        return False
    status = compat.supports.get(resource)
    return bool(status is True)


def _normalise_pickups(pickup_inputs: Sequence[PickupInput]) -> List[Dict[str, object]]:
    payload: List[Dict[str, object]] = []
    for entry in pickup_inputs:
        point_id = entry.get("id")
        if not point_id:
            raise ValueError("Pickup requires an 'id'")
        qty = entry.get("qty", entry.get("demand", 0))
        kind = entry.get("kind", "")
        payload.append(
            {
                "id": str(point_id),
                "qty": int(qty or 0),
                "demand": int(qty or 0),
                "kind": str(kind or ""),
            }
        )
    return payload


def _required_resources(pickups: Sequence[Mapping[str, object]]) -> List[str]:
    items: set[str] = set()
    for p in pickups:
        kind = str(p.get("kind") or "")
        if kind:
            items.add(kind)
    return sorted(items)


def _evaluate_cost(
    vehicle: VehicleType,
    distance_m: float,
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]],
    *,
    total_demand_kg: int = 0,
) -> Dict[str, float]:
    metadata = vehicle_metadata_map.get(vehicle.name) if vehicle_metadata_map else None
    components = _COST_CALCULATOR.evaluate(vehicle, distance_m, metadata, total_demand_kg=max(0, int(total_demand_kg)))
    return cost_components_to_breakdown(components)


def _extract_used_routes(
    distance_matrix: DistanceMatrix,
    manager,
    routing,
    assignment,
    point_ids_by_index: List[str],
    vehicles: Sequence[VehicleType],
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]],
) -> List[TripRoute]:
    trips: List[TripRoute] = []
    vehicle_count = routing.vehicles()
    for v in range(vehicle_count):
        index = routing.Start(v)
        route_indices: List[int] = []
        total_distance = 0.0
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route_indices.append(node)
            next_index = assignment.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(next_index)
            total_distance += distance_matrix.matrix[node][next_node]
            index = next_index
        node = manager.IndexToNode(index)
        route_indices.append(node)

        order = [point_ids_by_index[i] for i in route_indices]
        pickup_ids = [pid for pid in order if pid not in {order[0], order[-1]}]
        if not pickup_ids:
            continue
        vehicle = vehicles[v]
        # NOTE: Stage A trip cost details are for reference; total_demand_kg is applied later when
        # building physical routes (Stage B) where pickup quantities are known.
        breakdown = _evaluate_cost(vehicle, total_distance, vehicle_metadata_map, total_demand_kg=0)
        trips.append(
            TripRoute(
                vehicle=vehicle,
                pickup_ids=pickup_ids,
                order=order,
                total_distance_m=total_distance,
                cost_breakdown=breakdown,
            )
        )
    return trips


def _prepare_indices(distance_matrix: DistanceMatrix) -> Tuple[List[str], Dict[str, int]]:
    ordered: List[str] = [None] * len(distance_matrix.index_map)
    for point_id, idx in distance_matrix.index_map.items():
        ordered[idx] = point_id
    return ordered, distance_matrix.index_map


def _solve_stage_a_trips(
    distance_matrix: DistanceMatrix,
    depot: str,
    sink: str,
    pickups: Sequence[Mapping[str, object]],
    vehicles: Sequence[VehicleType],
    master: Optional[ProcessedMasterData],
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]],
    *,
    time_limit_s: int = 8,
) -> Union[List[TripRoute], NoSolution]:
    if not ORTOOLS_AVAILABLE:
        return NoSolution(NoSolutionReason.INFEASIBLE, "OR-Toolsが見つかりません。統合最適化を実行できません。")

    point_ids_by_index, index_map = _prepare_indices(distance_matrix)
    depot_idx = index_map[depot]
    sink_idx = index_map[sink]

    demands = [0] * len(point_ids_by_index)
    pickup_indices: List[int] = []
    pickup_kinds: Dict[int, str] = {}
    for p in pickups:
        pid = str(p.get("id") or "")
        if not pid:
            continue
        qty = int(p.get("qty") or p.get("demand") or 0)
        kind = str(p.get("kind") or "")
        idx = index_map[pid]
        demands[idx] = max(0, qty)
        pickup_indices.append(idx)
        pickup_kinds[idx] = kind

    # Validate compatibility coverage for each pickup.
    for idx in pickup_indices:
        kind = pickup_kinds.get(idx, "")
        allowed = [v for v in vehicles if _vehicle_supports_resource(v.name, kind, master)]
        if not allowed:
            return NoSolution(NoSolutionReason.INFEASIBLE, f"資源[{kind}]に対応できる車両がありません。")

    starts = [depot_idx] * len(vehicles)
    ends = [sink_idx] * len(vehicles)
    manager = pywrapcp.RoutingIndexManager(len(point_ids_by_index), len(vehicles), starts, ends)
    routing = pywrapcp.RoutingModel(manager)

    # Per-vehicle arc cost:
    # - distance-based (yen/m): fixed_cost_per_km + variable_per_km + driver_per_km
    # - node-based (yen): demand(to)[kg] * work_yen_per_kg
    callback_indices: List[int] = []
    for vehicle in vehicles:
        meta = vehicle_metadata_map.get(vehicle.name) if vehicle_metadata_map else None
        hourly_wage = float(getattr(meta, "hourly_wage", 0.0) or 0.0)
        avg_speed = float(getattr(meta, "average_speed_km_per_h", 0.0) or 0.0)
        loading_sec_per_kg = float(getattr(meta, "loading_time_per_kg", 0.0) or 0.0)

        driver_per_km = (hourly_wage / avg_speed) if (hourly_wage > 0 and avg_speed > 0) else 0.0
        work_yen_per_kg = (hourly_wage * loading_sec_per_kg / 3600.0) if (hourly_wage > 0 and loading_sec_per_kg > 0) else 0.0

        yen_per_m = (float(vehicle.fixed_cost_per_km) + float(vehicle.per_km_cost) + float(driver_per_km)) / 1000.0

        def _mk_cb(rate: float, node_rate: float):
            def _cb(from_index: int, to_index: int) -> int:
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                distance = distance_matrix.matrix[from_node][to_node]
                if distance >= UNREACHABLE_COST:
                    return int(UNREACHABLE_COST)
                demand_to = int(demands[to_node]) if 0 <= to_node < len(demands) else 0
                return int(round(distance * rate + demand_to * node_rate))

            return _cb

        cb_idx = routing.RegisterTransitCallback(_mk_cb(yen_per_m, work_yen_per_kg))
        callback_indices.append(cb_idx)

    for v, cb_idx in enumerate(callback_indices):
        routing.SetArcCostEvaluatorOfVehicle(cb_idx, v)

    def demand_cb(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        return int(demands[node])

    demand_cb_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_cb_idx,
        0,
        [int(v.capacity_kg) for v in vehicles],
        True,
        "Capacity",
    )

    # Compatibility: restrict allowed vehicles per pickup.
    for pickup_idx in pickup_indices:
        kind = pickup_kinds.get(pickup_idx, "")
        allowed_vehicle_ids = [i for i, v in enumerate(vehicles) if _vehicle_supports_resource(v.name, kind, master)]
        if allowed_vehicle_ids:
            routing.SetAllowedVehiclesForIndex(allowed_vehicle_ids, manager.NodeToIndex(pickup_idx))

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.seconds = int(max(1, time_limit_s))

    assignment = routing.SolveWithParameters(search_params)
    if assignment is None:
        return NoSolution(NoSolutionReason.INFEASIBLE, "OR-Toolsで解が見つかりませんでした。")

    return _extract_used_routes(distance_matrix, manager, routing, assignment, point_ids_by_index, vehicles, vehicle_metadata_map)


def solve_integrated_routing(
    distance_matrix: DistanceMatrix,
    depot: str,
    sink: str,
    pickup_inputs: Sequence[PickupInput],
    vehicle_types: Sequence[VehicleType],
    master: Optional[ProcessedMasterData] = None,
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]] = None,
    *,
    max_physical_vehicles: int = 4,
    max_trips: int = 5,
) -> Union[IntegratedFleetSolution, NoSolution]:
    """
    Integrated optimisation entry point (scaffold).

    Returns an `IntegratedFleetSolution` which contains a regular `FleetSolution` for UI
    compatibility plus trip-level details for debugging/extended reporting.
    """
    if depot == sink:
        return NoSolution(NoSolutionReason.INFEASIBLE, "車庫と集積場所は異なるノードを選択してください。")

    pickups = _normalise_pickups(pickup_inputs)
    if not pickups:
        return NoSolution(NoSolutionReason.INFEASIBLE, "回収地点がありません。")

    if not vehicle_types:
        return NoSolution(NoSolutionReason.INFEASIBLE, "車種候補がありません。")

    # Stage A: select up to `max_trips` vehicle slots that cover required resources (greedy), then VRP.
    required = _required_resources(pickups)
    sorted_types = sorted(
        vehicle_types,
        key=lambda v: ((float(v.fixed_cost_per_km) + float(v.per_km_cost)), -int(v.capacity_kg)),
    )

    selected: List[VehicleType] = []
    for res in required:
        candidates = [v for v in sorted_types if _vehicle_supports_resource(v.name, res, master)]
        if candidates:
            selected.append(candidates[0])
    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: List[VehicleType] = []
    for v in selected:
        if v.name in seen:
            continue
        seen.add(v.name)
        deduped.append(v)
    selected = deduped

    # Fill remaining slots with cheapest vehicles (allow duplicates by repeating cheapest).
    while len(selected) < max_trips and sorted_types:
        selected.append(sorted_types[min(len(selected), len(sorted_types) - 1)])
    selected = selected[: max(1, int(max_trips))]

    stage_a = _solve_stage_a_trips(
        distance_matrix,
        depot,
        sink,
        pickups,
        selected,
        master,
        vehicle_metadata_map,
    )
    if isinstance(stage_a, NoSolution):
        return stage_a
    trips = stage_a

    if not trips:
        return NoSolution(NoSolutionReason.INFEASIBLE, "解が見つかりませんでした。")

    # Stage B: fit trips into <= max_physical_vehicles by merging at most one pair (5->4).
    return_leg = distance_matrix.distance(sink, depot)
    if return_leg >= UNREACHABLE_COST:
        return NoSolution(NoSolutionReason.DISCONNECTED, "集積場所から車庫へ戻れません。")

    # Precompute pickup lookup (qty/kind).
    pickup_lookup: Dict[str, Dict[str, object]] = {str(p["id"]): dict(p) for p in pickups}

    def trip_demand(trip: TripRoute) -> int:
        return int(sum(int(pickup_lookup[pid].get("qty") or 0) for pid in trip.pickup_ids if pid in pickup_lookup))

    def trip_pickups_payload(trip: TripRoute) -> List[Dict[str, object]]:
        return [{"id": pid, "demand": int(pickup_lookup.get(pid, {}).get("qty") or 0)} for pid in trip.pickup_ids]

    def trip_kinds(trip: TripRoute) -> List[str]:
        return [str(pickup_lookup.get(pid, {}).get("kind") or "") for pid in trip.pickup_ids]

    def vehicle_can_cover_trip(vehicle: VehicleType, trip: TripRoute) -> bool:
        if vehicle.capacity_kg < trip_demand(trip):
            return False
        kinds = trip_kinds(trip)
        return all(_vehicle_supports_resource(vehicle.name, k, master) for k in kinds if k)

    def make_physical_route(vehicle: VehicleType, order: List[str], distance_m: float, pickup_ids: List[str]) -> VehicleRoute:
        full_order = list(order)
        if full_order[-1] != sink:
            # Defensive: enforce ending at sink before returning to depot
            full_order.append(sink)
        full_order.append(depot)
        total_distance = float(distance_m) + float(return_leg)
        total_demand = int(sum(int(pickup_lookup.get(pid, {}).get("qty") or 0) for pid in pickup_ids))
        breakdown = _evaluate_cost(vehicle, total_distance, vehicle_metadata_map, total_demand_kg=total_demand)
        return VehicleRoute(
            vehicle=vehicle,
            pickups=list(pickup_ids),
            solution=Solution(vehicle=vehicle, order=full_order, total_distance_m=total_distance, cost_breakdown=breakdown),
        )

    if len(trips) <= max_physical_vehicles:
        routes: List[VehicleRoute] = []
        totals: Dict[str, float] = defaultdict(float)
        for trip in trips:
            routes.append(make_physical_route(trip.vehicle, trip.order, trip.total_distance_m, trip.pickup_ids))
        for r in routes:
            for k, v in r.solution.cost_breakdown.items():
                totals[k] += float(v)
        totals.setdefault("fixed_cost", 0.0)
        totals.setdefault("distance_cost", 0.0)
        totals["total_cost"] = totals["fixed_cost"] + totals["distance_cost"]
        fleet = FleetSolution(routes=routes, cost_breakdown=dict(totals))
        return IntegratedFleetSolution(fleet=fleet, trips=trips, vehicle_count=len(routes), trip_count=len(trips))

    if len(trips) != max_physical_vehicles + 1:
        return NoSolution(
            NoSolutionReason.INFEASIBLE,
            f"便数({len(trips)})が上限を超えています（最大{max_physical_vehicles+1}便まで対応）。",
        )

    # Try merging any pair; choose minimal total cost.
    best: Optional[IntegratedFleetSolution] = None

    for i in range(len(trips)):
        for j in range(i + 1, len(trips)):
            other = [t for k, t in enumerate(trips) if k not in {i, j}]
            trip_a, trip_b = trips[i], trips[j]

            candidates = [v for v in vehicle_types if vehicle_can_cover_trip(v, trip_a) and vehicle_can_cover_trip(v, trip_b)]
            if not candidates:
                continue

            for vehicle in candidates:
                # Re-optimise A: depot -> ... -> sink
                sol_a = solve_path_routing(distance_matrix, trip_pickups_payload(trip_a), depot, sink, vehicle, vehicle_metadata_map)
                if isinstance(sol_a, NoSolution):
                    continue
                # Re-optimise B: sink -> ... -> sink (2nd trip after unloading)
                sol_b = solve_path_routing(distance_matrix, trip_pickups_payload(trip_b), sink, sink, vehicle, vehicle_metadata_map)
                if isinstance(sol_b, NoSolution):
                    continue

                merged_distance = float(sol_a.total_distance_m) + float(sol_b.total_distance_m)
                merged_order = list(sol_a.order) + list(sol_b.order[1:])  # avoid duplicate sink
                merged_pickups = list(trip_a.pickup_ids) + list(trip_b.pickup_ids)
                merged_route = make_physical_route(vehicle, merged_order, merged_distance, merged_pickups)

                routes: List[VehicleRoute] = [merged_route] + [make_physical_route(t.vehicle, t.order, t.total_distance_m, t.pickup_ids) for t in other]
                totals: Dict[str, float] = defaultdict(float)
                for r in routes:
                    for k, v in r.solution.cost_breakdown.items():
                        totals[k] += float(v)
                totals.setdefault("fixed_cost", 0.0)
                totals.setdefault("distance_cost", 0.0)
                totals["total_cost"] = totals["fixed_cost"] + totals["distance_cost"]
                fleet = FleetSolution(routes=routes, cost_breakdown=dict(totals))
                cand = IntegratedFleetSolution(fleet=fleet, trips=trips, vehicle_count=len(routes), trip_count=len(trips))

                if best is None or cand.fleet.cost < best.fleet.cost:
                    best = cand

    if best is None:
        return NoSolution(NoSolutionReason.INFEASIBLE, "4台以内にまとめられませんでした。")
    return best

