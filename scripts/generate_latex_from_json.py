"""Script to generate LaTeX section from report JSON data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.latex_generator import LaTeXGenerator
from services.report_config_manager import ReportConfigManager


def generate_latex_section(
    export_dir: Path = Path("claudedocs/report_export"),
    output_dir: Path = Path("docs/report_04/generated")
) -> None:
    """
    Generate LaTeX section from report data.

    Args:
        export_dir: Directory containing report data
        output_dir: Directory for generated LaTeX files
    """
    export_dir = Path(export_dir)
    output_dir = Path(output_dir)
    data_path = export_dir / "report_data.json"

    if not data_path.exists():
        print(f"❌ Error: {data_path} not found")
        print("Please run the report export from the Streamlit app first.")
        return

    print(f"📂 Loading data from: {data_path}")

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize LaTeX generator
    config_manager = ReportConfigManager(export_dir / "report_config.json")
    latex_gen = LaTeXGenerator(config_manager)

    print("\n📝 Generating LaTeX files...")

    # Generate main section file
    section_content = r"""\section{計算結果}

\subsection{計算条件}

計算に使用した条件を表\ref{tab:input_conditions}に示す。

\input{generated/input_conditions}

\begin{figure}[h]
\centering
\includegraphics[width=0.85\textwidth]{../../claudedocs/report_export/maps/conditions.png}
\caption{車庫・回収地点・集積場所の配置}
\label{fig:conditions_map}
\end{figure}

\subsection{コスト比較}

最適解とeCOM-10代替案のコスト比較を表\ref{tab:cost_comparison}に示す。

\input{generated/cost_comparison}

\subsection{最適ルート}

最適化により得られたルートを図\ref{fig:optimal_route}に示す。

\begin{figure}[h]
\centering
\includegraphics[width=0.9\textwidth]{../../claudedocs/report_export/maps/optimal_route.png}
\caption{最適ルート}
\label{fig:optimal_route}
\end{figure}

\subsection{ルート詳細}

\input{generated/route_details}

\subsection{コスト詳細}

\input{generated/optimal_cost_detail}
"""

    # Add eCOM-10 section if available
    if data.get("ecom10_solution") and data["ecom10_solution"].get("feasible"):
        section_content += r"""
\subsection{eCOM-10代替案}

eCOM-10を使用した場合のルートを図\ref{fig:ecom10_route}に示す。

\begin{figure}[h]
\centering
\includegraphics[width=0.9\textwidth]{../../claudedocs/report_export/maps/ecom10_route.png}
\caption{eCOM-10ルート}
\label{fig:ecom10_route}
\end{figure}

\input{generated/ecom10_cost_detail}
"""

    # Save main section file
    section_path = output_dir / "section_results.tex"
    section_path.write_text(section_content, encoding="utf-8")
    print(f"   ✅ {section_path}")

    # Copy LaTeX files from export directory
    latex_source_dir = export_dir / "latex"
    if latex_source_dir.exists():
        for tex_file in latex_source_dir.glob("*.tex"):
            dest_file = output_dir / tex_file.name
            dest_file.write_text(tex_file.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"   ✅ {dest_file}")

    print("\n✅ LaTeX generation complete!")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\n💡 Next steps:")
    print(f"   1. Add the following to docs/report_04/main.tex:")
    print(f"      \\input{{generated/section_results}}")
    print(f"   2. Compile: cd docs/report_04 && cmd /c compile.bat")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate LaTeX section from report data")
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=Path("claudedocs/report_export"),
        help="Directory containing report data"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/report_04/generated"),
        help="Directory for generated LaTeX files"
    )

    args = parser.parse_args()

    generate_latex_section(args.export_dir, args.output_dir)
