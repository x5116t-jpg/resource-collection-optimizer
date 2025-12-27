"""Streamlit entry point connecting UI and service layers."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import streamlit as st  # type: ignore

import networkx as nx


def _get_base_path() -> Path:
    """Get the base path for data files, works in both development and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # PyInstaller runtime: use _MEIPASS (temporary extraction directory)
        return Path(sys._MEIPASS)
    else:
        # Development: use the project root (parent of src/)
        return Path(__file__).parent.parent


def _get_data_dir() -> Path:
    """Get the data directory path."""
    return _get_base_path() / "data"

from services import (
    NoSolution,
    FleetSolution,
    PointRegistry,
    PointType,
    VehicleCatalog,
    ResourceInfo,
    Solution,
    build_distance_matrix,
    solve_fleet_routing,
    ProcessedMasterData,
    load_processed_master,
)
from services.master_repository import VehicleCandidate
from services.route_reconstruction import reconstruct_paths
from services.spatial_index import SpatialIndex
from services.ecom10_comparison import (
    compute_ecom10_alternative,
    find_alternative_vehicles,
    eCOM10CompatibilityResult,
)

try:  # pandas is optional but improves the UI
    import pandas as pd  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    pd = None  # type: ignore


DEFAULT_VEHICLE_RECORDS: List[Dict[str, float]] = [
    {"name": "small", "capacity_kg": 500, "fixed_cost": 10000.0, "per_km_cost": 120.0},
    {"name": "large", "capacity_kg": 1500, "fixed_cost": 18000.0, "per_km_cost": 90.0},
]


MODE_TO_ROLE = {
    "車庫": "depot",
    "回収地点": "pickup",
    "集積場所": "sink",
}

ROLE_TO_COLOR = {
    "depot": "green",
    "pickup": "blue",
    "sink": "red",
}


@dataclass(frozen=True)
class SelectedPoint:
    node_id: str
    lat: float
    lon: float
    role: str
    label: str


def _list_network_files() -> Dict[str, Path]:
    data_dir = _get_data_dir()
    files = sorted(data_dir.glob("road_network_*.json"))
    return {file.name: file for file in files}


@st.cache_resource(show_spinner=False)
def load_graph(json_path: str):
    path = Path(json_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.DiGraph()
    for node_id, node in data.get("nodes", {}).items():
        graph.add_node(node_id, lat=node.get("lat"), lon=node.get("lon"), name=node.get("name"))
    for edge in data.get("edges", []):
        length = float(edge.get("weight", 0.0))
        graph.add_edge(edge["from"], edge["to"], length=length, highway_type=edge.get("highway_type"))
    metadata = data.get("metadata", {})
    return graph, metadata


@st.cache_data(show_spinner=False)
def cached_distance_matrix(json_path: str, node_ids: Tuple[str, ...]):
    graph, _ = load_graph(json_path)
    points = [{"id": node_id, "osmid": node_id} for node_id in node_ids]
    return build_distance_matrix(graph, points)


@st.cache_resource(show_spinner=False)
def load_processed_master_cached() -> Optional[ProcessedMasterData]:
    processed_dir = _get_data_dir() / "processed"
    if not processed_dir.exists():
        return None
    try:
        return load_processed_master(processed_dir)
    except FileNotFoundError:
        st.warning("processed データが見つかりません。`scripts/build_master_data.py` を先に実行してください。")
    except Exception as exc:  # pragma: no cover - defensive
        st.warning(f"マスタデータの読込に失敗しました: {exc}")
    return None


def _generate_vehicle_defaults(
    master: Optional[ProcessedMasterData],
) -> Tuple[List[Dict[str, float]], Dict[str, Dict[str, float]]]:
    if not master or not master.vehicles:
        metadata = {record["name"]: {} for record in DEFAULT_VEHICLE_RECORDS}
        return [dict(record) for record in DEFAULT_VEHICLE_RECORDS], metadata

    vehicles: List[Dict[str, float]] = []
    metadata: Dict[str, Dict[str, float]] = {}
    for candidate in master.vehicles:
        if candidate.capacity_kg is None:
            # 備考行など車両仕様が未設定のレコードはスキップ
            continue
        capacity = int(round(candidate.capacity_kg or 0))
        # 年間固定費は距離当たり単価で評価するためベース固定費は 0 とする
        fixed_cost = 0.0
        per_km_cost = round(candidate.variable_cost_per_km, 2)
        vehicles.append(
            {
                "name": candidate.name,
                "capacity_kg": capacity,
                "fixed_cost": fixed_cost,
                "per_km_cost": per_km_cost,
                "fixed_cost_per_km": candidate.fixed_cost_per_km,
                "energy_consumption_kwh_per_km": candidate.energy_consumption_kwh_per_km or 0.0,
            }
        )
        metadata[candidate.name] = {
            "annual_fixed_cost": candidate.annual_fixed_cost,
            "fixed_cost_per_km": candidate.fixed_cost_per_km,
            "variable_cost_per_km": candidate.variable_cost_per_km,
            "energy_consumption_kwh_per_km": candidate.energy_consumption_kwh_per_km or 0.0,
        }
    return vehicles, metadata


def _format_range(range_dict: Optional[Dict[str, float]], unit: str) -> Optional[str]:
    if not range_dict:
        return None
    minimum = range_dict.get("min")
    maximum = range_dict.get("max")
    if minimum is None and maximum is None:
        return None
    if minimum == maximum:
        return f"{minimum}{unit}"
    return f"{minimum}〜{maximum}{unit}"


def _resource_summary(resource: ResourceInfo) -> List[str]:
    lines: List[str] = []
    density = _format_range(resource.bulk_density, "t/m³")
    gate_fee = _format_range(resource.gate_fee, "円/t")
    if resource.constraint_type:
        lines.append(f"制約: {resource.constraint_type}")
    if density:
        lines.append(f"嵩密度: {density}")
    if gate_fee:
        lines.append(f"ゲート料: {gate_fee}")
    if resource.treatment:
        lines.append(f"処理: {resource.treatment}")
    if resource.notes:
        lines.append(f"備考: {resource.notes}")
    return lines

def _init_session_state(master: Optional[ProcessedMasterData]) -> None:
    if "vehicles" not in st.session_state:
        vehicles, metadata = _generate_vehicle_defaults(master)
        st.session_state["vehicles"] = vehicles
        st.session_state["vehicle_metadata"] = metadata
    else:
        st.session_state.setdefault("vehicle_metadata", {})
    st.session_state.setdefault("pickup_attrs", {})
    st.session_state.setdefault("depot_id", None)
    st.session_state.setdefault("sink_id", None)
    st.session_state.setdefault("pickup_selection", [])
    st.session_state.setdefault("node_coords_cache", {})
    st.session_state.setdefault("spatial_index_cache", {})
    st.session_state.setdefault("last_click_token", None)
    st.session_state.setdefault("last_selected_node", None)
    st.session_state.setdefault("last_selected_role", None)
    st.session_state.setdefault("vehicle_requirements", {})
    st.session_state.setdefault("vehicle_filter_warnings", [])
    st.session_state.setdefault("required_resources", [])
    st.session_state.setdefault("pending_pickup", None)
    st.session_state.setdefault("pending_pickup_defaults", {})
    st.session_state.setdefault("pickup_dialog_open", False)
    st.session_state.setdefault("pickup_dialog_result", None)
    st.session_state.setdefault("pickup_dialog_rendered", False)
    st.session_state.setdefault("map_focus_token", None)
    st.session_state.setdefault("map_feedback", None)


def _toast(message: str, icon: str = "") -> None:
    toast_fn = getattr(st, "toast", None)
    if callable(toast_fn):
        toast_fn(message, icon=icon)
    else:  # pragma: no cover - fallback for older Streamlit
        if icon:
            st.info(f"{icon} {message}")
        else:
            st.info(message)


def _set_last_selection(node_id: Optional[str], role: Optional[str]) -> None:
    st.session_state["last_selected_node"] = node_id
    st.session_state["last_selected_role"] = role


def _clear_pending_pickup() -> None:
    st.session_state["pending_pickup"] = None
    st.session_state["pending_pickup_defaults"] = {}
    st.session_state["pickup_dialog_open"] = False
    st.session_state["pickup_dialog_rendered"] = False


def _set_map_feedback(kind: str, message: str) -> None:
    st.session_state["map_feedback"] = {"kind": kind, "message": message}


def _consume_map_feedback() -> Optional[Tuple[str, str]]:
    feedback = st.session_state.get("map_feedback")
    if isinstance(feedback, dict):
        message = str(feedback.get("message") or "")
        kind = str(feedback.get("kind") or "info")
        st.session_state["map_feedback"] = None
        if message:
            return kind, message
    return None


def _render_map_feedback() -> None:
    feedback = _consume_map_feedback()
    if not feedback:
        return
    kind, message = feedback
    if kind == "success":
        st.success(message)
    elif kind == "warning":
        st.warning(message, icon="⚠️")
    elif kind == "error":
        st.error(message)
    else:
        st.info(message)


def _detect_abandoned_pickup_dialog() -> None:
    if st.session_state.get("pickup_dialog_result"):
        return
    if st.session_state.get("pickup_dialog_open"):
        return
    pending = st.session_state.get("pending_pickup")
    if isinstance(pending, dict) and pending.get("node_id"):
        label = str(pending.get("label") or pending.get("node_id"))
        st.session_state["pickup_dialog_result"] = {
            "status": "cancel",
            "label": label,
            "reason": "dismissed",
        }


def _process_pickup_dialog_result() -> None:
    result = st.session_state.get("pickup_dialog_result")
    if not isinstance(result, dict):
        return

    status = str(result.get("status") or "")
    if status == "add":
        node_id = str(result.get("node_id") or "")
        resource = str(result.get("resource") or "")
        qty = int(result.get("qty") or 0)
        label = str(result.get("label") or node_id)
        if not node_id:
            _clear_pending_pickup()
        elif qty <= 0 or not resource:
            _clear_pending_pickup()
            _set_map_feedback("warning", "回収量または資源種別の入力内容が不正です。もう一度入力してください。")
        else:
            _finalise_pending_pickup(node_id, resource, qty)
            st.session_state["map_focus_token"] = {"node_id": node_id, "role": "pickup"}
            message = f"回収地点を追加しました: {label}" if label else f"回収地点を追加しました: {node_id}"
            _set_map_feedback("success", message)
    else:
        pending = st.session_state.get("pending_pickup")
        default_label = ""
        if isinstance(pending, dict):
            default_label = str(pending.get("label") or pending.get("node_id") or "")
        label = str(result.get("label") or default_label)
        _clear_pending_pickup()
        message = f"回収地点の追加をキャンセルしました: {label}" if label else "回収地点の追加をキャンセルしました。"
        _set_map_feedback("info", message)

    st.session_state["pickup_dialog_result"] = None


def _prepare_pending_defaults(
    node_id: str,
    master: Optional[ProcessedMasterData],
) -> Dict[str, object]:
    attrs = st.session_state.get("pickup_attrs", {})
    record = attrs.get(node_id, {}) if isinstance(attrs, dict) else {}
    default_qty = int(record.get("qty", 100)) if isinstance(record, dict) else 100
    default_resource = None
    if isinstance(record, dict):
        default_resource = record.get("resource") or record.get("kind")
    resource_names = sorted(master.resources.keys()) if master and master.resources else []
    if not default_resource and resource_names:
        default_resource = resource_names[0]
    return {"qty": int(default_qty), "resource": default_resource or ""}


def _finalise_pending_pickup(node_id: str, resource: str, qty: int) -> str:
    pickups: List[str] = list(st.session_state.get("pickup_selection", []))
    if node_id not in pickups:
        pickups.append(node_id)
    st.session_state["pickup_selection"] = pickups

    attrs = st.session_state.get("pickup_attrs", {})
    if not isinstance(attrs, dict):
        attrs = {}
    attrs[node_id] = {"qty": int(qty), "kind": resource, "resource": resource}
    st.session_state["pickup_attrs"] = attrs

    _set_last_selection(node_id, "pickup")
    _toast(f"回収地点を追加: {node_id}", icon="➕")
    _clear_pending_pickup()
    return node_id


def _ensure_selection_defaults(node_ids: List[str]) -> None:
    if not node_ids:
        return
    depot_id = st.session_state.get("depot_id")
    if depot_id not in node_ids:
        preferred = _find_closest_node(node_ids, target_lat=36.42025757338635, target_lon=139.3464551140531)
        st.session_state["depot_id"] = preferred or node_ids[0]
    if st.session_state.get("sink_id") not in node_ids:
        preferred = _find_closest_node(node_ids, target_lat=36.424856512788374, target_lon=139.34618718561728)
        st.session_state["sink_id"] = preferred or (node_ids[1] if len(node_ids) > 1 else node_ids[0])
    pickups = [node for node in st.session_state.get("pickup_selection", []) if node in node_ids]
    st.session_state["pickup_selection"] = pickups


def _render_vehicle_editor(master: Optional[ProcessedMasterData]) -> None:
    st.subheader("車種候補")
    vehicles = st.session_state["vehicles"]
    if pd is not None:
        df = pd.DataFrame(vehicles)
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            hide_index=True,
            key="vehicle_editor",
            column_config={
                "name": st.column_config.TextColumn("名称", required=True),
                "capacity_kg": st.column_config.NumberColumn("容量[kg]", min_value=0, step=100),
                "fixed_cost": st.column_config.NumberColumn("固定費[円]", min_value=0, step=1000),
                "per_km_cost": st.column_config.NumberColumn("距離単価[円/km]", min_value=0, step=10),
            },
        )
        st.session_state["vehicles"] = edited.to_dict(orient="records") if pd is not None else vehicles

        # Phase 3-2: リアルタイム検証
        vehicles = st.session_state["vehicles"]
        validation_errors = []
        for idx, vehicle in enumerate(vehicles):
            name = vehicle.get("name", "")
            capacity = vehicle.get("capacity_kg", 0)
            fixed_cost = vehicle.get("fixed_cost", 0)
            per_km_cost = vehicle.get("per_km_cost", 0)

            # 名称チェック
            if not name or str(name).strip() == "":
                validation_errors.append(f"❌ 車種{idx+1}: 名称が未入力です")

            # 容量チェック
            if capacity <= 0:
                validation_errors.append(f"❌ {name or f'車種{idx+1}'}: 容量は1以上を設定してください")

            # コストチェック
            if fixed_cost < 0:
                validation_errors.append(f"❌ {name or f'車種{idx+1}'}: 固定費は0以上を設定してください")
            if per_km_cost < 0:
                validation_errors.append(f"❌ {name or f'車種{idx+1}'}: 距離単価は0以上を設定してください")

            # 重複名称チェック
            if name and str(name).strip() != "":
                duplicate_count = sum(1 for v in vehicles if v.get("name") == name)
                if duplicate_count > 1:
                    validation_errors.append(f"⚠️ {name}: 重複した車種名があります")

        # エラー表示
        if validation_errors:
            st.error("以下の問題を修正してください:")
            for error in validation_errors:
                st.write(error)
        else:
            st.success("✅ 車種設定に問題はありません")

    else:  # pragma: no cover - fallback when pandas is unavailable
        updated: List[Dict[str, float]] = []
        for idx, vehicle in enumerate(vehicles):
            cols = st.columns(4)
            name = cols[0].text_input("名称", value=vehicle.get("name", ""), key=f"veh_name_{idx}")
            capacity = cols[1].number_input(
                "容量[kg]", value=int(vehicle.get("capacity_kg", 0)), min_value=0, step=100, key=f"veh_cap_{idx}"
            )
            fixed_cost = cols[2].number_input(
                "固定費[円]", value=float(vehicle.get("fixed_cost", 0)), min_value=0.0, step=1000.0, key=f"veh_fix_{idx}"
            )
            per_km = cols[3].number_input(
                "距離単価[円/km]", value=float(vehicle.get("per_km_cost", 0)), min_value=0.0, step=10.0, key=f"veh_var_{idx}"
            )
            updated.append(
                {
                    "name": name,
                    "capacity_kg": int(capacity),
                    "fixed_cost": float(fixed_cost),
                    "per_km_cost": float(per_km),
                }
            )
        if st.button("車種を追加", key="vehicle_add"):
            updated.append({"name": "new", "capacity_kg": 0, "fixed_cost": 0.0, "per_km_cost": 0.0})
        st.session_state["vehicles"] = updated

    if master and st.button("マスタから再読込", key="vehicle_reload"):
        vehicles, metadata = _generate_vehicle_defaults(master)
        st.session_state["vehicles"] = vehicles
        st.session_state["vehicle_metadata"] = metadata
        st.rerun()


def _collect_pickup_inputs(
    selected_pickups: List[str],
    master: Optional[ProcessedMasterData],
) -> List[Dict[str, object]]:
    attrs = st.session_state["pickup_attrs"]
    results: List[Dict[str, object]] = []
    required_resources: set[str] = set()
    resources = master.resources if master else {}
    compatibility = master.compatibility if master else {}
    resource_names = sorted(resources.keys()) if resources else []
    current_vehicle_names = {record.get("name") for record in st.session_state.get("vehicles", [])}

    for point_id in selected_pickups:
        defaults = attrs.get(point_id, {"qty": 100, "kind": "紙"})
        if "resource" not in defaults and "kind" in defaults:
            defaults["resource"] = defaults.get("kind")
        col_qty, col_kind = st.columns(2)
        qty = col_qty.number_input(
            f"{point_id} 量[kg]",
            min_value=0,
            value=int(defaults.get("qty", 0)),
            step=50,
            key=f"pickup_qty_{point_id}",
        )
        if resource_names:
            default_resource = defaults.get("resource") or resource_names[0]
            try:
                default_index = resource_names.index(default_resource)
            except ValueError:
                default_index = 0
            selected_resource = col_kind.selectbox(
                f"{point_id} 資源種別",
                resource_names,
                index=default_index,
                key=f"pickup_resource_{point_id}",
            )
            resource_info = resources.get(selected_resource)
            attrs[point_id] = {"qty": int(qty), "kind": selected_resource, "resource": selected_resource}
            result = {"id": point_id, "qty": int(qty), "kind": selected_resource}
            results.append(result)
            required_resources.add(selected_resource)

            if resource_info:
                summary_lines = _resource_summary(resource_info)
                if summary_lines:
                    st.caption(" / ".join(summary_lines))

            if compatibility and current_vehicle_names:
                supported = []
                unsupported = []
                for name in current_vehicle_names:
                    if not name:
                        continue
                    compat = compatibility.get(name)
                    if not compat:
                        continue
                    status = compat.supports.get(selected_resource)
                    if status is True:
                        supported.append(name)
                    elif status is False:
                        unsupported.append(name)
                if supported:
                    st.caption(f"適合車種: {', '.join(sorted(supported))}")
                if unsupported:
                    st.warning(f"非適合車種: {', '.join(sorted(unsupported))}", icon="⚠️")
        else:
            kind = col_kind.text_input(
                f"{point_id} 資源種別",
                value=str(defaults.get("kind", "")),
                key=f"pickup_kind_{point_id}",
            )
            attrs[point_id] = {"qty": int(qty), "kind": kind}
            results.append({"id": point_id, "qty": int(qty), "kind": kind})
    for point_id in list(attrs.keys()):
        if point_id not in selected_pickups:
            attrs.pop(point_id)
    st.session_state["required_resources"] = sorted(required_resources)
    return results


def _build_vehicle_catalog(records: List[Dict[str, object]]) -> VehicleCatalog:
    catalog = VehicleCatalog()
    metadata = st.session_state.get("vehicle_metadata", {})
    for record in records:
        name = str(record.get("name") or "").strip()
        if not name:
            continue
        meta = metadata.get(name, {}) if isinstance(metadata, dict) else {}
        catalog.add_vehicle(
            name=name,
            capacity=int(record.get("capacity_kg", 0)),
            fixed_cost=float(record.get("fixed_cost", 0.0)),
            per_km_cost=float(record.get("per_km_cost", 0.0)),
            fixed_cost_per_km=float(record.get("fixed_cost_per_km", 0.0) or 0.0),
            energy_consumption_kwh_per_km=float(record.get("energy_consumption_kwh_per_km", 0.0) or 0.0),
        )
    st.session_state["vehicle_requirements"] = {}
    return catalog


def _vehicle_cost_score(record: Dict[str, object]) -> float:
    name = str(record.get("name") or "").strip()
    per_km = float(record.get("per_km_cost", 0.0) or 0.0)
    fixed_per_km = float(record.get("fixed_cost_per_km", 0.0) or 0.0)
    return per_km + fixed_per_km


def _vehicle_supports_resource(
    name: str,
    resource: str,
    master: Optional[ProcessedMasterData],
) -> bool:
    if not resource:
        return True
    if master is None:
        return True
    if resource not in master.resources:
        return True
    compat = master.compatibility.get(name)
    if compat is None:
        return True
    status = compat.supports.get(resource)
    if status is True:
        return True
    if status is False:
        return False
    return False


def _make_vehicle_type(record: Dict[str, object]) -> "VehicleType":
    from services.vehicle_catalog import VehicleType  # local import to avoid circular type hints

    name = str(record.get("name") or "").strip()
    capacity = int(record.get("capacity_kg", 0) or 0)
    fixed_cost = float(record.get("fixed_cost", 0.0) or 0.0)
    per_km = float(record.get("per_km_cost", 0.0) or 0.0)
    fixed_per_km = float(record.get("fixed_cost_per_km", 0.0) or 0.0)
    energy_kwh_per_km = float(record.get("energy_consumption_kwh_per_km", 0.0) or 0.0)
    return VehicleType(
        name=name,
        capacity_kg=max(0, capacity),
        fixed_cost=fixed_cost,
        per_km_cost=per_km,
        fixed_cost_per_km=fixed_per_km,
        energy_consumption_kwh_per_km=energy_kwh_per_km,
    )


def _calculate_total_demand(pickup_inputs: Sequence[Dict[str, object]]) -> int:
    total_kg = 0
    for pickup in pickup_inputs:
        qty = pickup.get("qty", 0)
        try:
            qty_value = int(qty or 0)
        except (TypeError, ValueError):
            qty_value = 0
        if qty_value <= 0:
            continue
        total_kg += qty_value
    return max(0, total_kg)


def _extract_required_resources(pickup_inputs: Sequence[Dict[str, object]]) -> List[str]:
    resources: set[str] = set()
    for pickup in pickup_inputs:
        kind = pickup.get("kind")
        if not kind:
            continue
        resources.add(str(kind))
    return sorted(resources)


def _group_pickups_by_resource(
    pickup_inputs: Sequence[Dict[str, object]]
) -> Dict[str, List[Dict[str, object]]]:
    """ピックアップを資源種別ごとにグループ化"""
    groups: Dict[str, List[Dict[str, object]]] = {}
    for pickup in pickup_inputs:
        resource = str(pickup.get("kind", ""))
        if not resource:
            continue
        if resource not in groups:
            groups[resource] = []
        groups[resource].append(pickup)
    return groups


def _select_vehicle_for_resource(
    resource: str,
    pickups: List[Dict[str, object]],
    record_map: Dict[str, Dict[str, object]],
    master: Optional[ProcessedMasterData]
) -> Optional[Dict[str, object]]:
    """特定資源種別に対応する最適車両を選択"""
    total_demand = _calculate_total_demand(pickups)

    # この資源をサポートする車両のみフィルタ
    compatible = [
        record for name, record in record_map.items()
        if _vehicle_supports_resource(name, resource, master)
    ]

    if not compatible:
        return None

    # 容量チェック
    capacity_ok = _filter_by_capacity(compatible, total_demand)

    if not capacity_ok:
        return None

    return _select_best_vehicle(capacity_ok)


def _filter_by_resource_compatibility(
    record_map: Dict[str, Dict[str, object]],
    required_resources: Sequence[str],
    master: Optional[ProcessedMasterData],
) -> List[Dict[str, object]]:
    compatible: List[Dict[str, object]] = []
    for name, record in record_map.items():
        if all(_vehicle_supports_resource(name, res, master) for res in required_resources):
            compatible.append(record)
    return compatible


def _filter_by_capacity(
    candidates: Sequence[Dict[str, object]],
    total_demand_kg: int,
) -> List[Dict[str, object]]:
    capacity_ok: List[Dict[str, object]] = []
    for record in candidates:
        try:
            capacity = int(record.get("capacity_kg", 0) or 0)
        except (TypeError, ValueError):
            capacity = 0
        if capacity >= total_demand_kg:
            capacity_ok.append(record)
    return capacity_ok


def _select_best_vehicle(candidates: Sequence[Dict[str, object]]) -> Dict[str, object]:
    return min(candidates, key=_vehicle_cost_score)


def _generate_error_messages(
    compatible_candidates: Sequence[Dict[str, object]],
    total_demand_kg: int,
    required_resources: Sequence[str],
) -> List[str]:
    warnings: List[str] = []
    if not compatible_candidates:
        resources_str = "、".join(required_resources) or "未指定"
        warnings.append(
            f"資源種別 [{resources_str}] に対応できる車種が見つかりません。"
        )
        warnings.append("💡 ヒント: 車種候補の設定またはマスタデータを確認してください。")
        return warnings

    max_capacity = max(
        int(rec.get("capacity_kg", 0) or 0) for rec in compatible_candidates
    )
    shortage = max(0, total_demand_kg - max_capacity)
    warnings.append(
        f"総重量 {total_demand_kg}kg を運搬できる車種が見つかりません。"
    )
    warnings.append(f"💡 最大容量: {max_capacity}kg（不足: {shortage}kg）")

    sorted_vehicles = sorted(
        compatible_candidates,
        key=lambda x: int(x.get("capacity_kg", 0) or 0),
        reverse=True,
    )
    vehicle_info = ", ".join(
        f"{rec.get('name', '')}({rec.get('capacity_kg', 0)}kg)"
        for rec in sorted_vehicles[:5]
    )
    if vehicle_info:
        warnings.append(f"対応可能な車両: {vehicle_info}")
    return warnings


def _plan_vehicle_allocations(
    records: List[Dict[str, object]],
    master: Optional[ProcessedMasterData],
    pickup_inputs: Sequence[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[str]]:
    """
    複数車両での割り当て計画を作成

    資源種別ごとにピックアップをグループ化し、各資源に最適な車両を割り当てます。
    これにより、異なる資源種別を複数の専用車両で運搬できるようになります。
    """
    if not pickup_inputs:
        return [], []

    # 資源種別でグループ化
    resource_groups = _group_pickups_by_resource(pickup_inputs)

    if not resource_groups:
        return [], ["資源種別が指定されていません。"]

    record_map: Dict[str, Dict[str, object]] = {}
    for record in records:
        name = str(record.get("name") or "").strip()
        if not name:
            continue
        record_map[name] = record

    if not record_map:
        return [], ["利用可能な車種が設定されていません。"]

    plan: List[Dict[str, object]] = []
    warnings: List[str] = []

    # 各資源種別に最適車両を割り当て
    for resource, pickups in sorted(resource_groups.items()):
        vehicle = _select_vehicle_for_resource(resource, pickups, record_map, master)

        if vehicle is None:
            total_demand = _calculate_total_demand(pickups)

            # この資源をサポートする車両を探す
            compatible = [
                record for name, record in record_map.items()
                if _vehicle_supports_resource(name, resource, master)
            ]

            if not compatible:
                warnings.append(
                    f"資源種別 [{resource}] に対応できる車両が見つかりません。"
                )
            else:
                max_capacity = max(
                    int(rec.get("capacity_kg", 0) or 0) for rec in compatible
                )
                shortage = max(0, total_demand - max_capacity)
                warnings.append(
                    f"資源種別 [{resource}] の総重量 {total_demand}kg を運搬できる車両が見つかりません。"
                )
                warnings.append(f"💡 最大容量: {max_capacity}kg（不足: {shortage}kg）")
            continue

        plan.append({
            "vehicle": str(vehicle.get("name", "")),
            "record": vehicle,
            "resources": [resource],
            "pickups": pickups,
        })

    if not plan and not warnings:
        warnings.append("車両の割り当てができませんでした。")

    if warnings:
        warnings.append("💡 ヒント: 車種候補の設定またはマスタデータを確認してください。")

    return plan, warnings


def _build_point_registry(graph, depot: str, sink: str, pickups: List[Dict[str, object]]) -> PointRegistry:
    registry = PointRegistry()
    sequence = [depot] + [p["id"] for p in pickups] + [sink]
    seen = set()
    for point_id in sequence:
        if point_id in seen:
            continue
        seen.add(point_id)
        node = graph.nodes[point_id]
        point_type = PointType.PICKUP
        if point_id == depot:
            point_type = PointType.DEPOT
        elif point_id == sink:
            point_type = PointType.SINK
        registry.add_point(
            lat=float(node.get("lat", 0.0)),
            lon=float(node.get("lon", 0.0)),
            point_type=point_type,
            name=str(node.get("name") or point_id),
            point_id=point_id,
            node_id=point_id,
        )
    for pickup in pickups:
        registry.set_pickup_attr(pickup["id"], pickup["qty"], pickup["kind"])
    return registry


def _extract_node_coordinates(graph) -> List[Dict[str, object]]:
    coords: List[Dict[str, object]] = []
    for node_id, data in _iter_nodes(graph):
        lat = data.get("lat")
        lon = data.get("lon")
        if lat is None or lon is None:
            continue
        coords.append(
            {
                "id": node_id,
                "lat": float(lat),
                "lon": float(lon),
                "name": data.get("name") or node_id,
            }
        )
    return coords


def _build_node_lookup(node_coords: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    lookup: Dict[str, Dict[str, object]] = {}
    for entry in node_coords:
        node_id = str(entry.get("id") or entry.get("node_id"))
        if not node_id:
            continue
        lookup[node_id] = entry
    return lookup


def _find_closest_node(node_ids: List[str], target_lat: float, target_lon: float) -> Optional[str]:
    coords_cache: Dict[str, Dict[str, object]] = st.session_state.get("node_coords_cache", {})
    lookup: Optional[Dict[str, Dict[str, object]]] = None
    for entry in coords_cache.values():
        if isinstance(entry, dict) and "lookup" in entry:
            lookup = entry["lookup"]  # type: ignore[assignment]
            break
        if isinstance(entry, list):  # backward compatibility
            lookup = _build_node_lookup(entry)
            break
    if lookup is None:
        return node_ids[0] if node_ids else None

    best_id: Optional[str] = None
    best_distance = float("inf")
    for node_id in node_ids:
        coord = lookup.get(node_id)
        if not coord:
            continue
        lat = coord.get("lat")
        lon = coord.get("lon")
        if lat is None or lon is None:
            continue
        distance = (float(lat) - target_lat) ** 2 + (float(lon) - target_lon) ** 2
        if distance < best_distance:
            best_distance = distance
            best_id = node_id
    return best_id


def _collect_selected_points(
    depot_id: Optional[str],
    sink_id: Optional[str],
    pickup_ids: Sequence[str],
    node_lookup: Dict[str, Dict[str, object]],
) -> List[SelectedPoint]:
    def _build_point(node_id: Optional[str], role: str) -> Optional[SelectedPoint]:
        if not node_id:
            return None
        entry = node_lookup.get(node_id)
        if entry is None:
            st.warning(f"ノード '{node_id}' の座標情報が見つかりません。")
            return None
        lat = entry.get("lat")
        lon = entry.get("lon")
        if lat is None or lon is None:
            st.warning(f"ノード '{node_id}' に緯度経度情報がありません。")
            return None
        label = str(entry.get("name") or node_id)
        return SelectedPoint(node_id=node_id, lat=float(lat), lon=float(lon), role=role, label=label)

    points: List[SelectedPoint] = []
    seen: set[str] = set()

    candidates = [(depot_id, "depot")] + [(pid, "pickup") for pid in pickup_ids] + [(sink_id, "sink")]

    for candidate, role in candidates:
        point = _build_point(candidate, role)
        if point is None:
            continue
        if point.node_id in seen:
            continue
        points.append(point)
        seen.add(point.node_id)
    return points


def _find_selected_point(
    points: Sequence[SelectedPoint],
    node_id: Optional[str],
    role: Optional[str],
) -> Optional[SelectedPoint]:
    if not node_id or not role:
        return None
    for point in points:
        if point.node_id == node_id and point.role == role:
            return point
    return None
def _get_spatial_index(network_key: str, node_coords: List[Dict[str, object]]) -> SpatialIndex:
    cache: Dict[str, SpatialIndex] = st.session_state.get("spatial_index_cache", {})
    index = cache.get(network_key)
    if index is None or index.node_count != len(node_coords):
        index = SpatialIndex.from_iterable(node_coords)
        cache[network_key] = index
        st.session_state["spatial_index_cache"] = cache
    return index


def _iter_nodes(graph):
    if callable(graph.nodes):
        return graph.nodes(data=True)
    return graph.nodes.items()  # type: ignore[attr-defined]


def _render_network_map(
    node_coords: List[Dict[str, object]],
    selected_points: Sequence[SelectedPoint],
    mode: str,
    last_feedback: Optional[SelectedPoint],
):
    try:
        import folium  # type: ignore
        from streamlit_folium import st_folium  # type: ignore
    except ModuleNotFoundError:
        st.info("地図表示にはfoliumとstreamlit-foliumが必要です。")
        return None

    if last_feedback is not None:
        center_lat, center_lon = last_feedback.lat, last_feedback.lon
    elif selected_points:
        center_lat, center_lon = selected_points[0].lat, selected_points[0].lon
    elif node_coords:
        center_lat = float(node_coords[0]["lat"])
        center_lon = float(node_coords[0]["lon"])
    else:
        st.warning("ノードに座標情報がありません。")
        return None

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    mode_role = MODE_TO_ROLE.get(mode)

    for point in selected_points:
        base_color = ROLE_TO_COLOR.get(point.role, "gray")
        radius = 6 if point.role in {"depot", "sink"} else 5
        fill_opacity = 0.9
        border_color = base_color
        border_weight = 2

        if point.role == mode_role:
            radius += 1
            fill_opacity = 1.0

        if last_feedback and point.node_id == last_feedback.node_id and point.role == last_feedback.role:
            border_color = "#FFD54F"
            border_weight = 3
            radius += 2

        folium.CircleMarker(
            location=[point.lat, point.lon],
            radius=radius,
            color=border_color,
            weight=border_weight,
            fill=True,
            fill_color=base_color,
            fill_opacity=fill_opacity,
            popup=point.label,
        ).add_to(fmap)

    st.write(f"クリックモード: **{mode}**")
    st.caption("凡例: 緑=車庫 / 青=回収 / 赤=集積 / 黄色枠=最新の更新")
    return st_folium(
        fmap,
        width=700,
        height=520,
        key="network_map",
        returned_objects=["last_clicked"],
    )


def _render_pickup_dialog(master: Optional[ProcessedMasterData]) -> None:
    if not st.session_state.get("pickup_dialog_open"):
        return

    pending = st.session_state.get("pending_pickup")
    if not isinstance(pending, dict) or not pending.get("node_id"):
        _clear_pending_pickup()
        return

    node_id = str(pending.get("node_id"))
    label = str(pending.get("label") or node_id)

    st.session_state["pickup_dialog_rendered"] = True

    resource_names = sorted(master.resources.keys()) if master and master.resources else []
    defaults = st.session_state.get("pending_pickup_defaults", {})
    default_qty = int(defaults.get("qty", 100)) if isinstance(defaults, dict) else 100
    default_resource = ""
    if isinstance(defaults, dict):
        default_resource = str(defaults.get("resource") or "")
    if not default_resource and resource_names:
        default_resource = resource_names[0]

    def _dialog_body() -> None:
        st.subheader("回収地点の追加")
        st.caption(f"ノード: {label}")

        form_key = f"pickup_dialog_form_{node_id}"
        qty_key = f"pickup_dialog_qty_{node_id}"
        resource_key = f"pickup_dialog_resource_{node_id}"

        with st.form(form_key, clear_on_submit=False):
            # Phase 1完了: シンプルな回収量入力（詳細情報は削除）
            qty = st.number_input(
                "回収量 (kg)",
                min_value=0,
                max_value=100000,
                step=50,
                value=max(0, default_qty),
                key=qty_key,
            )

            # シンプルな資源種別選択
            resource_value = ""
            if resource_names:
                try:
                    index = resource_names.index(default_resource)
                except ValueError:
                    index = 0
                resource_value = st.selectbox(
                    "資源種別",
                    resource_names,
                    index=index,
                    key=resource_key,
                )
            else:
                st.warning("資源マスタが未登録です。先に設定してください。")

            col_add, col_cancel = st.columns(2)
            submit_add = col_add.form_submit_button("追加", use_container_width=True)
            submit_cancel = col_cancel.form_submit_button("キャンセル", use_container_width=True)

        if submit_cancel:
            st.session_state["pickup_dialog_result"] = {
                "status": "cancel",
                "label": label,
                "reason": "cancel_button",
            }
            st.session_state["pickup_dialog_open"] = False
            st.session_state["pickup_dialog_rendered"] = False
            _toast("回収地点の追加をキャンセルしました。", icon="ℹ️")
            st.rerun()

        if submit_add:
            if qty <= 0:
                st.warning("量は1以上を指定してください。")
                return
            if not resource_names:
                st.warning("資源種別を追加できません。資源マスタを確認してください。")
                return
            resource = str(resource_value or default_resource or resource_names[0])
            st.session_state["pending_pickup_defaults"] = {"qty": int(qty), "resource": resource}
            st.session_state["pickup_dialog_result"] = {
                "status": "add",
                "node_id": node_id,
                "qty": int(qty),
                "resource": resource,
                "label": label,
            }
            st.session_state["pickup_dialog_open"] = False
            st.session_state["pickup_dialog_rendered"] = False
            st.rerun()

    dialog_factory = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    if callable(dialog_factory):
        dialog_decorator = dialog_factory("回収地点の設定")

        if callable(dialog_decorator):

            @dialog_decorator
            def _dialog_wrapper() -> None:
                _dialog_body()

            _dialog_wrapper()
        else:
            placeholder = st.empty()

            def _render_inline():
                with placeholder.container():
                    _dialog_body()

            _render_inline()
    else:
        placeholder = st.empty()

        def _render_inline():
            with placeholder.container():
                _dialog_body()

        _render_inline()


def _get_vehicle_metadata(vehicle_name: str) -> Optional[VehicleCandidate]:
    """
    車両名からVehicleCandidateを取得する。

    Args:
        vehicle_name: 車両名

    Returns:
        VehicleCandidate または None（見つからない場合）
    """
    processed_master = st.session_state.get("processed_master")
    if not processed_master or not processed_master.vehicles:
        return None

    for candidate in processed_master.vehicles:
        if candidate.name == vehicle_name:
            return candidate

    return None


def _display_variable_cost_table(
    cost_breakdown: Dict[str, float],
    vehicle_name: str,
    distance_km: float
) -> None:
    """変動費詳細テーブルを表示"""
    st.markdown(f"**車両**: {vehicle_name} | **走行距離**: {distance_km:.2f} km")

    # 変動費項目の抽出
    variable_items = [
        (k.replace("変動費_", ""), v)
        for k, v in cost_breakdown.items()
        if k.startswith("変動費_")
    ]

    if not variable_items:
        st.info("変動費の詳細データがありません")
        return

    # テーブル作成
    rows = []
    for item_name, cost in variable_items:
        # 単価を逆算
        unit_cost = cost / distance_km if distance_km > 0 else 0
        rows.append({
            "費用項目": item_name,
            "単価 (円/km)": f"{unit_cost:.2f}",
            "走行距離 (km)": f"{distance_km:.2f}",
            "金額 (円)": f"{int(cost):,}"
        })

    # DataFrameで表示
    if pd is not None:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:  # pragma: no cover
        st.write(rows)

    # 合計表示
    total_variable = cost_breakdown.get("distance_cost", 0)
    st.metric("変動費合計", f"{int(total_variable):,} 円")


def _display_fixed_cost_table(
    cost_breakdown: Dict[str, float],
    vehicle_name: str,
    distance_km: float
) -> None:
    """固定費詳細テーブルを表示"""
    st.markdown(f"**車両**: {vehicle_name} | **走行距離**: {distance_km:.2f} km")

    # 固定費項目の抽出
    fixed_items = [
        (k.replace("固定費_", ""), v)
        for k, v in cost_breakdown.items()
        if k.startswith("固定費_")
    ]

    if not fixed_items:
        st.info("固定費の詳細データがありません")
        return

    # テーブル作成
    rows = []
    for item_name, cost in fixed_items:
        # km単価を逆算
        per_km = cost / distance_km if distance_km > 0 else 0
        rows.append({
            "費用項目": item_name,
            "km単価 (円/km)": f"{per_km:.2f}",
            "走行距離 (km)": f"{distance_km:.2f}",
            "金額 (円)": f"{int(cost):,}"
        })

    # DataFrameで表示
    if pd is not None:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:  # pragma: no cover
        st.write(rows)

    # 合計表示
    total_fixed = cost_breakdown.get("fixed_cost", 0)
    st.metric("固定費合計", f"{int(total_fixed):,} 円")


def _display_cost_formula(cost_breakdown: Dict[str, float]) -> None:
    """計算式と計算結果を表示"""
    st.markdown("#### 📐 コスト計算式")

    # LaTeX形式で数式表示
    st.latex(r"\text{総コスト} = \text{変動費} + \text{固定費}")

    st.markdown("**変動費の計算**:")
    st.latex(r"\text{変動費} = \sum_{i} (\text{単価}_i \times \text{走行距離})")

    st.markdown("**固定費の計算**:")
    st.latex(r"\text{固定費} = \sum_{i} \left(\frac{\text{年間費用}_i}{\text{年間走行距離}} \times \text{走行距離}\right)")

    st.markdown("---")
    st.markdown("#### 💵 計算結果")

    # 計算結果の表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "変動費",
            f"{int(cost_breakdown.get('distance_cost', 0)):,} 円"
        )
    with col2:
        st.metric(
            "固定費",
            f"{int(cost_breakdown.get('fixed_cost', 0)):,} 円"
        )
    with col3:
        st.metric(
            "総コスト",
            f"{int(cost_breakdown.get('total_cost', 0)):,} 円",
            delta=None,
            delta_color="off"
        )


def _display_detailed_cost_breakdown(
    cost_breakdown: Dict[str, float],
    vehicle_name: str
) -> None:
    """
    詳細なコスト内訳を表示する。

    Args:
        cost_breakdown: 詳細内訳を含むコスト辞書
        vehicle_name: 車両名（タイトル表示用）
    """
    st.markdown("### 💰 コスト詳細内訳")

    # 詳細データの有無をチェック
    has_variable_details = any(k.startswith("変動費_") for k in cost_breakdown.keys())
    has_fixed_details = any(k.startswith("固定費_") for k in cost_breakdown.keys())

    if not has_variable_details and not has_fixed_details:
        st.info("💡 詳細内訳データがありません（基本表示モード）")
        return

    distance_km = cost_breakdown.get("distance_km", 0.0)

    # 垂直レイアウトで表示
    _display_variable_cost_table(cost_breakdown, vehicle_name, distance_km)
    st.markdown("---")
    _display_fixed_cost_table(cost_breakdown, vehicle_name, distance_km)
    st.markdown("---")
    _display_cost_formula(cost_breakdown)


def _display_single_solution(
    graph, solution: Solution, show_banner: bool = True, label_prefix: str = "", show_vehicle_info: bool = True
) -> None:
    if show_banner:
        st.success("最適化が完了しました。")
    metric_prefix = f"{label_prefix}" if label_prefix else ""
    st.metric(f"{metric_prefix}総距離 [km]", f"{solution.total_distance_m / 1000:.2f}")
    st.metric(f"{metric_prefix}総コスト [円]", f"{solution.cost_breakdown.get('total_cost', 0):,.0f}")
    # エネルギー消費量の表示
    energy_kwh = solution.cost_breakdown.get('energy_consumption_kwh')
    if energy_kwh is not None and energy_kwh > 0:
        st.metric(f"{metric_prefix}エネルギー消費量 [kWh]", f"{energy_kwh:.3f}")
    if show_vehicle_info:
        st.write("採用車種:", solution.vehicle.name)
    st.write("ルート順:", " → ".join(solution.order))

    breakdown_rows = [
        {"項目": "固定費", "金額": solution.cost_breakdown.get("fixed_cost", 0.0)},
        {"項目": "距離費", "金額": solution.cost_breakdown.get("distance_cost", 0.0)},
        {"項目": "総額", "金額": solution.cost_breakdown.get("total_cost", 0.0)},
    ]
    if pd is not None:
        st.table(pd.DataFrame(breakdown_rows))
    else:  # pragma: no cover
        st.write(breakdown_rows)

    # 詳細コスト内訳の表示
    _display_detailed_cost_breakdown(solution.cost_breakdown, solution.vehicle.name)

    try:
        import folium  # type: ignore
        from streamlit_folium import st_folium  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        st.info("地図表示にはfoliumとstreamlit-foliumが必要です。")
        return

    polylines = reconstruct_paths(graph, solution.order)
    flat_coords = [coord for segment in polylines for coord in segment]
    if flat_coords:
        center = flat_coords[0]
    else:
        start_node = graph.nodes[solution.order[0]]
        center = (float(start_node.get("lat", 0.0)), float(start_node.get("lon", 0.0)))

    fmap = folium.Map(location=center, zoom_start=12)

    total_points = len(solution.order)
    for idx, point_id in enumerate(solution.order, start=1):
        node = graph.nodes[point_id]
        lat = float(node.get("lat", 0.0))
        lon = float(node.get("lon", 0.0))
        if idx == 1:
            circle_color = "#2e7d32"
        elif idx == total_points:
            circle_color = "#c62828"
        else:
            circle_color = "#1565c0"

        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color=circle_color,
            weight=3,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.85,
            popup=f"{idx}. {point_id}",
        ).add_to(fmap)

        if idx == 1:
            icon_anchor = (10, 20)
        elif idx == total_points:
            icon_anchor = (10, 0)
        else:
            icon_anchor = (10, 10)

        badge_html = (
            f"<div style=\"display:flex;align-items:center;justify-content:center;width:20px;height:20px;"
            f"border-radius:50%;background-color:{circle_color};color:#ffffff;font-size:12px;font-weight:bold;\">"
            f"{idx}</div>"
        )

        folium.map.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                icon_size=(20, 20),
                icon_anchor=icon_anchor,
                html=badge_html,
            ),
        ).add_to(fmap)

    for segment in polylines:
        if segment:
            folium.PolyLine(segment, color="blue", weight=4, opacity=0.8).add_to(fmap)

    st_folium(fmap, width=700, height=500)
    if total_points:
        st.caption("凡例: 1番目=出発, 最終番号=終点, 青=経路中間")


def _display_fleet_solution(
    graph,
    fleet_solution: FleetSolution,
    plan_summary: Optional[Sequence[Dict[str, object]]] = None,
) -> None:
    st.success("複数車両で最適化が完了しました。")
    st.metric("総距離 [km]", f"{fleet_solution.total_distance_m / 1000:.2f}")
    st.metric("総コスト [円]", f"{fleet_solution.cost_breakdown.get('total_cost', 0):,.0f}")
    # エネルギー消費量の表示
    total_energy_kwh = fleet_solution.cost_breakdown.get('energy_consumption_kwh')
    if total_energy_kwh is not None and total_energy_kwh > 0:
        st.metric("総エネルギー消費量 [kWh]", f"{total_energy_kwh:.3f}")

    breakdown_rows = [
        {"項目": "固定費", "金額": fleet_solution.cost_breakdown.get("fixed_cost", 0.0)},
        {"項目": "距離費", "金額": fleet_solution.cost_breakdown.get("distance_cost", 0.0)},
        {"項目": "総額", "金額": fleet_solution.cost_breakdown.get("total_cost", 0.0)},
    ]
    if pd is not None:
        st.table(pd.DataFrame(breakdown_rows))
    else:  # pragma: no cover
        st.write(breakdown_rows)

    plan_lookup: Dict[str, Dict[str, object]] = {}
    if plan_summary and isinstance(plan_summary, Sequence):
        plan_lookup = {
            str(entry.get("vehicle")): entry for entry in plan_summary if isinstance(entry, dict)
        }

    for idx, route in enumerate(fleet_solution.routes, start=1):
        entry = plan_lookup.get(route.vehicle.name)
        st.subheader(f"車両 {idx}: {route.vehicle.name}")
        if entry:
            resources = entry.get("resources") or []
            if resources:
                st.caption(f"対応資源: {', '.join(resources)}")
            pickup_ids = entry.get("pickup_ids") or []
            if pickup_ids:
                st.caption(f"対象ノード: {', '.join(str(pid) for pid in pickup_ids)}")
        _display_single_solution(
            graph,
            route.solution,
            show_banner=False,
            label_prefix=f"車両{idx} ",
            show_vehicle_info=False,
        )


def _display_comparison_results(
    graph,
    optimal_solution: FleetSolution,
    ecom10_solution,
    compatibility_result: eCOM10CompatibilityResult,
    plan_summary: Optional[Sequence[Dict[str, object]]] = None,
) -> None:
    """最適解と eCOM-10 代替案を並列表示"""
    st.markdown("## 📊 最適化結果の比較")
    st.markdown("---")

    col1, col2 = st.columns(2)

    # 左カラム: 最適解
    with col1:
        st.markdown("### 🏆 最適解（推奨）")
        st.metric("総距離 (km)", f"{optimal_solution.total_distance_m / 1000:.2f}")
        st.metric("総コスト (円)", f"{optimal_solution.cost_breakdown.get('total_cost', 0):,.0f}")

        energy_kwh = optimal_solution.cost_breakdown.get('energy_consumption_kwh')
        if energy_kwh:
            st.metric("エネルギー消費 (kWh)", f"{energy_kwh:.2f}")

        # 車両構成
        st.markdown("**📋 車両構成:**")
        for idx, route in enumerate(optimal_solution.routes, start=1):
            st.write(f"・{route.vehicle.name}")

    # 右カラム: eCOM-10 代替案
    with col2:
        st.markdown("### 🚐 eCOM-10 利用の場合")

        if isinstance(ecom10_solution, NoSolution):
            # 解なしの場合
            st.error("❌ eCOM-10 による運搬は不可能です")
            st.write(ecom10_solution.message)

            # 非適合資源の詳細表示
            if compatibility_result.incompatible_pickups:
                st.markdown("**以下の資源はeCOM-10では運搬できません:**")
                processed_master = st.session_state.get("processed_master")

                for pickup in compatibility_result.incompatible_pickups:
                    resource_type = pickup.get("kind", "不明")
                    quantity = pickup.get("qty", 0)

                    # 代替車両の提案
                    if processed_master:
                        alternatives = find_alternative_vehicles(
                            resource_type, quantity, processed_master
                        )
                        st.warning(
                            f"**❌ {resource_type}** ({quantity}kg)\n\n"
                            f"代替車両: {', '.join(alternatives)}"
                        )
                    else:
                        st.warning(f"**❌ {resource_type}** ({quantity}kg)")

        else:
            # 解ありの場合
            distance_diff = ecom10_solution.total_distance_m - optimal_solution.total_distance_m
            cost_diff = ecom10_solution.cost_breakdown.get('total_cost', 0) - optimal_solution.cost_breakdown.get('total_cost', 0)

            st.metric(
                "総距離 (km)",
                f"{ecom10_solution.total_distance_m / 1000:.2f}",
                delta=f"{distance_diff / 1000:+.2f} km"
            )

            # コスト差分（削減の場合は緑、増加の場合は赤）
            cost_percent = (cost_diff / optimal_solution.cost_breakdown.get('total_cost', 1) * 100) if optimal_solution.cost_breakdown.get('total_cost', 0) > 0 else 0
            st.metric(
                "総コスト (円)",
                f"{ecom10_solution.cost_breakdown.get('total_cost', 0):,.0f}",
                delta=f"{cost_diff:+,.0f} 円 ({cost_percent:+.1f}%)",
                delta_color="inverse"  # 減少が良い
            )

            # エネルギー差分
            ecom10_energy = ecom10_solution.cost_breakdown.get('energy_consumption_kwh')
            optimal_energy = optimal_solution.cost_breakdown.get('energy_consumption_kwh')

            if ecom10_energy is not None and optimal_energy is not None:
                energy_diff = ecom10_energy - optimal_energy
                energy_percent = (energy_diff / optimal_energy * 100) if optimal_energy > 0 else 0
                st.metric(
                    "エネルギー消費 (kWh)",
                    f"{ecom10_energy:.2f}",
                    delta=f"{energy_diff:+.2f} kWh ({energy_percent:+.1f}%)",
                    delta_color="inverse"
                )

                # CO2 削減効果の表示
                if energy_diff < 0:
                    st.success(f"🌱 CO₂削減効果: {abs(energy_diff):.2f} kWh 相当")

            # 車両構成
            st.markdown("**📋 車両構成:**")
            for idx, route in enumerate(ecom10_solution.routes, start=1):
                st.write(f"・{route.vehicle.name}")

            # 警告・制約情報
            if compatibility_result.warnings:
                st.markdown("**⚠️ 制約事項:**")
                for warning in compatibility_result.warnings:
                    if "💡" in warning:
                        st.info(warning)
                    else:
                        st.warning(warning)

    # 推奨メッセージ
    st.markdown("---")
    if isinstance(ecom10_solution, FleetSolution):
        cost_saving = optimal_solution.cost_breakdown.get('total_cost', 0) - ecom10_solution.cost_breakdown.get('total_cost', 0)
        if cost_saving > 0:
            st.success(
                f"💡 **推奨**: 短距離・軽量資源の場合、eCOM-10 で "
                f"約 {cost_saving:,.0f} 円のコスト削減と CO₂ 削減効果が期待できます"
            )
        else:
            st.info(
                "💡 **推奨**: 最適解の方がコスト面で有利です。"
                "ただし、環境負荷低減を重視する場合は eCOM-10 も検討価値があります"
            )
    else:
        st.info(
            "💡 **代替案**: 軽量資源（林業残材、古紙等）に変更することで "
            "eCOM-10 での運搬が可能になります"
        )

    # 元の詳細表示を追加
    st.markdown("---")
    st.markdown("## 📋 最適化結果の詳細")

    # コスト内訳テーブル
    st.markdown("### 💰 コスト内訳（最適解）")
    breakdown_rows = [
        {"項目": "固定費", "金額": optimal_solution.cost_breakdown.get("fixed_cost", 0.0)},
        {"項目": "距離費", "金額": optimal_solution.cost_breakdown.get("distance_cost", 0.0)},
        {"項目": "総額", "金額": optimal_solution.cost_breakdown.get("total_cost", 0.0)},
    ]
    if pd is not None:
        st.table(pd.DataFrame(breakdown_rows))
    else:
        st.write(breakdown_rows)

    # コスト内訳テーブル（eCOM-10）
    if isinstance(ecom10_solution, FleetSolution):
        st.markdown("### 💰 コスト内訳（eCOM-10）")
        ecom10_breakdown_rows = [
            {"項目": "固定費", "金額": ecom10_solution.cost_breakdown.get("fixed_cost", 0.0)},
            {"項目": "距離費", "金額": ecom10_solution.cost_breakdown.get("distance_cost", 0.0)},
            {"項目": "総額", "金額": ecom10_solution.cost_breakdown.get("total_cost", 0.0)},
        ]
        if pd is not None:
            st.table(pd.DataFrame(ecom10_breakdown_rows))
        else:
            st.write(ecom10_breakdown_rows)

    # 各車両ごとのルート詳細
    st.markdown("### 🚗 各車両のルート詳細")
    plan_lookup: Dict[str, Dict[str, object]] = {}
    if plan_summary and isinstance(plan_summary, Sequence):
        plan_lookup = {
            str(entry.get("vehicle")): entry for entry in plan_summary if isinstance(entry, dict)
        }

    for idx, route in enumerate(optimal_solution.routes, start=1):
        entry = plan_lookup.get(route.vehicle.name)
        st.subheader(f"車両 {idx}: {route.vehicle.name}")
        if entry:
            resources = entry.get("resources") or []
            if resources:
                st.caption(f"対応資源: {', '.join(resources)}")
            pickup_ids = entry.get("pickup_ids") or []
            if pickup_ids:
                st.caption(f"対象ノード: {', '.join(str(pid) for pid in pickup_ids)}")
        _display_single_solution(
            graph,
            route.solution,
            show_banner=False,
            label_prefix=f"車両{idx} ",
            show_vehicle_info=False,
        )


def check_password() -> bool:
    """パスワード認証を行います。正しいパスワードが入力された場合はTrueを返します。"""

    def password_entered():
        """パスワードが入力されたときの処理"""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # パスワードをセッションに保存しない
        else:
            st.session_state["password_correct"] = False

    # 初回アクセス時
    if "password_correct" not in st.session_state:
        st.title("🔐 資源回収ルート最適化ツール")
        st.markdown("---")
        st.text_input(
            "パスワードを入力してください",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False

    # パスワードが間違っている場合
    elif not st.session_state["password_correct"]:
        st.title("🔐 資源回収ルート最適化ツール")
        st.markdown("---")
        st.text_input(
            "パスワードを入力してください",
            type="password",
            on_change=password_entered,
            key="password",
        )
        st.error("😕 パスワードが正しくありません")
        return False

    # パスワードが正しい場合
    else:
        return True


def main() -> None:
    # パスワード認証チェック
    if not check_password():
        st.stop()

    st.title("資源回収ルート最適化ツール")
    processed_master = load_processed_master_cached()
    _init_session_state(processed_master)
    st.session_state["processed_master"] = processed_master
    _detect_abandoned_pickup_dialog()
    _process_pickup_dialog_result()

    network_files = _list_network_files()
    if not network_files:
        st.warning("data/ 配下にネットワークJSONが存在しません。")
        return

    selected_name = st.sidebar.selectbox("道路ネットワークファイル", options=list(network_files.keys()))
    selected_path = network_files[selected_name]
    graph, metadata = load_graph(str(selected_path))

    coords_cache: Dict[str, Dict[str, object]] = st.session_state.get("node_coords_cache", {})
    cache_entry = coords_cache.get(selected_name)
    if isinstance(cache_entry, list):  # backward compatibility with既存セッション
        node_coords = cache_entry
        node_lookup = _build_node_lookup(node_coords)
        cache_entry = {"coords": node_coords, "lookup": node_lookup}
        coords_cache[selected_name] = cache_entry
        st.session_state["node_coords_cache"] = coords_cache
    if cache_entry is None:
        node_coords = _extract_node_coordinates(graph)
        node_lookup = _build_node_lookup(node_coords)
        cache_entry = {"coords": node_coords, "lookup": node_lookup}
        coords_cache[selected_name] = cache_entry
        st.session_state["node_coords_cache"] = coords_cache
    node_coords = cache_entry["coords"]  # type: ignore[index]
    node_lookup = cache_entry["lookup"]  # type: ignore[index]
    node_ids = [str(entry["id"]) for entry in node_coords]

    def edge_count() -> int:
        try:
            return graph.number_of_edges()  # type: ignore[attr-defined]
        except AttributeError:
            return sum(len(neighbours) for neighbours in getattr(graph, "_succ", {}).values())

    st.sidebar.write(f"ノード数: {metadata.get('node_count', len(graph.nodes))}")
    st.sidebar.write(f"エッジ数: {metadata.get('edge_count', edge_count())}")

    # Phase 1-1: 選択状況のサイドバー表示
    st.sidebar.markdown("---")
    st.sidebar.subheader("📍 現在の選択状況")

    # 車庫の状態取得（ここでは初期値のみ、後で更新される）
    depot_id_preview = st.session_state.get("depot_id")
    sink_id_preview = st.session_state.get("sink_id")
    pickup_selection_preview = st.session_state.get("pickup_selection", [])
    vehicles_preview = st.session_state.get("vehicles", [])

    # 車庫
    depot_display = depot_id_preview if depot_id_preview else "未選択"
    depot_status = "✅" if depot_id_preview else "⚠️"
    st.sidebar.markdown(f"{depot_status} **車庫**: {depot_display}")

    # 集積場所
    sink_display = sink_id_preview if sink_id_preview else "未選択"
    sink_status = "✅" if sink_id_preview else "⚠️"
    st.sidebar.markdown(f"{sink_status} **集積場所**: {sink_display}")

    # 回収地点
    pickup_count = len(pickup_selection_preview)
    pickup_status = "✅" if pickup_count > 0 else "⚠️"
    st.sidebar.markdown(f"{pickup_status} **回収地点**: {pickup_count}箇所")

    # 車種
    vehicle_count = len([v for v in vehicles_preview if v.get("name")])
    vehicle_status = "✅" if vehicle_count > 0 else "⚠️"
    st.sidebar.markdown(f"{vehicle_status} **車種候補**: {vehicle_count}種類")

    if not node_ids:
        st.error("ノードが存在しません。")
        return

    _ensure_selection_defaults(node_ids)

    # ========================================
    # セクション1: 地点選択
    # ========================================
    st.markdown("## 📍 地点選択")
    st.markdown("地図をクリックして、車庫・回収地点・集積場所を選択してください。")

    mode = st.radio("地図クリックモード", ("車庫", "回収地点", "集積場所"), index=1, horizontal=True)

    # Phase 1-2: クリックモードの説明追加
    mode_help = {
        "車庫": "🏠 **車両の出発・帰着地点**を選択してください。地図上でクリックすると最寄りのノードが車庫に設定されます。",
        "回収地点": "📦 **資源を回収する地点**を選択してください。クリック後、資源種別と回収量を入力します。",
        "集積場所": "🏭 **回収した資源を集める場所**を選択してください。回収後、必ずこの地点を経由します。"
    }
    st.info(mode_help[mode])

    depot_id = st.session_state.get("depot_id")
    sink_id = st.session_state.get("sink_id")
    pickup_selection: List[str] = st.session_state.get("pickup_selection", [])

    selected_points = _collect_selected_points(depot_id, sink_id, pickup_selection, node_lookup)
    last_feedback = _find_selected_point(
        selected_points,
        st.session_state.get("last_selected_node"),
        st.session_state.get("last_selected_role"),
    )

    focus_token = st.session_state.get("map_focus_token")
    if isinstance(focus_token, dict):
        focus_point = _find_selected_point(
            selected_points,
            focus_token.get("node_id"),
            focus_token.get("role"),
        )
        if focus_point:
            last_feedback = focus_point
        st.session_state["map_focus_token"] = None

    spatial_index = _get_spatial_index(selected_name, node_coords)

    # Phase 1-3: 地図凡例の強化
    st.markdown("---")
    st.subheader("🗺️ 地点選択マップ")

    # 凡例を目立つ形で表示
    cols = st.columns(4)
    cols[0].markdown("🟢 **車庫** (出発/帰着)")
    cols[1].markdown("🔵 **回収地点**")
    cols[2].markdown("🔴 **集積場所**")
    cols[3].markdown("🟡 **最新選択**")

    st.caption("💡 地図をクリックして地点を選択できます。現在のモードに応じて地点が設定されます。")

    _render_map_feedback()

    map_state = _render_network_map(node_coords, selected_points, mode, last_feedback)

    if map_state and map_state.get("last_clicked"):
        lat = map_state["last_clicked"].get("lat")
        lon = map_state["last_clicked"].get("lng")
        if lat is not None and lon is not None:
            click_token = (round(float(lat), 6), round(float(lon), 6), mode)
            if st.session_state.get("last_click_token") != click_token:
                st.session_state["last_click_token"] = click_token
                result = spatial_index.nearest(float(lat), float(lon))
                nearest = result.node_id
                if nearest is not None:
                    if mode == "車庫":
                        st.session_state["depot_id"] = nearest
                        _set_last_selection(nearest, "depot")
                    elif mode == "集積場所":
                        st.session_state["sink_id"] = nearest
                        _set_last_selection(nearest, "sink")
                    else:
                        if st.session_state.get("pickup_dialog_open"):
                            _toast("前の回収地点の入力を完了してください。", icon="⚠️")
                        else:
                            pickups = st.session_state.get("pickup_selection", [])
                            if nearest in {st.session_state["depot_id"], st.session_state["sink_id"]}:
                                _toast("車庫または集積地点と同じノードは回収地点に追加できません。", icon="⚠️")
                            elif nearest in pickups:
                                _toast("既に追加済みの回収地点です。", icon="ℹ️")
                            else:
                                entry = node_lookup.get(nearest, {})
                                st.session_state["pending_pickup"] = {
                                    "node_id": nearest,
                                    "label": entry.get("name") or nearest,
                                    "lat": entry.get("lat"),
                                    "lon": entry.get("lon"),
                                }
                                st.session_state["pending_pickup_defaults"] = _prepare_pending_defaults(nearest, processed_master)
                                st.session_state["pickup_dialog_open"] = True
                                st.session_state["pickup_dialog_rendered"] = False
                                _toast(f"資源種別と量を入力: {nearest}", icon="📝")
                                _set_last_selection(None, None)

    # Pickup dialog for new points
    st.session_state["pickup_dialog_rendered"] = False
    _render_pickup_dialog(processed_master)
    if (
        st.session_state.get("pickup_dialog_open")
        and not st.session_state.get("pickup_dialog_rendered")
        and st.session_state.get("pickup_dialog_result") is None
    ):
        pending = st.session_state.get("pending_pickup")
        if isinstance(pending, dict) and pending.get("node_id"):
            label = str(pending.get("label") or pending.get("node_id"))
            st.session_state["pickup_dialog_result"] = {
                "status": "cancel",
                "label": label,
                "reason": "closed",
            }
            _process_pickup_dialog_result()
            _render_map_feedback()

    # Phase 2-5: 回収地点一覧の改善
    pickup_selection = st.session_state.get("pickup_selection", [])
    if pickup_selection:
        st.markdown("---")
        st.subheader("📦 選択済み回収地点")

        # 各地点をカード形式で表示
        for idx, point_id in enumerate(pickup_selection, start=1):
            attrs = st.session_state.get("pickup_attrs", {}).get(point_id, {})
            qty = attrs.get("qty", 0)
            resource = attrs.get("resource") or attrs.get("kind", "未設定")

            # エクスパンダーで展開可能
            with st.expander(f"#{idx} {point_id} - {resource} {qty}kg", expanded=False):
                col1, col2, col3 = st.columns([3, 3, 1])

                # Phase 2完了: シンプルな資源種別と回収量の編集
                resource_names = sorted(processed_master.resources.keys()) if processed_master and processed_master.resources else []
                if resource_names:
                    try:
                        default_index = resource_names.index(resource)
                    except ValueError:
                        default_index = 0
                    new_resource = col1.selectbox(
                        "資源種別",
                        resource_names,
                        index=default_index,
                        key=f"edit_resource_{point_id}"
                    )
                else:
                    new_resource = col1.text_input("資源種別", value=resource, key=f"edit_resource_{point_id}")

                new_qty = col2.number_input(
                    "回収量 (kg)",
                    min_value=0,
                    max_value=100000,
                    value=int(qty),
                    step=50,
                    key=f"edit_qty_{point_id}",
                )

                # 更新ボタン
                if col1.button("更新", key=f"update_{point_id}"):
                    attrs_dict = st.session_state.get("pickup_attrs", {})
                    attrs_dict[point_id] = {"qty": int(new_qty), "kind": new_resource, "resource": new_resource}
                    st.session_state["pickup_attrs"] = attrs_dict
                    st.success(f"✅ {point_id} を更新しました")
                    st.rerun()

                # 削除ボタン
                if col3.button("🗑️", key=f"delete_{point_id}", help="この地点を削除"):
                    pickups = st.session_state.get("pickup_selection", [])
                    if point_id in pickups:
                        pickups.remove(point_id)
                        st.session_state["pickup_selection"] = pickups
                    attrs_dict = st.session_state.get("pickup_attrs", {})
                    if point_id in attrs_dict:
                        attrs_dict.pop(point_id)
                        st.session_state["pickup_attrs"] = attrs_dict
                    st.success(f"🗑️ {point_id} を削除しました")
                    st.rerun()

        # 一括削除ボタン
        if st.button("🗑️ すべての回収地点をクリア", key="pickup_clear_all"):
            st.session_state["pickup_selection"] = []
            st.session_state["pickup_attrs"] = {}
            _clear_pending_pickup()
            st.success("🗑️ すべての回収地点を削除しました")
            if st.session_state.get("last_selected_role") == "pickup":
                _set_last_selection(None, None)
            st.rerun()

    # ========================================
    # セクション2: 最適化実行
    # ========================================
    st.markdown("## ⚡ 最適化実行")

    # Phase 3, 4完了: 選択状況表示とノード手動選択を削除（地図クリックのみで選択）
    depot_id = st.session_state.get("depot_id")
    sink_id = st.session_state.get("sink_id")
    pickup_selection = st.session_state.get("pickup_selection", [])

    # 車種割当プラン生成（内部で自動実行）
    pickup_inputs = []
    if pickup_selection:
        pickup_inputs = _collect_pickup_inputs(pickup_selection, processed_master)

    vehicle_plan, plan_warnings = _plan_vehicle_allocations(
        st.session_state["vehicles"],
        processed_master,
        pickup_inputs,
    )
    st.session_state["vehicle_filter_warnings"] = list(dict.fromkeys(plan_warnings))
    st.session_state["fleet_plan"] = vehicle_plan
    catalog = _build_vehicle_catalog(st.session_state["vehicles"])
    vehicles_defined = catalog.list_vehicles()

    # 車種割当警告の表示
    if plan_warnings:
        st.markdown("---")
        st.subheader("⚠️ 車種割当の警告")
        for warning in plan_warnings:
            st.warning(warning, icon="⚠️")
        st.info("💡 警告を解消してから最適化を実行することを推奨します。")

    # Phase 1-5: 実行前チェックリストの追加
    st.markdown("---")
    st.subheader("✅ 実行前チェック")

    # チェック項目の定義
    checks = {
        "車庫が設定されている": depot_id is not None,
        "集積場所が設定されている": sink_id is not None,
        "車庫と集積場所が異なる": depot_id != sink_id if (depot_id and sink_id) else False,
        "回収地点が1箇所以上ある": len(pickup_selection) > 0,
        "全回収地点に資源種別が設定されている": all(
            pickup_id in st.session_state.get("pickup_attrs", {})
            for pickup_id in pickup_selection
        ) if pickup_selection else False,
        "車種が1種類以上設定されている": len(vehicles_defined) > 0,
        "車種割当プランが作成されている": len(vehicle_plan) > 0,
        "車種割当に警告がない": len(st.session_state.get("vehicle_filter_warnings", [])) == 0,
    }

    # チェック結果の表示
    all_passed = True
    for check_name, passed in checks.items():
        icon = "✅" if passed else "❌"
        st.markdown(f"{icon} {check_name}")
        if not passed:
            all_passed = False

    # 実行可否の判定表示
    if all_passed:
        st.success("🎉 すべての条件を満たしています。最適化を実行できます。")
    else:
        st.error("⚠️ 上記の条件を満たしてから実行してください。")

    st.markdown("---")

    if st.button("最適化を実行", type="primary", disabled=not all_passed):
        # Phase 3-4: プログレス表示の追加
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            if depot_id == sink_id:
                st.error("車庫と集積場所は異なるノードを選択してください。")
                return
            if not vehicles_defined:
                st.error("少なくとも1種類の車種を定義してください。")
                return
            if not vehicle_plan:
                st.error("資源に対応する車種割当を作成できませんでした。車種設定を見直してください。")
                return

            unique_nodes: List[str] = []
            for node_id in [depot_id] + pickup_selection + [sink_id]:
                if node_id not in unique_nodes:
                    unique_nodes.append(node_id)

            # ステップ1: 距離行列計算
            status_text.text("📊 距離行列を計算中...")
            progress_bar.progress(25)

            with st.spinner("距離行列を計算中..."):
                distance_matrix = cached_distance_matrix(str(selected_path), tuple(unique_nodes))

            # ステップ2: 車種割当準備
            status_text.text("🚗 車種割当を準備中...")
            progress_bar.progress(50)

            assignments: List[Tuple["VehicleType", List[Dict[str, object]]]] = []
            plan_summary: List[Dict[str, object]] = []
            for entry in vehicle_plan:
                vehicle_type = _make_vehicle_type(entry.get("record", {}))
                pickups_for_vehicle = [
                    {"id": item["id"], "demand": int(item.get("qty", 0))}
                    for item in entry.get("pickups", [])
                    if item.get("id") is not None
                ]
                if not pickups_for_vehicle:
                    continue
                assignments.append((vehicle_type, pickups_for_vehicle))
                plan_summary.append(
                    {
                        "vehicle": vehicle_type.name,
                        "resources": entry.get("resources", []),
                        "pickup_ids": [str(item["id"]) for item in entry.get("pickups", [])],
                    }
                )

            if not assignments:
                st.error("割り当て可能な回収地点がありません。入力内容を確認してください。")
                return

            # ステップ3: 最適化実行
            status_text.text("⚡ 最適化を実行中...")
            progress_bar.progress(75)

            # vehicle_metadata_mapの作成
            vehicle_metadata_map: Dict[str, VehicleCandidate] = {}
            processed_master = st.session_state.get("processed_master")
            if processed_master and processed_master.vehicles:
                for candidate in processed_master.vehicles:
                    vehicle_metadata_map[candidate.name] = candidate

            with st.spinner("最適化を実行中..."):
                result = solve_fleet_routing(distance_matrix, depot_id, sink_id, assignments, vehicle_metadata_map)

            # eCOM-10 代替案の計算
            ecom10_result = None
            ecom10_compatibility = None
            if isinstance(result, FleetSolution) and processed_master:
                with st.spinner("eCOM-10 代替案を計算中..."):
                    # eCOM-10 車両を取得
                    ecom10_vehicle = None
                    other_vehicles = []

                    for candidate in processed_master.vehicles:
                        if candidate.name == "eCOM-10":
                            # VehicleType を作成
                            from services.vehicle_catalog import VehicleType
                            ecom10_vehicle = VehicleType(
                                name=candidate.name,
                                capacity_kg=candidate.capacity_kg,
                                fixed_cost=candidate.annual_fixed_cost / candidate.annual_distance_km if candidate.annual_distance_km > 0 else 0,
                                per_km_cost=candidate.variable_cost_per_km,
                            )
                        else:
                            from services.vehicle_catalog import VehicleType
                            other_vehicles.append(
                                VehicleType(
                                    name=candidate.name,
                                    capacity_kg=candidate.capacity_kg,
                                    fixed_cost=candidate.annual_fixed_cost / candidate.annual_distance_km if candidate.annual_distance_km > 0 else 0,
                                    per_km_cost=candidate.variable_cost_per_km,
                                )
                            )

                    if ecom10_vehicle and other_vehicles:
                        ecom10_result, ecom10_compatibility = compute_ecom10_alternative(
                            distance_matrix=distance_matrix,
                            depot=depot_id,
                            sink=sink_id,
                            pickup_inputs=pickup_inputs,
                            ecom10_vehicle=ecom10_vehicle,
                            other_vehicles=other_vehicles,
                            master=processed_master,
                            vehicle_metadata_map=vehicle_metadata_map,
                        )

            # ステップ4: 完了
            progress_bar.progress(100)
            status_text.text("✅ 完了しました！")

            if isinstance(result, NoSolution):
                st.error(f"解が見つかりません: {result.message}")
                st.session_state.pop("latest_solution", None)
            else:
                registry = _build_point_registry(graph, depot_id, sink_id, pickup_inputs)
                st.session_state["latest_solution"] = {
                    "solution": result,
                    "points": [asdict(point) for point in registry.list_points()],
                    "plan": plan_summary,
                    "ecom10_solution": ecom10_result,
                    "ecom10_compatibility": ecom10_compatibility,
                }

        finally:
            # プログレスバーをクリア
            import time
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()

    # 実行結果の表示
    stored_solution = st.session_state.get("latest_solution")
    if stored_solution:
        solution_obj = stored_solution.get("solution")
        plan_summary = stored_solution.get("plan")
        ecom10_solution = stored_solution.get("ecom10_solution")
        ecom10_compatibility = stored_solution.get("ecom10_compatibility")

        if isinstance(solution_obj, FleetSolution):
            # eCOM-10 比較結果がある場合は比較表示
            if ecom10_solution is not None and ecom10_compatibility is not None:
                _display_comparison_results(
                    graph,
                    solution_obj,
                    ecom10_solution,
                    ecom10_compatibility,
                    plan_summary
                )
            else:
                # 通常の表示
                _display_fleet_solution(graph, solution_obj, plan_summary)
        elif isinstance(solution_obj, Solution):
            _display_single_solution(graph, solution_obj)


if __name__ == "__main__":  # pragma: no cover
    main()
