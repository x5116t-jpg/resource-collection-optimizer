"""
Generate LaTeX compatibility table from JSON data
"""
import json
import sys

def generate_latex_table(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    compatibility = data['compatibility']

    # Get all resources (from first vehicle)
    first_vehicle = list(compatibility.keys())[0]
    resources = list(compatibility[first_vehicle]['supports'].keys())
    vehicles = list(compatibility.keys())

    # Start LaTeX table with sidewaystable for landscape orientation
    latex = []
    latex.append(r"\begin{sidewaystable}[p]")
    latex.append(r"\centering")
    latex.append(r"\caption{車両・資源適合性マトリックス}")
    latex.append(r"\label{tab:compatibility}")
    latex.append(r"\begin{tabular}{|l|" + "c|" * len(resources) + "}")
    latex.append(r"\hline")

    # Header row
    header = r"\textbf{車両} & "
    header += " & ".join([r"\rotatebox{90}{\textbf{" + res + r"}}" for res in resources])
    header += r" \\ \hline"
    latex.append(header)

    # Data rows
    for vehicle in vehicles:
        row = [vehicle]
        for resource in resources:
            supports = compatibility[vehicle]['supports'][resource]
            req = compatibility[vehicle]['requirements'][resource]

            if supports:
                if req and req != "null":
                    # Conditional compatibility
                    cell = r"$\triangle$"
                else:
                    # Full compatibility
                    cell = r"$\circ$"
            else:
                # Not compatible
                cell = r"$\times$"

            row.append(cell)

        latex.append(" & ".join(row) + r" \\ \hline")

    latex.append(r"\end{tabular}")
    latex.append(r"\end{sidewaystable}")

    # Add legend (in normal orientation)
    latex.append(r"")
    latex.append(r"\vspace{0.5em}")
    latex.append(r"\noindent\textbf{凡例}：")
    latex.append(r"$\circ$: 適合、")
    latex.append(r"$\triangle$: 条件付き適合、")
    latex.append(r"$\times$: 不適合")

    # Add requirements table for conditional compatibility (landscape)
    latex.append(r"")
    latex.append(r"\vspace{1em}")
    latex.append(r"\noindent\textbf{条件付き適合の詳細}：")
    latex.append(r"")
    latex.append(r"\begin{table}[H]")
    latex.append(r"\centering")
    latex.append(r"\caption{条件付き適合の要件}")
    latex.append(r"\begin{tabular}{|l|l|l|}")
    latex.append(r"\hline")
    latex.append(r"\textbf{車両} & \textbf{資源} & \textbf{必要条件} \\ \hline")

    for vehicle in vehicles:
        for resource in resources:
            req = compatibility[vehicle]['requirements'][resource]
            if req and req != "null" and compatibility[vehicle]['supports'][resource]:
                latex.append(f"{vehicle} & {resource} & {req} " + r"\\ \hline")

    latex.append(r"\end{tabular}")
    latex.append(r"\end{table}")

    return "\n".join(latex)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_compatibility_table.py <json_path>")
        sys.exit(1)

    json_path = sys.argv[1]
    latex_table = generate_latex_table(json_path)
    print(latex_table)
