"""Report export module for generating structured data and visualizations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .map_generator import MapGenerator
from .latex_generator import LaTeXGenerator
from .report_config_manager import ReportConfigManager


@dataclass
class ReportExportInput:
    """Input data required for report export."""

    # Input conditions
    depot: Dict[str, Any]
    sink: Dict[str, Any]
    pickups: List[Dict[str, Any]]
    vehicles: List[Dict[str, Any]]
    network_file: str

    # Optimization results
    optimal_solution: Any  # FleetSolution
    graph: Any  # networkx.Graph

    # Optional eCOM-10 comparison
    ecom10_solution: Optional[Any] = None
    compatibility_result: Optional[Any] = None

    # Metadata
    user_note: str = ""


class ReportExporter:
    """Main exporter class for report generation."""

    def __init__(self, output_dir: Path = Path("claudedocs/report_export")):
        """
        Initialize report exporter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.config_manager = ReportConfigManager(self.output_dir / "report_config.json")
        self.map_generator = MapGenerator(self.config_manager)
        self.latex_generator = LaTeXGenerator(self.config_manager)

    def export(self, input_data: ReportExportInput) -> Tuple[Path, List[str]]:
        """
        Export report data to structured files.

        Args:
            input_data: Report export input data

        Returns:
            Tuple of (output directory path, list of warning/error messages)
        """
        messages = []

        # Create directories
        self._create_directories()

        # Validate configuration
        if not self.config_manager.validate():
            msg = "Warning: Configuration validation failed, using defaults"
            print(msg)
            messages.append(msg)

        # Export JSON data
        json_path = self._export_json(input_data)
        print(f"✓ JSON data exported: {json_path}")

        # Export maps
        try:
            map_messages = self._export_maps(input_data)
            messages.extend(map_messages)
            print(f"✓ Maps exported to: {self.output_dir / 'maps'}")
        except Exception as e:
            import traceback
            msg = f"Error: Map export failed: {e}"
            print(msg)
            traceback.print_exc()
            messages.append(msg)
            messages.append(traceback.format_exc())

        # Export LaTeX
        try:
            self._export_latex(input_data)
            print(f"✓ LaTeX code exported to: {self.output_dir / 'latex'}")
        except Exception as e:
            import traceback
            msg = f"Warning: LaTeX export failed: {e}"
            print(msg)
            traceback.print_exc()
            messages.append(msg)

        # Create README
        self._create_readme()
        print(f"✓ README created")

        return self.output_dir, messages

    def _create_directories(self) -> None:
        """Create necessary directory structure."""
        (self.output_dir / "maps").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "latex").mkdir(parents=True, exist_ok=True)

    def _export_json(self, input_data: ReportExportInput) -> Path:
        """Export structured JSON data."""
        data = self._build_json_data(input_data)
        json_path = self.output_dir / "report_data.json"

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return json_path

    def _build_json_data(self, input_data: ReportExportInput) -> Dict:
        """Build JSON data structure."""
        from .route_reconstruction import reconstruct_paths

        # Metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "system_version": "1.0.0",
            "export_config_version": self.config_manager.config.get("version", "1.0.0"),
            "user_note": input_data.user_note
        }

        # Input conditions
        input_conditions = {
            "depot": input_data.depot,
            "sink": input_data.sink,
            "pickups": input_data.pickups,
            "vehicles": input_data.vehicles,
            "network_file": input_data.network_file
        }

        # Optimal solution
        optimal_solution = self._serialize_fleet_solution(
            input_data.optimal_solution,
            input_data.graph
        )

        # eCOM-10 solution (if available)
        ecom10_solution = None
        if input_data.ecom10_solution is not None:
            if hasattr(input_data.ecom10_solution, 'routes'):
                # FleetSolution
                ecom10_solution = {
                    "feasible": True,
                    **self._serialize_fleet_solution(input_data.ecom10_solution, input_data.graph)
                }
            else:
                # NoSolution
                ecom10_solution = {
                    "feasible": False,
                    "reason": str(input_data.ecom10_solution.reason) if hasattr(input_data.ecom10_solution, 'reason') else "unknown",
                    "message": str(input_data.ecom10_solution.message) if hasattr(input_data.ecom10_solution, 'message') else ""
                }

            # Add compatibility info
            if input_data.compatibility_result:
                ecom10_solution["compatibility"] = {
                    "compatible_resources": [
                        str(p.get("kind", "")) for p in input_data.compatibility_result.compatible_pickups
                    ],
                    "incompatible_resources": [
                        str(p.get("kind", "")) for p in input_data.compatibility_result.incompatible_pickups
                    ],
                    "warnings": input_data.compatibility_result.warnings,
                    "total_compatible_weight_kg": input_data.compatibility_result.total_compatible_weight
                }

        return {
            "metadata": metadata,
            "input_conditions": input_conditions,
            "optimal_solution": optimal_solution,
            "ecom10_solution": ecom10_solution
        }

    def _serialize_fleet_solution(self, solution: Any, graph: Any) -> Dict:
        """Serialize FleetSolution to JSON-compatible dict."""
        from .route_reconstruction import reconstruct_paths

        routes_data = []
        all_polylines = []

        for route in solution.routes:
            route_order = route.solution.order

            # Reconstruct polylines
            try:
                polylines = reconstruct_paths(graph, route_order)
                all_polylines.extend(polylines)
            except Exception as e:
                print(f"Warning: Failed to reconstruct route polylines: {e}")
                polylines = []

            routes_data.append({
                "vehicle_name": route.vehicle.name,
                "pickups": route.pickups,
                "route_order": route_order,
                "distance_km": route.total_distance_m / 1000.0,
                "cost_breakdown": route.solution.cost_breakdown
            })

        return {
            "total_distance_km": solution.total_distance_m / 1000.0,
            "cost_breakdown": solution.cost_breakdown,
            "routes": routes_data,
            "route_polylines": all_polylines
        }

    def _export_maps(self, input_data: ReportExportInput) -> List[str]:
        """Export map visualizations."""
        import traceback
        messages = []
        maps_dir = self.output_dir / "maps"

        # 1. Conditions map
        try:
            conditions_map = self.map_generator.create_conditions_map(
                depot=input_data.depot,
                sink=input_data.sink,
                pickups=input_data.pickups
            )
            self.map_generator.save_map(
                conditions_map,
                maps_dir / "conditions",
                save_html=True,
                save_image=True
            )
            messages.append("✓ Conditions map created successfully")
        except Exception as e:
            msg = f"Warning: Failed to create conditions map: {e}"
            print(msg)
            traceback.print_exc()
            messages.append(msg)

        # 2. Optimal route map
        try:
            optimal_map = self.map_generator.create_route_map(
                graph=input_data.graph,
                solution=input_data.optimal_solution,
                depot=input_data.depot,
                sink=input_data.sink,
                title="最適ルート"
            )
            self.map_generator.save_map(
                optimal_map,
                maps_dir / "optimal_route",
                save_html=True,
                save_image=True
            )
            messages.append("✓ Optimal route map created successfully")
        except Exception as e:
            msg = f"Error: Failed to create optimal route map: {e}"
            print(msg)
            traceback.print_exc()
            messages.append(msg)
            messages.append(f"Details: {traceback.format_exc()}")

        # 3. eCOM-10 route map (if available)
        if input_data.ecom10_solution is not None and hasattr(input_data.ecom10_solution, 'routes'):
            try:
                ecom10_map = self.map_generator.create_route_map(
                    graph=input_data.graph,
                    solution=input_data.ecom10_solution,
                    depot=input_data.depot,
                    sink=input_data.sink,
                    title="eCOM-10ルート"
                )
                self.map_generator.save_map(
                    ecom10_map,
                    maps_dir / "ecom10_route",
                    save_html=True,
                    save_image=True
                )
                messages.append("✓ eCOM-10 route map created successfully")
            except Exception as e:
                msg = f"Warning: Failed to create eCOM-10 route map: {e}"
                print(msg)
                traceback.print_exc()
                messages.append(msg)

        return messages

    def _export_latex(self, input_data: ReportExportInput) -> None:
        """Export LaTeX code."""
        latex_dir = self.output_dir / "latex"

        # 1. Input conditions table
        try:
            conditions_tex = self.latex_generator.generate_conditions_table(
                depot=input_data.depot,
                sink=input_data.sink,
                pickups=input_data.pickups,
                vehicles=input_data.vehicles
            )
            (latex_dir / "input_conditions.tex").write_text(conditions_tex, encoding="utf-8")
        except Exception as e:
            print(f"Warning: Failed to generate conditions table: {e}")

        # 2. Cost comparison table
        try:
            comparison_tex = self.latex_generator.generate_cost_comparison_table(
                optimal_solution=input_data.optimal_solution,
                ecom10_solution=input_data.ecom10_solution
            )
            (latex_dir / "cost_comparison.tex").write_text(comparison_tex, encoding="utf-8")
        except Exception as e:
            print(f"Warning: Failed to generate cost comparison table: {e}")

        # 3. Optimal solution cost detail
        try:
            optimal_detail_tex = self.latex_generator.generate_cost_detail_table(
                input_data.optimal_solution.cost_breakdown,
                title="最適解コスト詳細"
            )
            (latex_dir / "optimal_cost_detail.tex").write_text(optimal_detail_tex, encoding="utf-8")
        except Exception as e:
            print(f"Warning: Failed to generate optimal cost detail: {e}")

        # 4. eCOM-10 cost detail (if available)
        if input_data.ecom10_solution is not None and hasattr(input_data.ecom10_solution, 'cost_breakdown'):
            try:
                ecom10_detail_tex = self.latex_generator.generate_cost_detail_table(
                    input_data.ecom10_solution.cost_breakdown,
                    title="eCOM-10コスト詳細"
                )
                (latex_dir / "ecom10_cost_detail.tex").write_text(ecom10_detail_tex, encoding="utf-8")
            except Exception as e:
                print(f"Warning: Failed to generate eCOM-10 cost detail: {e}")

        # 5. Route details
        try:
            route_tex = self.latex_generator.generate_route_details(
                input_data.optimal_solution
            )
            (latex_dir / "route_details.tex").write_text(route_tex, encoding="utf-8")
        except Exception as e:
            print(f"Warning: Failed to generate route details: {e}")

    def _create_readme(self) -> None:
        """Create README file explaining the export."""
        readme_content = """# 報告書出力データ

このディレクトリには、資源回収ルート最適化システムの計算結果が保存されています。

## ファイル構成

### report_data.json
計算条件、最適化結果、eCOM-10比較結果を含む構造化データ。

### report_config.json
地図生成とLaTeX出力の設定ファイル。ズームレベル、画像サイズ、色などをカスタマイズ可能。

### maps/
地図画像ファイル:
- `conditions.png/html`: 計算条件地図（車庫・回収地点・集積場所）
- `optimal_route.png/html`: 最適ルート地図
- `ecom10_route.png/html`: eCOM-10ルート地図（存在する場合）

### latex/
LaTeX報告書用のテーブルと図:
- `input_conditions.tex`: 計算条件表
- `cost_comparison.tex`: コスト比較表
- `optimal_cost_detail.tex`: 最適解コスト詳細
- `ecom10_cost_detail.tex`: eCOM-10コスト詳細（存在する場合）
- `route_details.tex`: ルート詳細

## 使用方法

### 地図の調整

1. HTMLファイルをブラウザで開いて表示を確認
2. `report_config.json` の設定を編集
3. `python scripts/regenerate_maps.py` で地図を再生成

### LaTeX報告書への統合

1. `docs/report_04/main.tex` に以下を追加:

```latex
\\section{計算結果}
\\input{../../claudedocs/report_export/latex/input_conditions}
\\input{../../claudedocs/report_export/latex/cost_comparison}
```

2. コンパイル: `cd docs/report_04 && cmd /c compile.bat`

## 地図設定のカスタマイズ

`report_config.json` の主要パラメータ:

- `zoom_start`: ズームレベル (1-18)
- `width_px`, `height_px`: 画像サイズ
- `colors`: マーカーの色
- `marker_sizes`: マーカーのサイズ
- `route_color`, `route_weight`: ルート線の色と太さ

## 再生成スクリプト

### 地図の再生成
```bash
python scripts/regenerate_maps.py
```

### 地図設定の調整
```bash
python scripts/adjust_report_maps.py
```

### LaTeX自動生成
```bash
python scripts/generate_latex_from_json.py
```
"""
        readme_path = self.output_dir / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
