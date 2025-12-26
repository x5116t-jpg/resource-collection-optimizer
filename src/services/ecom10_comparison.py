"""
eCOM-10代替案計算モジュール

eCOM-10（低速電動コミュニティバス）を使用した資源回収の代替案を計算し、
現行の最適化結果と比較するための機能を提供します。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union
from dataclasses import dataclass

from .optimizer import (
    Solution,
    NoSolution,
    FleetSolution,
    VehicleRoute,
    NoSolutionReason,
    PickupInput,
    solve_fleet_routing,
)
from .distance_matrix import DistanceMatrix
from .vehicle_catalog import VehicleType
from .master_repository import ProcessedMasterData, VehicleCandidate


# eCOM-10の制約定数
ECOM10_MAX_CAPACITY_KG = 1000  # 最大積載量
ECOM10_MAX_RANGE_M = 30000  # 航続距離 30km = 30,000m
ECOM10_MAX_SPEED_KMH = 19  # 最高速度
ECOM10_ENERGY_CONSUMPTION_KWH_PER_KM = 0.5  # エネルギー消費


@dataclass(frozen=True)
class eCOM10CompatibilityResult:
    """eCOM-10互換性チェック結果"""
    compatible_pickups: List[Dict[str, object]]
    incompatible_pickups: List[Dict[str, object]]
    warnings: List[str]
    total_compatible_weight: int


def check_ecom10_compatibility(
    pickup_inputs: Sequence[PickupInput],
    master: Optional[ProcessedMasterData],
) -> eCOM10CompatibilityResult:
    """
    資源の eCOM-10 互換性をチェック

    Args:
        pickup_inputs: 回収地点情報
        master: マスタデータ

    Returns:
        eCOM10CompatibilityResult: 互換性チェック結果
    """
    compatible_pickups: List[Dict[str, object]] = []
    incompatible_pickups: List[Dict[str, object]] = []
    warnings: List[str] = []
    total_compatible_weight = 0

    # マスタデータから eCOM-10 の互換性情報を取得
    ecom10_compatibility = None
    if master and master.compatibility:
        ecom10_compatibility = master.compatibility.get("eCOM-10")

    for pickup in pickup_inputs:
        resource_type = str(pickup.get("kind", ""))
        quantity = int(pickup.get("qty", 0))
        pickup_id = pickup.get("id", "不明")

        if not resource_type:
            warnings.append(f"⚠️ 回収地点 {pickup_id} に資源種別が設定されていません")
            incompatible_pickups.append(pickup)
            continue

        # 互換性チェック
        is_compatible = False
        incompatible_reason = "互換性情報なし"

        if ecom10_compatibility:
            support_status = ecom10_compatibility.supports.get(resource_type)

            if support_status is True:
                is_compatible = True
            elif support_status is False:
                is_compatible = False
                # 非適合理由を取得
                reason = ecom10_compatibility.requirements.get(resource_type)
                if reason:
                    incompatible_reason = reason
                else:
                    incompatible_reason = "車両構造上不適合"

        # 判定結果に基づいて分類
        if is_compatible:
            compatible_pickups.append(pickup)
            total_compatible_weight += quantity
        else:
            incompatible_pickups.append(pickup)
            warnings.append(
                f"❌ **{resource_type}** ({quantity}kg) は eCOM-10 では運搬できません\n"
                f"   理由: {incompatible_reason}"
            )

    return eCOM10CompatibilityResult(
        compatible_pickups=compatible_pickups,
        incompatible_pickups=incompatible_pickups,
        warnings=warnings,
        total_compatible_weight=total_compatible_weight,
    )


def validate_ecom10_constraints(
    total_weight_kg: int,
    total_distance_m: float,
) -> Tuple[bool, List[str]]:
    """
    eCOM-10 の制約（容量・航続距離）を検証

    Args:
        total_weight_kg: 総重量 (kg)
        total_distance_m: 総走行距離 (m)

    Returns:
        (is_valid, warnings): 制約を満たすか、警告メッセージリスト
    """
    is_valid = True
    warnings: List[str] = []

    # 容量制約チェック
    if total_weight_kg > ECOM10_MAX_CAPACITY_KG:
        is_valid = False
        excess_weight = total_weight_kg - ECOM10_MAX_CAPACITY_KG
        warnings.append(
            f"⚠️ 総重量 {total_weight_kg}kg が eCOM-10 の最大積載量 ({ECOM10_MAX_CAPACITY_KG}kg) を超過しています\n"
            f"   超過量: {excess_weight}kg\n"
            f"   対策: 複数台に分割または他車両を使用"
        )

    # 航続距離制約チェック
    if total_distance_m > ECOM10_MAX_RANGE_M:
        is_valid = False
        excess_distance_km = (total_distance_m - ECOM10_MAX_RANGE_M) / 1000.0
        warnings.append(
            f"⚠️ 総走行距離 {total_distance_m / 1000.0:.1f}km が eCOM-10 の航続距離 (30km) を超過しています\n"
            f"   超過距離: {excess_distance_km:.1f}km\n"
            f"   対策: より近い拠点を利用または他車両を使用"
        )

    # 所要時間の情報提供（警告ではなく情報）
    if total_distance_m > 0:
        time_hours = (total_distance_m / 1000.0) / ECOM10_MAX_SPEED_KMH
        hours = int(time_hours)
        minutes = int((time_hours - hours) * 60)
        warnings.append(
            f"💡 eCOM-10 の所要時間: 約{hours}時間{minutes}分\n"
            f"   (最高速度 {ECOM10_MAX_SPEED_KMH}km/h のため)"
        )

    return is_valid, warnings


def compute_ecom10_alternative(
    distance_matrix: DistanceMatrix,
    depot: str,
    sink: str,
    pickup_inputs: Sequence[PickupInput],
    ecom10_vehicle: VehicleType,
    other_vehicles: Sequence[VehicleType],
    master: Optional[ProcessedMasterData] = None,
    vehicle_metadata_map: Optional[Dict[str, VehicleCandidate]] = None,
) -> Tuple[Union[FleetSolution, NoSolution], eCOM10CompatibilityResult]:
    """
    eCOM-10 を使用した代替案を計算

    処理フロー:
    1. 資源種別ごとに eCOM-10 互換性チェック
    2. 互換資源 → eCOM-10 に割り当て
    3. 非互換資源 → 他車両に割り当て
    4. 容量・航続距離制約チェック
    5. ルート最適化実行
    6. FleetSolution を返却

    Args:
        distance_matrix: 距離行列
        depot: 車庫ノードID
        sink: 集積場所ノードID
        pickup_inputs: 回収地点情報
        ecom10_vehicle: eCOM-10 車両タイプ
        other_vehicles: 代替車両候補リスト
        master: マスタデータ
        vehicle_metadata_map: 車両メタデータマップ

    Returns:
        (solution, compatibility_result): 代替案または解なし、互換性チェック結果
    """
    # 1. 互換性チェック
    compatibility_result = check_ecom10_compatibility(pickup_inputs, master)

    # すべて非互換の場合
    if not compatibility_result.compatible_pickups:
        no_solution = NoSolution(
            NoSolutionReason.INFEASIBLE,
            "すべての資源が eCOM-10 では運搬できません\n" + "\n".join(compatibility_result.warnings)
        )
        return no_solution, compatibility_result

    # 2. 制約検証（容量チェック）
    if compatibility_result.total_compatible_weight > ECOM10_MAX_CAPACITY_KG:
        no_solution = NoSolution(
            NoSolutionReason.CAPACITY,
            f"eCOM-10 互換資源の総重量 ({compatibility_result.total_compatible_weight}kg) が "
            f"最大積載量 ({ECOM10_MAX_CAPACITY_KG}kg) を超過しています"
        )
        return no_solution, compatibility_result

    # 3. 車両割り当ての構築
    assignments: List[Tuple[VehicleType, List[Dict[str, object]]]] = []

    # eCOM-10 で運搬可能な資源を割り当て
    if compatibility_result.compatible_pickups:
        assignments.append((ecom10_vehicle, compatibility_result.compatible_pickups))

    # 非互換資源を他車両に割り当て
    if compatibility_result.incompatible_pickups:
        if other_vehicles:
            # 最も適した代替車両を選定（簡略化のため最初の車両を使用）
            best_alternative = other_vehicles[0]
            assignments.append((best_alternative, compatibility_result.incompatible_pickups))
        else:
            no_solution = NoSolution(
                NoSolutionReason.INFEASIBLE,
                "非互換資源を運搬する代替車両が見つかりません"
            )
            return no_solution, compatibility_result

    # 4. ルート最適化実行
    try:
        fleet_solution = solve_fleet_routing(
            distance_matrix=distance_matrix,
            depot=depot,
            sink=sink,
            assignments=assignments,
            vehicle_metadata_map=vehicle_metadata_map,
        )

        return fleet_solution, compatibility_result

    except Exception as e:
        no_solution = NoSolution(
            NoSolutionReason.INFEASIBLE,
            f"ルート最適化中にエラーが発生しました: {str(e)}"
        )
        return no_solution, compatibility_result


def find_alternative_vehicles(
    resource_type: str,
    quantity: int,
    master: ProcessedMasterData,
) -> List[str]:
    """
    非適合資源に対する代替車両を提案

    Args:
        resource_type: 資源種別
        quantity: 量 (kg)
        master: マスタデータ

    Returns:
        代替車両名のリスト
    """
    alternatives = []

    if not master or not master.vehicles:
        return ["適合車両なし"]

    for vehicle in master.vehicles:
        if not vehicle.name or not vehicle.capacity_kg:
            continue

        # eCOM-10は除外
        if vehicle.name == "eCOM-10":
            continue

        compatibility = master.compatibility.get(vehicle.name)
        if not compatibility:
            continue

        # 互換性チェック
        if compatibility.supports.get(resource_type) == True:
            # 容量チェック
            if vehicle.capacity_kg >= quantity:
                alternatives.append(vehicle.name)

    return alternatives if alternatives else ["適合車両なし"]
