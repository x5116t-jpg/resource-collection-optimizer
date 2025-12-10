"""Routing solver backed by OR-Tools with graceful fallback."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .distance_matrix import DistanceMatrix, UNREACHABLE_COST
from .vehicle_catalog import VehicleType
from .master_repository import VehicleCandidate

try:  # pragma: no cover - optional dependency
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2  # type: ignore

    ORTOOLS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    ORTOOLS_AVAILABLE = False


class NoSolutionReason(str, Enum):
    CAPACITY = "capacity"
    DISCONNECTED = "disconnected"
    INFEASIBLE = "infeasible"


@dataclass(frozen=True)
class Solution:
    """Routing solution with aggregated metrics."""

    vehicle: VehicleType
    order: List[str]
    total_distance_m: float
    cost_breakdown: Dict[str, float]

    @property
    def cost(self) -> float:
        return float(self.cost_breakdown.get("total_cost", 0.0))

    @property
    def is_feasible(self) -> bool:
        return True


@dataclass(frozen=True)
class NoSolution:
    """Represents an infeasible routing outcome."""

    reason: NoSolutionReason
    message: str = ""

    @property
    def is_feasible(self) -> bool:
        return False


PickupInput = Mapping[str, Union[str, int, float]]


@dataclass(frozen=True)
class VehicleRoute:
    """Single vehicle route within a fleet solution."""

    vehicle: VehicleType
    pickups: List[str]
    solution: Solution

    @property
    def total_distance_m(self) -> float:
        return float(self.solution.total_distance_m)

    @property
    def cost(self) -> float:
        return self.solution.cost


@dataclass(frozen=True)
class FleetSolution:
    """Composite solution covering multiple vehicles."""

    routes: List[VehicleRoute]
    cost_breakdown: Dict[str, float]

    @property
    def cost(self) -> float:
        return float(self.cost_breakdown.get("total_cost", 0.0))

    @property
    def total_distance_m(self) -> float:
        return float(sum(route.total_distance_m for route in self.routes))

    @property
    def is_feasible(self) -> bool:
        return bool(self.routes)


def _normalise_pickups(pickups: Sequence[PickupInput]) -> List[Dict[str, Union[str, int]]]:
    normalised: List[Dict[str, Union[str, int]]] = []
    for entry in pickups:
        point_id = entry.get("id")
        if not point_id:
            raise ValueError("Pickup requires an 'id'")
        demand = int(entry.get("demand", 0))
        normalised.append({"id": str(point_id), "demand": max(0, demand)})
    return normalised


def _ensure_sequence(vehicles: Union[Iterable[VehicleType], VehicleType]) -> List[VehicleType]:
    if isinstance(vehicles, VehicleType):
        return [vehicles]
    return list(vehicles)


def _compute_route_order(depot: str, pickup_ids: Sequence[str], sink: str) -> List[str]:
    route = [depot]
    route.extend(pickup_ids)
    route.append(sink)
    route.append(depot)
    return route


def _route_distance(distance_matrix: DistanceMatrix, order: Sequence[str]) -> float:
    distance = 0.0
    for start, end in zip(order[:-1], order[1:]):
        step = distance_matrix.distance(start, end)
        if step >= UNREACHABLE_COST:
            return UNREACHABLE_COST
        distance += step
    return distance


def _evaluate_cost(
    vehicle: VehicleType,
    distance_m: float,
    vehicle_metadata: Optional[VehicleCandidate] = None
) -> Dict[str, float]:
    """
    車両のコストとエネルギー消費量を評価し、詳細内訳を含むcost_breakdownを返す。

    Args:
        vehicle: 最適化用の車両タイプ
        distance_m: 走行距離(m)
        vehicle_metadata: 詳細内訳情報（Noneの場合は基本3項目のみ）

    Returns:
        cost_breakdown辞書（基本3項目 + エネルギー消費量 + 詳細内訳）
    """
    distance_km = distance_m / 1000.0

    # 基本計算（既存ロジック）
    variable_cost = vehicle.distance_cost(distance_m)
    fixed_cost = vehicle.fixed_cost_for_distance(distance_m)
    total_cost = fixed_cost + variable_cost

    result = {
        "fixed_cost": int(fixed_cost),
        "distance_cost": int(variable_cost),
        "total_cost": int(total_cost),
        "distance_km": distance_km,
    }

    # ✨ 新規追加: エネルギー消費量計算
    if vehicle.energy_consumption_kwh_per_km > 0:
        energy_kwh = vehicle.energy_consumption_kwh(distance_m)
        result["energy_consumption_kwh"] = round(energy_kwh, 3)  # 小数点3桁で丸め

    # 詳細内訳の計算（新規ロジック）
    if vehicle_metadata is None:
        return result

    # 変動費詳細
    if vehicle_metadata.variable_cost_breakdown:
        for item_name, unit_cost in vehicle_metadata.variable_cost_breakdown.items():
            try:
                key = f"変動費_{item_name}"
                result[key] = int(float(unit_cost) * distance_km)
            except (ValueError, TypeError):
                continue

    # 固定費詳細
    if vehicle_metadata.fixed_cost_breakdown and vehicle_metadata.annual_distance_km:
        if vehicle_metadata.annual_distance_km > 0:
            for item_name, annual_manyen in vehicle_metadata.fixed_cost_breakdown.items():
                try:
                    # 万円 → 円 変換
                    annual_yen = float(annual_manyen) * 10000
                    # km単価計算
                    per_km = annual_yen / vehicle_metadata.annual_distance_km
                    # この走行距離での費用
                    key = f"固定費_{item_name}"
                    result[key] = int(per_km * distance_km)
                except (ValueError, TypeError, ZeroDivisionError):
                    continue

    return result


def _detect_disconnects(distance_matrix: DistanceMatrix, depot: str, sink: str, pickups: Sequence[Dict[str, Union[str, int]]]) -> bool:
    """Return True if any required leg is unreachable."""

    checkpoints = set([sink, depot] + [p["id"] for p in pickups])
    for point in checkpoints:
        if not distance_matrix.is_reachable(depot, point):
            return True
        if not distance_matrix.is_reachable(point, depot):
            return True
    if not distance_matrix.is_reachable(depot, sink) or not distance_matrix.is_reachable(sink, depot):
        return True
    for pickup in pickups:
        pid = pickup["id"]
        if not distance_matrix.is_reachable(pid, sink):
            return True
    return False


def _solve_simple(
    distance_matrix: DistanceMatrix,
    pickups: Sequence[Dict[str, Union[str, int]]],
    depot: str,
    sink: str,
    vehicles: Sequence[VehicleType],
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]] = None,
) -> Union[Solution, NoSolution]:
    """Fallback heuristic identical to旧スタブ実装."""

    order = _compute_route_order(depot, [entry["id"] for entry in pickups], sink)
    total_distance = _route_distance(distance_matrix, order)
    if total_distance >= UNREACHABLE_COST:
        return NoSolution(NoSolutionReason.DISCONNECTED, "到達不能な区間があります。")

    best_solution: Union[Solution, None] = None
    for vehicle in vehicles:
        metadata = vehicle_metadata_map.get(vehicle.name) if vehicle_metadata_map else None
        breakdown = _evaluate_cost(vehicle, total_distance, metadata)
        solution = Solution(
            vehicle=vehicle,
            order=list(order),
            total_distance_m=total_distance,
            cost_breakdown=breakdown,
        )
        if best_solution is None or solution.cost < best_solution.cost:
            best_solution = solution

    if best_solution is None:
        return NoSolution(NoSolutionReason.INFEASIBLE, "解が見つかりませんでした。")
    return best_solution


def _prepare_indices(distance_matrix: DistanceMatrix) -> Tuple[List[str], Dict[str, int]]:
    ordered: List[str] = [None] * len(distance_matrix.index_map)
    for point_id, idx in distance_matrix.index_map.items():
        ordered[idx] = point_id
    return ordered, distance_matrix.index_map


def _solve_with_ortools(
    distance_matrix: DistanceMatrix,
    pickups: Sequence[Dict[str, Union[str, int]]],
    depot: str,
    sink: str,
    vehicles: Sequence[VehicleType],
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]] = None,
) -> Union[Solution, NoSolution]:
    point_ids_by_index, index_map = _prepare_indices(distance_matrix)
    depot_idx = index_map[depot]
    sink_idx = index_map[sink]
    pickup_indices = [index_map[entry["id"]] for entry in pickups]
    demands = [0] * len(point_ids_by_index)
    for entry in pickups:
        demands[index_map[entry["id"]]] = int(entry["demand"])

    best_solution: Union[Solution, None] = None

    for vehicle in vehicles:
        manager = pywrapcp.RoutingIndexManager(len(point_ids_by_index), 1, depot_idx, depot_idx)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            distance = distance_matrix.matrix[from_node][to_node]
            if distance >= UNREACHABLE_COST:
                return int(UNREACHABLE_COST)
            return int(round(distance))

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        def demand_callback(from_index: int) -> int:
            node = manager.IndexToNode(from_index)
            return int(demands[node])

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            [vehicle.capacity_kg],
            True,
            "Capacity",
        )

        def order_callback(from_index: int, to_index: int) -> int:
            del from_index, to_index
            return 1

        order_callback_index = routing.RegisterTransitCallback(order_callback)
        routing.AddDimension(
            order_callback_index,
            0,
            len(point_ids_by_index) + 1,
            True,
            "Order",
        )
        order_dimension = routing.GetDimensionOrDie("Order")

        sink_routing_index = routing.NodeToIndex(sink_idx)
        for pickup_idx in pickup_indices:
            pickup_index = routing.NodeToIndex(pickup_idx)
            routing.solver().Add(
                order_dimension.CumulVar(pickup_index) <= order_dimension.CumulVar(sink_routing_index) - 1
            )

        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = 5

        assignment = routing.SolveWithParameters(search_params)
        if assignment is None:
            continue

        index = routing.Start(0)
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

        route_order = [point_ids_by_index[i] for i in route_indices]
        metadata = vehicle_metadata_map.get(vehicle.name) if vehicle_metadata_map else None
        breakdown = _evaluate_cost(vehicle, total_distance, metadata)
        solution = Solution(
            vehicle=vehicle,
            order=route_order,
            total_distance_m=total_distance,
            cost_breakdown=breakdown,
        )
        if best_solution is None or solution.cost < best_solution.cost:
            best_solution = solution

    if best_solution is None:
        return NoSolution(NoSolutionReason.INFEASIBLE, "OR-Toolsで解が見つかりませんでした。")
    return best_solution


def solve_routing(
    distance_matrix: DistanceMatrix,
    pickups: Sequence[PickupInput],
    depot: str,
    sink: str,
    vehicles: Union[Iterable[VehicleType], VehicleType],
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]] = None,
) -> Union[Solution, NoSolution]:
    """Compute optimum route using OR-Tools when利用可、不可時は簡易解を提供。"""

    pickup_entries = _normalise_pickups(pickups)
    total_demand = sum(max(0, entry["demand"]) for entry in pickup_entries)
    candidate_vehicles = [v for v in _ensure_sequence(vehicles) if v.capacity_kg >= total_demand]
    if not candidate_vehicles:
        return NoSolution(NoSolutionReason.CAPACITY, "容量を満たす車種がありません。")

    if _detect_disconnects(distance_matrix, depot, sink, pickup_entries):
        return NoSolution(NoSolutionReason.DISCONNECTED, "到達不能な区間があります。")

    if not pickup_entries:
        base_order = _compute_route_order(depot, [], sink)
        total_distance = _route_distance(distance_matrix, base_order)
        metadata = vehicle_metadata_map.get(candidate_vehicles[0].name) if vehicle_metadata_map else None
        breakdown = _evaluate_cost(candidate_vehicles[0], total_distance, metadata)
        return Solution(
            vehicle=candidate_vehicles[0],
            order=base_order,
            total_distance_m=total_distance,
            cost_breakdown=breakdown,
        )

    if ORTOOLS_AVAILABLE:
        try:
            return _solve_with_ortools(distance_matrix, pickup_entries, depot, sink, candidate_vehicles, vehicle_metadata_map)
        except Exception:  # pragma: no cover - safety net
            pass

    return _solve_simple(distance_matrix, pickup_entries, depot, sink, candidate_vehicles, vehicle_metadata_map)


def solve_fleet_routing(
    distance_matrix: DistanceMatrix,
    depot: str,
    sink: str,
    assignments: Sequence[Tuple[VehicleType, Sequence[PickupInput]]],
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]] = None,
) -> Union[FleetSolution, NoSolution]:
    routes: List[VehicleRoute] = []
    totals: Dict[str, float] = defaultdict(float)

    for vehicle, pickup_group in assignments:
        payload: List[Dict[str, Union[str, int]]] = []
        for item in pickup_group:
            point_id = item.get("id")
            if point_id is None:
                continue
            demand_value = item.get("demand", item.get("qty", 0))
            payload.append({"id": str(point_id), "demand": int(demand_value or 0)})

        if not payload:
            continue

        result = solve_routing(distance_matrix, payload, depot, sink, [vehicle], vehicle_metadata_map)
        if isinstance(result, NoSolution):
            return result

        routes.append(
            VehicleRoute(
                vehicle=result.vehicle,
                pickups=[entry["id"] for entry in payload],
                solution=result,
            )
        )
        for key, value in result.cost_breakdown.items():
            totals[key] += float(value)

    if not routes:
        return NoSolution(NoSolutionReason.INFEASIBLE, "回収対象の割り当てが見つかりません。")

    totals.setdefault("fixed_cost", 0.0)
    totals.setdefault("distance_cost", 0.0)
    totals.setdefault("total_cost", totals["fixed_cost"] + totals["distance_cost"])
    return FleetSolution(routes=routes, cost_breakdown=dict(totals))
