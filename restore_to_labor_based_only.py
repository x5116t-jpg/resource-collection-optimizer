"""
前回の作業時間ベース人件費計算修正完了時点に戻す

復元内容：
- 今回削除した変動費6項目を復元
- 今回削除した固定費4項目を復元
- eCOM-10の税金を0.0に戻す
- 前回削除した人件費4項目は削除したまま（新パラメータで計算）
- 新パラメータ（hourly_wage等）は維持
"""
import json
from pathlib import Path
from typing import Dict

def restore_to_labor_based_only(current_path: Path, before_simplify_path: Path, output_path: Path):
    """前回の修正完了時点に戻す"""

    # 現在のデータ（前回+今回の修正が適用済み）
    with current_path.open('r', encoding='utf-8') as f:
        current_data = json.load(f)

    # 簡素化前のデータ（全項目が存在）
    with before_simplify_path.open('r', encoding='utf-8') as f:
        before_data = json.load(f)

    print("=" * 60)
    print("前回の作業時間ベース人件費計算修正完了時点に復元")
    print("=" * 60)
    print()

    # 名前でマッピング
    before_vehicles = {v['name']: v for v in before_data['vehicles']}

    restored_vehicles = []

    for current_vehicle in current_data['vehicles']:
        vehicle_name = current_vehicle.get('name', 'unknown')
        before_vehicle = before_vehicles.get(vehicle_name)

        if not before_vehicle:
            print(f"[警告] {vehicle_name} が簡素化前データに見つかりません")
            restored_vehicles.append(current_vehicle)
            continue

        print(f"\n[{vehicle_name}] 復元中:")

        # 1. 変動費: 今回削除した6項目を復元（前回削除した4項目は復元しない）
        if 'variable_cost_breakdown' in current_vehicle:
            # 今回削除した6項目を簡素化前データから取得
            items_to_restore = [
                "高速料金_円_per_km",
                "回収容器費_円_per_km",
                "消耗品費_円_per_km",
                "通信費_円_per_km",
                "マニフェスト費用_円_per_km",
                "処理費_参考値_円_per_km"
            ]

            for key in items_to_restore:
                if key in before_vehicle['variable_cost_breakdown']:
                    value = before_vehicle['variable_cost_breakdown'][key]
                    current_vehicle['variable_cost_breakdown'][key] = value
                    print(f"  [変動費復元] {key} = {value}")

            # 変動費合計を再計算
            variable_cost_sum = sum(current_vehicle['variable_cost_breakdown'].values())
            current_vehicle['variable_cost_per_km'] = variable_cost_sum
            print(f"  [変動費再計算] {variable_cost_sum:.1f} 円/km")

        # 2. 固定費: 今回削除した4項目を復元
        if 'fixed_cost_breakdown' in current_vehicle:
            items_to_restore = [
                "許認可費用_万円_per_年",
                "システム利用料_万円_per_年",
                "福利厚生費_万円_per_年",
                "社会保険料_万円_per_年"
            ]

            for key in items_to_restore:
                if key in before_vehicle['fixed_cost_breakdown']:
                    value = before_vehicle['fixed_cost_breakdown'][key]
                    current_vehicle['fixed_cost_breakdown'][key] = value
                    print(f"  [固定費復元] {key} = {value} 万円/年")

            # 固定費合計を再計算
            annual_fixed_cost_manyen = sum(current_vehicle['fixed_cost_breakdown'].values())
            annual_fixed_cost_yen = annual_fixed_cost_manyen * 10000
            current_vehicle['annual_fixed_cost'] = annual_fixed_cost_yen

            # 固定費単価を再計算
            annual_distance = current_vehicle.get('annual_distance_km', 0)
            if annual_distance > 0:
                fixed_cost_per_km = annual_fixed_cost_yen / annual_distance
                current_vehicle['fixed_cost_per_km'] = round(fixed_cost_per_km, 2)

            print(f"  [固定費再計算] {annual_fixed_cost_yen:,.0f} 円/年 ({current_vehicle.get('fixed_cost_per_km', 0):.2f} 円/km)")

        # 3. eCOM-10の税金を0.0に戻す
        if vehicle_name == 'eCOM-10':
            print(f"\n  [eCOM-10] 税金を0.0に戻す:")
            if 'fixed_cost_breakdown' in current_vehicle:
                # 自動車税
                old_auto_tax = current_vehicle['fixed_cost_breakdown'].get('自動車税_万円_per_年', 0.0)
                current_vehicle['fixed_cost_breakdown']['自動車税_万円_per_年'] = 0.0
                print(f"    自動車税: {old_auto_tax} 万円/年 -> 0.0 万円/年")

                # 重量税
                old_weight_tax = current_vehicle['fixed_cost_breakdown'].get('重量税_万円_per_年', 0.0)
                current_vehicle['fixed_cost_breakdown']['重量税_万円_per_年'] = 0.0
                print(f"    重量税: {old_weight_tax} 万円/年 -> 0.0 万円/年")

                # 固定費合計を再計算
                annual_fixed_cost_manyen = sum(current_vehicle['fixed_cost_breakdown'].values())
                annual_fixed_cost_yen = annual_fixed_cost_manyen * 10000
                current_vehicle['annual_fixed_cost'] = annual_fixed_cost_yen

                annual_distance = current_vehicle.get('annual_distance_km', 0)
                if annual_distance > 0:
                    fixed_cost_per_km = annual_fixed_cost_yen / annual_distance
                    current_vehicle['fixed_cost_per_km'] = round(fixed_cost_per_km, 2)

                print(f"    固定費合計: {annual_fixed_cost_yen:,.0f} 円/年 ({current_vehicle.get('fixed_cost_per_km', 0):.2f} 円/km)")

        # 4. 新パラメータ（hourly_wage等）は維持
        if 'hourly_wage' in current_vehicle:
            print(f"  [維持] hourly_wage = {current_vehicle['hourly_wage']} 円/h")
            print(f"  [維持] average_speed_km_per_h = {current_vehicle['average_speed_km_per_h']} km/h")
            print(f"  [維持] loading_time_per_kg = {current_vehicle['loading_time_per_kg']} 秒/kg")

        restored_vehicles.append(current_vehicle)

    # 更新されたデータを保存
    current_data['vehicles'] = restored_vehicles

    print("\n" + "=" * 60)
    print(f"Saving: {output_path}")
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

    print(f"完了: {len(restored_vehicles)} 台の車両データを復元しました")
    print()
    print("復元内容:")
    print("  ✓ 変動費6項目を復元（高速料金、回収容器費、消耗品費、通信費、マニフェスト費用、処理費）")
    print("  ✓ 固定費4項目を復元（許認可費用、システム利用料、福利厚生費、社会保険料）")
    print("  ✓ eCOM-10の税金を0.0に戻す")
    print("  ✓ 新パラメータ（hourly_wage等）を維持")
    print("  ✓ 前回削除した人件費4項目は削除のまま")


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    current_file = base_dir / "data" / "processed" / "vehicles.json"
    before_file = base_dir / "vehicles_before_simplify.json"
    output_file = base_dir / "data" / "processed" / "vehicles.json"

    restore_to_labor_based_only(current_file, before_file, output_file)

    print("\n" + "=" * 60)
    print("前回の作業時間ベース人件費計算修正完了時点に復元しました")
    print("=" * 60)
