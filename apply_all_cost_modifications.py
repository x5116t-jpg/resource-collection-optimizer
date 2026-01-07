"""
前回の作業時間ベース人件費計算修正 + 今回のコスト項目削減を統合適用

統合修正内容：
【前回の修正】
1. 人件費項目を削除（4項目）
2. 新パラメータ追加（hourly_wage, average_speed_km_per_h, loading_time_per_kg）

【今回の修正】
1. 変動費項目削除（6項目）
2. 固定費項目削除（4項目）
3. eCOM-10税金修正
"""
import json
from pathlib import Path
from typing import Dict, List

# 【前回の修正】削除対象の人件費項目
REMOVE_LABOR_COST_KEYS = [
    "運転手人件費_円_per_km",
    "作業時間人件費_15km_円_per_km",
    "作業時間人件費_30km_円_per_km",
    "作業時間人件費_40km_円_per_km"
]

# 【今回の修正】削除対象の変動費項目
REMOVE_VARIABLE_COST_KEYS = [
    "高速料金_円_per_km",
    "回収容器費_円_per_km",
    "消耗品費_円_per_km",
    "通信費_円_per_km",
    "マニフェスト費用_円_per_km",
    "処理費_参考値_円_per_km"
]

# 【今回の修正】削除対象の固定費項目
REMOVE_FIXED_COST_KEYS = [
    "許認可費用_万円_per_年",
    "システム利用料_万円_per_年",
    "福利厚生費_万円_per_年",
    "社会保険料_万円_per_年"
]

# 【前回の修正】車両タイプ別の作業時間ベースパラメータ
# 設計書の推奨パラメータ一覧から抽出
VEHICLE_LABOR_PARAMS = {
    "軽トラック": {
        "hourly_wage": 3000.0,
        "average_speed_km_per_h": 30.0,
        "loading_time_per_kg": 2.0
    },
    "2t平ボディ": {
        "hourly_wage": 3200.0,
        "average_speed_km_per_h": 35.0,
        "loading_time_per_kg": 1.8
    },
    "2tダンプ": {
        "hourly_wage": 3200.0,
        "average_speed_km_per_h": 35.0,
        "loading_time_per_kg": 1.5
    },
    "4t平ボディ": {
        "hourly_wage": 3500.0,
        "average_speed_km_per_h": 40.0,
        "loading_time_per_kg": 2.2
    },
    "4tダンプ": {
        "hourly_wage": 3500.0,
        "average_speed_km_per_h": 40.0,
        "loading_time_per_kg": 1.8
    },
    "10tダンプ": {
        "hourly_wage": 4000.0,
        "average_speed_km_per_h": 35.0,
        "loading_time_per_kg": 2.5
    },
    "eCOM-10": {
        "hourly_wage": 2800.0,
        "average_speed_km_per_h": 12.0,
        "loading_time_per_kg": 2.5
    },
    # 他の車両はデフォルト値を使用
}


def apply_labor_cost_modification(vehicle: Dict) -> Dict:
    """
    【前回の修正】作業時間ベース人件費計算への変更を適用

    Args:
        vehicle: 車両データ（辞書）

    Returns:
        更新された車両データ
    """
    vehicle_name = vehicle.get("name", "unknown")
    print(f"\n[{vehicle_name}] 前回の修正（作業時間ベース人件費）:")

    # 1. 旧人件費項目の削除
    if "variable_cost_breakdown" in vehicle:
        for key in REMOVE_LABOR_COST_KEYS:
            if key in vehicle["variable_cost_breakdown"]:
                removed_value = vehicle["variable_cost_breakdown"].pop(key)
                print(f"  [削除] {key} = {removed_value}")

    # 2. 新パラメータの追加
    params = VEHICLE_LABOR_PARAMS.get(vehicle_name, {
        "hourly_wage": 3000.0,
        "average_speed_km_per_h": 30.0,
        "loading_time_per_kg": 2.0
    })

    vehicle["hourly_wage"] = params["hourly_wage"]
    vehicle["average_speed_km_per_h"] = params["average_speed_km_per_h"]
    vehicle["loading_time_per_kg"] = params["loading_time_per_kg"]

    print(f"  [追加] hourly_wage = {params['hourly_wage']} 円/h")
    print(f"  [追加] average_speed_km_per_h = {params['average_speed_km_per_h']} km/h")
    print(f"  [追加] loading_time_per_kg = {params['loading_time_per_kg']} 秒/kg")

    return vehicle


def simplify_vehicle_costs(vehicle: Dict) -> Dict:
    """
    【今回の修正】車両のコスト項目を簡素化し、合計値を再計算する

    Args:
        vehicle: 車両データ（辞書）

    Returns:
        更新された車両データ
    """
    vehicle_name = vehicle.get("name", "unknown")
    print(f"\n[{vehicle_name}] 今回の修正（コスト項目削減）:")

    # 変動費項目の削除
    if "variable_cost_breakdown" in vehicle:
        for key in REMOVE_VARIABLE_COST_KEYS:
            if key in vehicle["variable_cost_breakdown"]:
                removed_value = vehicle["variable_cost_breakdown"].pop(key)
                print(f"  [変動費削除] {key} = {removed_value}")

        # 変動費合計の再計算
        variable_cost_sum = sum(vehicle["variable_cost_breakdown"].values())
        vehicle["variable_cost_per_km"] = variable_cost_sum
        print(f"  [変動費再計算] {variable_cost_sum:.1f} 円/km")

    # 固定費項目の削除
    if "fixed_cost_breakdown" in vehicle:
        for key in REMOVE_FIXED_COST_KEYS:
            if key in vehicle["fixed_cost_breakdown"]:
                removed_value = vehicle["fixed_cost_breakdown"].pop(key)
                print(f"  [固定費削除] {key} = {removed_value} 万円/年")

        # 固定費合計の再計算（万円 → 円）
        annual_fixed_cost_manyen = sum(vehicle["fixed_cost_breakdown"].values())
        annual_fixed_cost_yen = annual_fixed_cost_manyen * 10000
        vehicle["annual_fixed_cost"] = annual_fixed_cost_yen

        # 固定費単価の再計算
        annual_distance = vehicle.get("annual_distance_km", 0)
        if annual_distance > 0:
            fixed_cost_per_km = annual_fixed_cost_yen / annual_distance
            vehicle["fixed_cost_per_km"] = round(fixed_cost_per_km, 2)

        print(f"  [固定費再計算] {annual_fixed_cost_yen:,.0f} 円/年 ({vehicle.get('fixed_cost_per_km', 0):.2f} 円/km)")

    return vehicle


def fix_ecom10_taxes(vehicle: Dict) -> Dict:
    """
    【今回の修正】eCOM-10の税金を修正する

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
        print(f"  自動車税: {old_auto_tax} 万円/年 -> 2.5 万円/年")

        # 重量税の修正
        old_weight_tax = vehicle["fixed_cost_breakdown"].get("重量税_万円_per_年", 0.0)
        vehicle["fixed_cost_breakdown"]["重量税_万円_per_年"] = 1.0
        print(f"  重量税: {old_weight_tax} 万円/年 -> 1.0 万円/年")

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
    """vehicles.jsonに前回＋今回の修正を統合適用"""

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
        print(f"\n{'=' * 60}")
        print(f"車両: {vehicle_name}")
        print("=" * 60)

        # 【前回の修正】作業時間ベース人件費計算
        vehicle = apply_labor_cost_modification(vehicle)

        # 【今回の修正】コスト項目の簡素化
        vehicle = simplify_vehicle_costs(vehicle)

        # 【今回の修正】eCOM-10の場合は税金を修正
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
    print("前回＋今回の修正を統合適用")
    print("=" * 60)
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print()
    print("【前回の修正】作業時間ベース人件費計算")
    print("  - 人件費項目削除（4項目）")
    print("  - 新パラメータ追加（hourly_wage, average_speed_km_per_h, loading_time_per_kg）")
    print()
    print("【今回の修正】コスト項目削減とeCOM-10税金修正")
    print("  - 変動費削除（6項目）")
    print("  - 固定費削除（4項目）")
    print("  - eCOM-10税金修正")
    print()

    update_vehicles_json(input_file, output_file)

    print("\n" + "=" * 60)
    print("すべての処理が完了しました")
    print("=" * 60)
