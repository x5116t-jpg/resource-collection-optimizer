"""LaTeX code generation module for report export."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class LaTeXGenerator:
    """Generates LaTeX code for report tables and figures."""

    def __init__(self, config_manager):
        """
        Initialize LaTeX generator.

        Args:
            config_manager: ReportConfigManager instance
        """
        self.config = config_manager.config

    def generate_conditions_table(
        self,
        depot: Dict,
        sink: Dict,
        pickups: List[Dict],
        vehicles: List[Dict]
    ) -> str:
        """
        Generate LaTeX table for input conditions.

        Args:
            depot: Depot information
            sink: Sink information
            pickups: List of pickup information
            vehicles: List of vehicle information

        Returns:
            LaTeX table code
        """
        table_format = self.config.get("latex_settings", {}).get("table_format", "booktabs")

        # Header
        if table_format == "booktabs":
            latex = r"\begin{table}[h]" + "\n"
            latex += r"\centering" + "\n"
            latex += r"\caption{計算条件一覧}" + "\n"
            latex += r"\begin{tabular}{ll}" + "\n"
            latex += r"\toprule" + "\n"
            latex += r"項目 & 値 \\" + "\n"
            latex += r"\midrule" + "\n"
        else:
            latex = r"\begin{table}[h]" + "\n"
            latex += r"\centering" + "\n"
            latex += r"\caption{計算条件一覧}" + "\n"
            latex += r"\begin{tabular}{|l|l|}" + "\n"
            latex += r"\hline" + "\n"
            latex += r"項目 & 値 \\" + "\n"
            latex += r"\hline" + "\n"

        # Content rows
        rows = []
        depot_label = depot.get('label', depot.get('id', '不明'))
        sink_label = sink.get('label', sink.get('id', '不明'))

        rows.append(f"車庫 & {depot_label} ({depot['lat']:.4f}°N, {depot['lon']:.4f}°E) \\\\")
        rows.append(f"集積場所 & {sink_label} ({sink['lat']:.4f}°N, {sink['lon']:.4f}°E) \\\\")
        rows.append(f"回収地点数 & {len(pickups)} 箇所 \\\\")

        # Resource summary
        resource_summary: Dict[str, int] = {}
        for p in pickups:
            res = p.get("resource_type", p.get("kind", "不明"))
            qty = p.get("quantity_kg", p.get("qty", 0))
            resource_summary[res] = resource_summary.get(res, 0) + qty

        for res, total_qty in resource_summary.items():
            rows.append(f"　{res} & {total_qty} kg \\\\")

        rows.append(f"車両候補数 & {len(vehicles)} 種類 \\\\")

        # Footer
        if table_format == "booktabs":
            footer = r"\bottomrule" + "\n"
            footer += r"\end{tabular}" + "\n"
            footer += r"\end{table}" + "\n"
        else:
            footer = r"\hline" + "\n"
            footer += r"\end{tabular}" + "\n"
            footer += r"\end{table}" + "\n"

        return latex + "\n".join(rows) + "\n" + footer

    def generate_cost_comparison_table(
        self,
        optimal_solution: Any,
        ecom10_solution: Optional[Any] = None
    ) -> str:
        """
        Generate LaTeX table comparing costs between solutions.

        Args:
            optimal_solution: Optimal FleetSolution
            ecom10_solution: eCOM-10 FleetSolution or NoSolution

        Returns:
            LaTeX table code
        """
        table_format = self.config.get("latex_settings", {}).get("table_format", "booktabs")
        number_fmt = self.config.get("latex_settings", {}).get("number_format", "{:,.0f}")

        # Header
        if table_format == "booktabs":
            latex = r"\begin{table}[h]" + "\n"
            latex += r"\centering" + "\n"
            latex += r"\caption{コスト比較表}" + "\n"
            latex += r"\begin{tabular}{lrr}" + "\n"
            latex += r"\toprule" + "\n"
            latex += r"項目 & 最適解 & eCOM-10 \\" + "\n"
            latex += r"\midrule" + "\n"
        else:
            latex = r"\begin{table}[h]" + "\n"
            latex += r"\centering" + "\n"
            latex += r"\caption{コスト比較表}" + "\n"
            latex += r"\begin{tabular}{|l|r|r|}" + "\n"
            latex += r"\hline" + "\n"
            latex += r"項目 & 最適解 & eCOM-10 \\" + "\n"
            latex += r"\hline" + "\n"

        # Data rows
        optimal_cost = optimal_solution.cost_breakdown
        has_ecom10 = ecom10_solution is not None and hasattr(ecom10_solution, 'cost_breakdown')
        ecom10_cost = ecom10_solution.cost_breakdown if has_ecom10 else {}

        rows = []

        # Distance
        optimal_dist = optimal_solution.total_distance_m / 1000.0
        ecom10_dist = ecom10_solution.total_distance_m / 1000.0 if has_ecom10 else 0
        ecom10_dist_str = f"{ecom10_dist:.2f}" if has_ecom10 else "-"
        rows.append(f"総距離 [km] & {optimal_dist:.2f} & {ecom10_dist_str} \\\\")

        # Fixed cost
        optimal_fixed = optimal_cost.get('fixed_cost', 0)
        ecom10_fixed = ecom10_cost.get('fixed_cost', 0) if has_ecom10 else 0
        ecom10_fixed_str = number_fmt.format(ecom10_fixed) if has_ecom10 else "-"
        rows.append(f"固定費 [円] & {number_fmt.format(optimal_fixed)} & {ecom10_fixed_str} \\\\")

        # Distance cost
        optimal_variable = optimal_cost.get('distance_cost', 0)
        ecom10_variable = ecom10_cost.get('distance_cost', 0) if has_ecom10 else 0
        ecom10_variable_str = number_fmt.format(ecom10_variable) if has_ecom10 else "-"
        rows.append(f"距離費 [円] & {number_fmt.format(optimal_variable)} & {ecom10_variable_str} \\\\")

        # Total cost
        optimal_total = optimal_cost.get('total_cost', 0)
        ecom10_total = ecom10_cost.get('total_cost', 0) if has_ecom10 else 0
        ecom10_total_str = number_fmt.format(ecom10_total) if has_ecom10 else "-"
        rows.append(f"総コスト [円] & {number_fmt.format(optimal_total)} & {ecom10_total_str} \\\\")

        # Energy consumption (if available)
        if 'energy_consumption_kwh' in optimal_cost:
            optimal_energy = optimal_cost['energy_consumption_kwh']
            ecom10_energy = ecom10_cost.get('energy_consumption_kwh', 0) if has_ecom10 else 0
            ecom10_energy_str = f"{ecom10_energy:.2f}" if has_ecom10 else "-"
            rows.append(f"エネルギー消費 [kWh] & {optimal_energy:.2f} & {ecom10_energy_str} \\\\")

        # Footer
        if table_format == "booktabs":
            footer = r"\bottomrule" + "\n"
            footer += r"\end{tabular}" + "\n"
            footer += r"\end{table}" + "\n"
        else:
            footer = r"\hline" + "\n"
            footer += r"\end{tabular}" + "\n"
            footer += r"\end{table}" + "\n"

        return latex + "\n".join(rows) + "\n" + footer

    def generate_cost_detail_table(
        self,
        cost_breakdown: Dict[str, float],
        title: str = "コスト詳細内訳"
    ) -> str:
        """
        Generate detailed cost breakdown table.

        Args:
            cost_breakdown: Cost breakdown dictionary
            title: Table title

        Returns:
            LaTeX table code
        """
        table_format = self.config.get("latex_settings", {}).get("table_format", "booktabs")
        number_fmt = self.config.get("latex_settings", {}).get("number_format", "{:,.0f}")

        # Header
        if table_format == "booktabs":
            latex = r"\begin{table}[h]" + "\n"
            latex += r"\centering" + "\n"
            latex += f"\\caption{{{title}}}\n"
            latex += r"\begin{tabular}{lr}" + "\n"
            latex += r"\toprule" + "\n"
            latex += r"項目 & 金額 [円] \\" + "\n"
            latex += r"\midrule" + "\n"
        else:
            latex = r"\begin{table}[h]" + "\n"
            latex += r"\centering" + "\n"
            latex += f"\\caption{{{title}}}\n"
            latex += r"\begin{tabular}{|l|r|}" + "\n"
            latex += r"\hline" + "\n"
            latex += r"項目 & 金額 [円] \\" + "\n"
            latex += r"\hline" + "\n"

        # Basic items
        rows = []
        basic_keys = ["fixed_cost", "distance_cost", "total_cost"]
        basic_labels = {
            "fixed_cost": "固定費合計",
            "distance_cost": "距離費合計",
            "total_cost": "総コスト"
        }

        for key in basic_keys:
            if key in cost_breakdown:
                label = basic_labels.get(key, key)
                value = number_fmt.format(cost_breakdown[key])
                rows.append(f"{label} & {value} \\\\")

        # Detailed breakdown
        if table_format == "booktabs":
            rows.append(r"\midrule")
        else:
            rows.append(r"\hline")

        # Variable cost details
        variable_items = {k: v for k, v in cost_breakdown.items() if k.startswith("変動費_")}
        if variable_items:
            rows.append(r"\multicolumn{2}{l}{\textbf{変動費内訳}} \\")
            for key, value in variable_items.items():
                label = "　" + key.replace("変動費_", "")
                rows.append(f"{label} & {number_fmt.format(value)} \\\\")

        # Fixed cost details
        fixed_items = {k: v for k, v in cost_breakdown.items() if k.startswith("固定費_")}
        if fixed_items:
            rows.append(r"\multicolumn{2}{l}{\textbf{固定費内訳}} \\")
            for key, value in fixed_items.items():
                label = "　" + key.replace("固定費_", "")
                rows.append(f"{label} & {number_fmt.format(value)} \\\\")

        # Footer
        if table_format == "booktabs":
            footer = r"\bottomrule" + "\n"
            footer += r"\end{tabular}" + "\n"
            footer += r"\end{table}" + "\n"
        else:
            footer = r"\hline" + "\n"
            footer += r"\end{tabular}" + "\n"
            footer += r"\end{table}" + "\n"

        return latex + "\n".join(rows) + "\n" + footer

    def generate_route_details(self, solution: Any) -> str:
        """
        Generate route details text in LaTeX format.

        Args:
            solution: FleetSolution object

        Returns:
            LaTeX formatted route details
        """
        latex = ""

        for idx, route in enumerate(solution.routes, start=1):
            latex += f"\\subsection{{車両{idx}: {route.vehicle.name}}}\n\n"
            latex += f"\\textbf{{ルート順序}}: {' → '.join(route.solution.order)}\n\n"
            latex += f"\\textbf{{走行距離}}: {route.total_distance_m / 1000:.2f} km\n\n"
            latex += f"\\textbf{{コスト}}: {route.cost:,.0f} 円\n\n"

        return latex
