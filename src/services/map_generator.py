"""Map generation module for report export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False


class MapGenerator:
    """Generates maps for report export."""

    def __init__(self, config_manager):
        """
        Initialize map generator.

        Args:
            config_manager: ReportConfigManager instance
        """
        if not FOLIUM_AVAILABLE:
            raise ImportError("folium is required for map generation. Install with: pip install folium")

        self.config = config_manager.config

    def create_conditions_map(
        self,
        depot: Dict,
        sink: Dict,
        pickups: List[Dict]
    ) -> folium.Map:
        """
        Create conditions map showing depot, sink, and pickup points.

        Args:
            depot: Depot information {"id": str, "lat": float, "lon": float, "label": str}
            sink: Sink information
            pickups: List of pickup information

        Returns:
            folium.Map object
        """
        config = self.config.get("map_settings", {}).get("conditions_map", {})

        # Calculate center coordinates
        all_points = [depot, sink] + pickups
        center_lat, center_lon = self._calculate_center(all_points)

        # Create folium map
        fmap = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=config.get("zoom_start", 13),
            tiles=config.get("tile_layer", "OpenStreetMap")
        )

        # Auto-zoom if enabled
        if config.get("auto_zoom", True):
            bounds = self._calculate_bounds(all_points)
            fmap.fit_bounds(bounds)

        # Get colors and sizes
        colors = config.get("colors", {})
        sizes = config.get("marker_sizes", {})

        # Add depot marker
        self._add_marker(
            fmap,
            depot,
            color=colors.get("depot", "green"),
            size=sizes.get("depot", 8),
            icon_type="depot",
            label_prefix="車庫"
        )

        # Add sink marker
        self._add_marker(
            fmap,
            sink,
            color=colors.get("sink", "red"),
            size=sizes.get("sink", 8),
            icon_type="sink",
            label_prefix="集積場所"
        )

        # Add pickup markers
        for pickup in pickups:
            resource = pickup.get("resource_type", pickup.get("kind", ""))
            qty = pickup.get("quantity_kg", pickup.get("qty", 0))

            popup_text = f"<b>回収地点</b><br>{pickup.get('label', pickup['id'])}"
            if resource:
                popup_text += f"<br>資源: {resource}"
            if qty > 0:
                popup_text += f"<br>量: {qty} kg"

            tooltip_text = f"{resource} ({qty}kg)" if resource and qty > 0 else "回収地点"

            folium.CircleMarker(
                location=[pickup["lat"], pickup["lon"]],
                radius=sizes.get("pickup", 6),
                color=colors.get("pickup", "blue"),
                fill=True,
                fill_color=colors.get("pickup", "blue"),
                fill_opacity=0.7,
                popup=popup_text,
                tooltip=tooltip_text
            ).add_to(fmap)

        return fmap

    def create_route_map(
        self,
        graph: Any,
        solution: Any,
        depot: Dict,
        sink: Dict,
        title: str = "ルート地図"
    ) -> folium.Map:
        """
        Create route map showing optimized routes.

        Args:
            graph: NetworkX graph
            solution: FleetSolution object
            depot: Depot information
            sink: Sink information
            title: Map title

        Returns:
            folium.Map object
        """
        try:
            from .route_reconstruction import reconstruct_paths
        except ImportError:
            from services.route_reconstruction import reconstruct_paths

        config = self.config.get("map_settings", {}).get("route_map", {})

        # Collect all points
        all_points = [depot, sink]

        # Calculate center
        center_lat, center_lon = self._calculate_center(all_points)

        # Create map
        fmap = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=config.get("zoom_start", 12),
            tiles=config.get("tile_layer", "OpenStreetMap")
        )

        # Draw routes
        route_color = config.get("route_color", "#0066CC")
        route_weight = config.get("route_weight", 4)
        route_opacity = config.get("route_opacity", 0.8)

        for idx, route in enumerate(solution.routes):
            polylines = reconstruct_paths(graph, route.solution.order)
            for segment in polylines:
                if segment:
                    folium.PolyLine(
                        segment,
                        color=route_color,
                        weight=route_weight,
                        opacity=route_opacity,
                        popup=f"車両: {route.vehicle.name}"
                    ).add_to(fmap)

        # Add markers (depot, sink, pickups)
        colors = config.get("colors", self.config["map_settings"]["conditions_map"].get("colors", {}))
        sizes = config.get("marker_sizes", self.config["map_settings"]["conditions_map"].get("marker_sizes", {}))

        self._add_marker(fmap, depot, colors.get("depot", "green"), sizes.get("depot", 8), "depot", "車庫")
        self._add_marker(fmap, sink, colors.get("sink", "red"), sizes.get("sink", 8), "sink", "集積場所")

        # Auto-zoom
        if config.get("auto_zoom", True):
            bounds = self._calculate_bounds(all_points)
            fmap.fit_bounds(bounds)

        return fmap

    def save_map(
        self,
        fmap: folium.Map,
        output_path: Path,
        save_html: bool = True,
        save_image: bool = True
    ) -> None:
        """
        Save map to HTML and/or image file.

        Args:
            fmap: folium.Map object
            output_path: Output path without extension
            save_html: Whether to save HTML version
            save_image: Whether to save image version
        """
        try:
            from ..utils.html_to_image import convert_html_to_png
        except ImportError:
            from utils.html_to_image import convert_html_to_png

        # Save HTML
        if save_html:
            html_path = output_path.with_suffix(".html")
            fmap.save(str(html_path))

        # Save image
        if save_image:
            html_path = output_path.with_suffix(".html")
            if not html_path.exists():
                fmap.save(str(html_path))

            png_path = output_path.with_suffix(".png")

            # Determine which map type this is
            map_type = "conditions_map" if "conditions" in output_path.name else "route_map"
            config = self.config.get("map_settings", {}).get(map_type, {})

            width = config.get("width_px", 1200)
            height = config.get("height_px", 900)

            try:
                convert_html_to_png(
                    str(html_path),
                    str(png_path),
                    width=width,
                    height=height
                )
            except Exception as e:
                print(f"Warning: Failed to convert HTML to PNG: {e}")
                print("HTML file saved, but PNG conversion skipped.")

    def _add_marker(
        self,
        fmap: folium.Map,
        point: Dict,
        color: str,
        size: int,
        icon_type: str,
        label_prefix: str
    ) -> None:
        """Add a marker to the map."""
        label = point.get('label', point['id'])
        popup_text = f"<b>{label_prefix}</b><br>{label}"

        folium.CircleMarker(
            location=[point["lat"], point["lon"]],
            radius=size,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=popup_text,
            tooltip=label_prefix
        ).add_to(fmap)

    def _calculate_center(self, points: List[Dict]) -> Tuple[float, float]:
        """Calculate center coordinates from list of points."""
        lats = [p["lat"] for p in points if "lat" in p and p["lat"] is not None]
        lons = [p["lon"] for p in points if "lon" in p and p["lon"] is not None]

        if not lats or not lons:
            return (35.6762, 139.6503)  # Default to Tokyo

        return sum(lats) / len(lats), sum(lons) / len(lons)

    def _calculate_bounds(self, points: List[Dict]) -> List[List[float]]:
        """Calculate bounds from list of points."""
        lats = [p["lat"] for p in points if "lat" in p and p["lat"] is not None]
        lons = [p["lon"] for p in points if "lon" in p and p["lon"] is not None]

        if not lats or not lons:
            return [[35.6, 139.6], [35.7, 139.7]]

        return [[min(lats), min(lons)], [max(lats), max(lons)]]
