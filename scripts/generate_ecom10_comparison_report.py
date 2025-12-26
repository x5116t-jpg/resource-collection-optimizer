"""
eCOM-10 比較レポート自動生成スクリプト

使用例:
    python scripts/generate_ecom10_comparison_report.py --scenario all --output reports/
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# テストシナリオ定義
TEST_SCENARIOS = {
    "compatible_resources": {
        "name": "互換資源のみ",
        "pickups": [
            {"id": "point_1", "kind": "林業残材", "qty": 500},
            {"id": "point_2", "kind": "古紙・段ボール", "qty": 300},
        ]
    },
    "incompatible_resources": {
        "name": "非互換資源のみ",
        "pickups": [
            {"id": "point_1", "kind": "建設廃材", "qty": 800},
            {"id": "point_2", "kind": "金属スクラップ", "qty": 600},
        ]
    },
    "mixed_resources": {
        "name": "混合資源",
        "pickups": [
            {"id": "point_1", "kind": "林業残材", "qty": 600},
            {"id": "point_2", "kind": "建設廃材", "qty": 800},
        ]
    },
}


def generate_report(scenario: str, output_dir: Path) -> None:
    """
    比較レポートを生成

    Args:
        scenario: テストシナリオ名
        output_dir: 出力ディレクトリ
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"ecom10_comparison_{scenario}_{timestamp}.md"

    scenario_data = TEST_SCENARIOS[scenario]

    report_content = f"""# eCOM-10 比較レポート

**シナリオ**: {scenario_data['name']}
**生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## テスト条件

### 回収地点
"""

    for pickup in scenario_data["pickups"]:
        report_content += f"- {pickup['id']}: {pickup['kind']} ({pickup['qty']}kg)\n"

    # eCOM-10互換性チェックのシミュレーション
    try:
        from services.ecom10_comparison import check_ecom10_compatibility
        from services.master_repository import load_processed_master

        # マスタデータの読み込み
        data_dir = project_root / "data" / "processed"
        master = load_processed_master(str(data_dir))

        # 互換性チェック
        compatibility = check_ecom10_compatibility(scenario_data["pickups"], master)

        report_content += f"""
## 互換性チェック結果

### ✅ eCOM-10で運搬可能な資源
"""
        if compatibility.compatible_pickups:
            for pickup in compatibility.compatible_pickups:
                report_content += f"- {pickup.get('kind')}: {pickup.get('qty')}kg\n"
            report_content += f"\n**総重量**: {compatibility.total_compatible_weight}kg\n"
        else:
            report_content += "なし\n"

        report_content += f"""
### ❌ eCOM-10では運搬できない資源
"""
        if compatibility.incompatible_pickups:
            for pickup in compatibility.incompatible_pickups:
                report_content += f"- {pickup.get('kind')}: {pickup.get('qty')}kg\n"
        else:
            report_content += "なし\n"

        if compatibility.warnings:
            report_content += "\n### ⚠️ 警告メッセージ\n"
            for warning in compatibility.warnings:
                report_content += f"{warning}\n\n"

    except Exception as e:
        report_content += f"""
## エラー

互換性チェック中にエラーが発生しました: {str(e)}
"""

    report_content += """
## 比較結果

### 最適解（参考値）

| 項目 | 値 |
|------|-----|
| 総距離 | - |
| 総コスト | - |
| エネルギー消費 | - |
| 車両構成 | - |

### eCOM-10 代替案（参考値）

| 項目 | 値 | 差分 |
|------|-----|------|
| 総距離 | - | - |
| 総コスト | - | - |
| エネルギー消費 | - | - |
| 車両構成 | - | - |

## 結論

このレポートは互換性チェックの結果を示しています。
実際の最適化計算を行うには、道路ネットワークデータと具体的な地点座標が必要です。

---
*自動生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

    # レポート保存
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding="utf-8")

    print(f"✅ レポート生成完了: {report_path}")


def generate_summary(output_dir: Path, scenarios: List[str]) -> None:
    """
    PR用のサマリーレポートを生成

    Args:
        output_dir: 出力ディレクトリ
        scenarios: 実行したシナリオリスト
    """
    summary_path = output_dir / "ecom10_comparison_summary.md"

    summary_content = f"""# eCOM-10 比較分析サマリー

**実行日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**実行シナリオ数**: {len(scenarios)}

## 実行結果

"""

    for scenario in scenarios:
        scenario_data = TEST_SCENARIOS.get(scenario, {})
        scenario_name = scenario_data.get("name", scenario)
        summary_content += f"### {scenario_name}\n"
        summary_content += f"- シナリオ: `{scenario}`\n"
        summary_content += f"- ステータス: ✅ 完了\n\n"

    summary_content += """
## 次のステップ

詳細なレポートは Artifacts からダウンロードしてください。

---
*自動生成レポート*
"""

    summary_path.write_text(summary_content, encoding="utf-8")
    print(f"✅ サマリー生成完了: {summary_path}")


def main():
    parser = argparse.ArgumentParser(description="eCOM-10 比較レポート生成")
    parser.add_argument(
        "--scenario",
        choices=["all"] + list(TEST_SCENARIOS.keys()),
        default="all",
        help="テストシナリオ"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports"),
        help="出力ディレクトリ"
    )

    args = parser.parse_args()

    scenarios_to_run = []
    if args.scenario == "all":
        scenarios_to_run = list(TEST_SCENARIOS.keys())
    else:
        scenarios_to_run = [args.scenario]

    for scenario in scenarios_to_run:
        print(f"\n📊 シナリオ '{scenario}' を実行中...")
        generate_report(scenario, args.output)

    # サマリー生成
    generate_summary(args.output, scenarios_to_run)

    print(f"\n✅ すべてのレポート生成が完了しました")


if __name__ == "__main__":
    main()
