"""Script to adjust map settings and regenerate maps."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def adjust_map_settings(
    export_dir: Path = Path("claudedocs/report_export"),
    zoom_start: Optional[int] = None,
    width_px: Optional[int] = None,
    height_px: Optional[int] = None,
    route_color: Optional[str] = None,
    tile_layer: Optional[str] = None
) -> None:
    """
    Adjust map settings in configuration file.

    Args:
        export_dir: Directory containing report data
        zoom_start: Zoom level (1-18)
        width_px: Image width in pixels
        height_px: Image height in pixels
        route_color: Route line color (hex code)
        tile_layer: Map tile layer
    """
    config_path = Path(export_dir) / "report_config.json"

    if not config_path.exists():
        print(f"❌ Error: {config_path} not found")
        print("Please run the report export from the Streamlit app first.")
        return

    print(f"📂 Loading configuration from: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Apply adjustments
    changes = []

    if zoom_start is not None:
        if 1 <= zoom_start <= 18:
            config["map_settings"]["conditions_map"]["zoom_start"] = zoom_start
            config["map_settings"]["route_map"]["zoom_start"] = zoom_start - 1
            changes.append(f"zoom_start: {zoom_start}")
        else:
            print(f"⚠️  Warning: zoom_start must be 1-18, got {zoom_start}, skipping")

    if width_px is not None:
        if width_px > 0:
            config["map_settings"]["conditions_map"]["width_px"] = width_px
            config["map_settings"]["route_map"]["width_px"] = width_px
            changes.append(f"width_px: {width_px}")
        else:
            print(f"⚠️  Warning: width_px must be positive, got {width_px}, skipping")

    if height_px is not None:
        if height_px > 0:
            config["map_settings"]["conditions_map"]["height_px"] = height_px
            config["map_settings"]["route_map"]["height_px"] = height_px
            changes.append(f"height_px: {height_px}")
        else:
            print(f"⚠️  Warning: height_px must be positive, got {height_px}, skipping")

    if route_color is not None:
        config["map_settings"]["route_map"]["route_color"] = route_color
        changes.append(f"route_color: {route_color}")

    if tile_layer is not None:
        valid_tiles = ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter", "Stamen Terrain"]
        if tile_layer in valid_tiles:
            config["map_settings"]["conditions_map"]["tile_layer"] = tile_layer
            config["map_settings"]["route_map"]["tile_layer"] = tile_layer
            changes.append(f"tile_layer: {tile_layer}")
        else:
            print(f"⚠️  Warning: tile_layer must be one of {valid_tiles}, got {tile_layer}, skipping")

    # Save updated configuration
    if changes:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Configuration updated:")
        for change in changes:
            print(f"   • {change}")

        print(f"\n💡 Next step: Run the following command to regenerate maps:")
        print(f"   python scripts/regenerate_maps.py")
    else:
        print("\n⚠️  No changes made to configuration")

    print(f"\n📁 Configuration file: {config_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Adjust map settings")
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=Path("claudedocs/report_export"),
        help="Directory containing report data"
    )
    parser.add_argument(
        "--zoom",
        type=int,
        help="Zoom level (1-18)"
    )
    parser.add_argument(
        "--width",
        type=int,
        help="Image width in pixels"
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Image height in pixels"
    )
    parser.add_argument(
        "--route-color",
        type=str,
        help="Route line color (hex code, e.g., #FF6600)"
    )
    parser.add_argument(
        "--tile-layer",
        type=str,
        choices=["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter", "Stamen Terrain"],
        help="Map tile layer"
    )

    args = parser.parse_args()

    adjust_map_settings(
        export_dir=args.export_dir,
        zoom_start=args.zoom,
        width_px=args.width,
        height_px=args.height,
        route_color=args.route_color,
        tile_layer=args.tile_layer
    )
