"""
コスト項目削減とeCOM-10税金修正スクリプト

変更内容：
1. 変動費から6項目を削除
2. 固定費から4項目を削除
3. eCOM-10の自動車税・重量税を修正
4. 合計値を再計算
"""
import json
from pathlib import Path
from typing import Dict, List

# 削除対象の変動費項目
REMOVE_VARIABLE_COST_KEYS = [
    "高速料金_円_per_km",
    "回収容器費_円_per_km",
    "消耗品費_円_per_km",
    "通信費_円_per_km",
    "マニフェスト費用_円_per_km",
    "処理費_参考値_円_per_km"
]

# 削除対象の固定費項目
REMOVE_FIXED_COST_KEYS = [
    "許認可費用_万円_per_年",
    "システム利用料_万円_per_年",
    "福利厚生費_万円_per_年",
    "社会保険料_万円_per_年"
]


def simplify_vehicle_costs(vehicle: Dict) -> Dict:
    """
    車両のコスト項目を簡素化し、合計値を再計算する

    Args:
        vehicle: 車両データ（辞書）

    Returns:
        更新された車両データ
    """
    vehicle_name = vehicle.get("name", "unknown")

    # 変動費項目の削除
    if "variable_cost_breakdown" in vehicle:
        for key in REMOVE_VARIABLE_COST_KEYS:
            if key in vehicle["variable_cost_breakdown"]:
                removed_value = vehicle["variable_cost_breakdown"].pop(key)
                print(f"  [変動費削除] {vehicle_name}: {key} = {removed_value}")

        # 変動費合計の再計算
        variable_cost_sum = sum(vehicle["variable_cost_breakdown"].values())
        vehicle["variable_cost_per_km"] = variable_cost_sum
        print(f"  [変動費再計算] {vehicle_name}: {variable_cost_sum:.1f} 円/km")

    # 固定費項目の削除
    if "fixed_cost_breakdown" in vehicle:
        for key in REMOVE_FIXED_COST_KEYS:
            if key in vehicle["fixed_cost_breakdown"]:
                removed_value = vehicle["fixed_cost_breakdown"].pop(key)
                print(f"  [固定費削除] {vehicle_name}: {key} = {removed_value} 万円/年")

        # 固定費合計の再計算（万円 → 円）
        annual_fixed_cost_manyen = sum(vehicle["fixed_cost_breakdown"].values())
        annual_fixed_cost_yen = annual_fixed_cost_manyen * 10000
        vehicle["annual_fixed_cost"] = annual_fixed_cost_yen

        # 固定費単価の再計算
        annual_distance = vehicle.get("annual_distance_km", 0)
        if annual_distance > 0:
            fixed_cost_per_km = annual_fixed_cost_yen / annual_distance
            vehicle["fixed_cost_per_km"] = round(fixed_cost_per_km, 2)

        print(f"  [固定費再計算] {vehicle_name}: {annual_fixed_cost_yen:,.0f} 円/年 ({vehicle.get('fixed_cost_per_km', 0):.2f} 円/km)")

    return vehicle


def fix_ecom10_taxes(vehicle: Dict) -> Dict:
    """
    eCOM-10の税金を修正する

    Args:
        vehicle: 車両データ（辞書）

    Returns:
        更新された車両データ
    """
    if vehicle.get("name") != "eCOM-10":
        return vehicle

    print(f"\n[eCOM-10] 税金を修正:")

    if "fixed_cost_breakdown" in vehicle:
        # 自動車税の修正
        old_auto_tax = vehicle["fixed_cost_breakdown"].get("自動車税_万円_per_年", 0.0)
        vehicle["fixed_cost_breakdown"]["自動車税_万円_per_年"] = 2.5
        print(f"  自動車税: {old_auto_tax} 万円/年 → 2.5 万円/年")

        # 重量税の修正
        old_weight_tax = vehicle["fixed_cost_breakdown"].get("重量税_万円_per_年", 0.0)
        vehicle["fixed_cost_breakdown"]["重量税_万円_per_年"] = 1.0
        print(f"  重量税: {old_weight_tax} 万円/年 → 1.0 万円/年")

        # 固定費合計の再計算
        annual_fixed_cost_manyen = sum(vehicle["fixed_cost_breakdown"].values())
        annual_fixed_cost_yen = annual_fixed_cost_manyen * 10000
        vehicle["annual_fixed_cost"] = annual_fixed_cost_yen

        # 固定費単価の再計算
        annual_distance = vehicle.get("annual_distance_km", 0)
        if annual_distance > 0:
            fixed_cost_per_km = annual_fixed_cost_yen / annual_distance
            vehicle["fixed_cost_per_km"] = round(fixed_cost_per_km, 2)

        print(f"  固定費合計: {annual_fixed_cost_yen:,.0f} 円/年 ({vehicle.get('fixed_cost_per_km', 0):.2f} 円/km)")

    return vehicle


def update_vehicles_json(input_path: Path, output_path: Path):
    """vehicles.jsonを更新"""

    # JSONを読み込み
    print(f"Loading: {input_path}")
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n処理対象車両数: {len(data.get('vehicles', []))}")
    print("=" * 60)

    # 各車両を更新
    updated_vehicles = []
    for vehicle in data.get("vehicles", []):
        vehicle_name = vehicle.get("name", "unknown")
        print(f"\n[{vehicle_name}] 処理中:")

        # コスト項目の簡素化
        vehicle = simplify_vehicle_costs(vehicle)

        # eCOM-10の場合は税金を修正
        vehicle = fix_ecom10_taxes(vehicle)

        updated_vehicles.append(vehicle)

    # 更新されたデータを保存
    data["vehicles"] = updated_vehicles

    print("\n" + "=" * 60)
    print(f"Saving: {output_path}")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"完了: {len(updated_vehicles)} 台の車両データを更新しました")


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    input_file = base_dir / "data" / "processed" / "vehicles.json"
    output_file = base_dir / "data" / "processed" / "vehicles.json"

    print("=" * 60)
    print("コスト項目削減とeCOM-10税金修正スクリプト")
    print("=" * 60)
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print()

    update_vehicles_json(input_file, output_file)

    print("\n" + "=" * 60)
    print("すべての処理が完了しました")
    print("=" * 60)
