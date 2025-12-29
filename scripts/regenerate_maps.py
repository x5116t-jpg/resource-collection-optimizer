"""Script to regenerate maps from existing report data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.map_generator import MapGenerator
from services.report_config_manager import ReportConfigManager


def regenerate_maps(export_dir: Path = Path("claudedocs/report_export")) -> None:
    """
    Regenerate maps from report_data.json using current configuration.

    Args:
        export_dir: Directory containing report data
    """
    export_dir = Path(export_dir)
    data_path = export_dir / "report_data.json"

    if not data_path.exists():
        print(f"❌ Error: {data_path} not found")
        print(f"Please run the report export from the Streamlit app first.")
        return

    print(f"📂 Loading data from: {data_path}")

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Initialize managers
    config_manager = ReportConfigManager(export_dir / "report_config.json")
    map_generator = MapGenerator(config_manager)

    maps_dir = export_dir / "maps"
    maps_dir.mkdir(exist_ok=True, parents=True)

    # Regenerate conditions map
    print("\n🗺️  Regenerating conditions map...")
    try:
        conditions_map = map_generator.create_conditions_map(
            depot=data["input_conditions"]["depot"],
            sink=data["input_conditions"]["sink"],
            pickups=data["input_conditions"]["pickups"]
        )
        map_generator.save_map(
            conditions_map,
            maps_dir / "conditions",
            save_html=True,
            save_image=True
        )
        print("   ✅ conditions.png and conditions.html created")
    except Exception as e:
        print(f"   ❌ Failed to regenerate conditions map: {e}")

    # Note: Route map regeneration requires the graph object which is not in JSON
    print("\n⚠️  Note: Route maps cannot be regenerated from JSON alone")
    print("   They require the original network graph.")
    print("   To regenerate route maps, please re-run the optimization in the Streamlit app.")

    print("\n✅ Map regeneration complete!")
    print(f"\n📁 Output directory: {maps_dir}")
    print(f"\n💡 Tip: Open the HTML files in a browser to preview the maps")
    print(f"   Then adjust settings in {export_dir / 'report_config.json'}")
    print(f"   And run this script again to regenerate with new settings.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Regenerate maps from report data")
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=Path("claudedocs/report_export"),
        help="Directory containing report data (default: claudedocs/report_export)"
    )

    args = parser.parse_args()

    regenerate_maps(args.export_dir)
