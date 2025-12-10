"""Profile Folium map generation with FastMarkerCluster and GeoJSON click handling."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import folium  # type: ignore
from folium.plugins import FastMarkerCluster  # type: ignore

DATA_PATH = Path("data/road_network_20251017_154630.json")
OUTPUT_DIR = Path("scripts/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NodeRecord = Tuple[float, float, str, str]


def load_node_coordinates() -> List[NodeRecord]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    nodes: List[NodeRecord] = []
    for node_id, node in data["nodes"].items():
        lat = float(node.get("lat", 0.0))
        lon = float(node.get("lon", 0.0))
        name = str(node.get("name") or node_id)
        nodes.append((lat, lon, str(node_id), name))
    return nodes


def build_fast_marker_cluster_map(nodes: Iterable[NodeRecord]) -> folium.Map:
    nodes = list(nodes)
    if not nodes:
        raise ValueError("No nodes provided")
    center_lat, center_lon, *_ = nodes[0]
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    cluster = FastMarkerCluster([[lat, lon] for lat, lon, *_ in nodes])
    cluster.add_to(fmap)
    return fmap


def _geojson_feature_collection(nodes: Iterable[NodeRecord]) -> Dict[str, object]:
    features = []
    for lat, lon, node_id, name in nodes:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"name": name, "node_id": node_id},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def build_geojson_click_map(nodes: Iterable[NodeRecord]) -> folium.Map:
    nodes = list(nodes)
    if not nodes:
        raise ValueError("No nodes provided")
    center_lat, center_lon, *_ = nodes[0]
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    geojson = folium.GeoJson(
        _geojson_feature_collection(nodes),
        name="nodes",
        zoom_on_click=False,
        tooltip=folium.features.GeoJsonTooltip(fields=["name"], aliases=["ノード"]),
    )
    geojson.add_to(fmap)
    geojson_var = geojson.get_name()
    click_script = f"""
    <script>
    if (typeof {geojson_var} !== 'undefined') {{
      {geojson_var}.eachLayer(function(layer) {{
        const nodeId = layer.feature && layer.feature.properties && layer.feature.properties.node_id;
        if (!nodeId) return;
        layer.on('click', function() {{
          const payload = {{type: 'node-click', nodeId: nodeId}};
          if (window.parent && window.parent.postMessage) {{
            window.parent.postMessage(payload, '*');
          }} else {{
            console.log('node-click', payload);
          }}
        }});
      }});
    }}
    </script>
    """
    fmap.get_root().html.add_child(folium.Element(click_script))
    return fmap


def profile(name: str, builder) -> Dict[str, float | str]:
    start = time.perf_counter()
    fmap = builder()
    build_time = time.perf_counter() - start
    output_path = OUTPUT_DIR / f"{name}.html"
    save_start = time.perf_counter()
    fmap.save(str(output_path))
    save_time = time.perf_counter() - save_start
    return {"name": name, "build_time": build_time, "save_time": save_time, "output": str(output_path)}


def main() -> None:
    nodes = load_node_coordinates()
    fast_marker_stats = profile("fast_marker_cluster", lambda: build_fast_marker_cluster_map(nodes))
    geojson_stats = profile("geojson_click", lambda: build_geojson_click_map(nodes))
    print("FastMarkerCluster:", fast_marker_stats)
    print("GeoJSON click prototype:", geojson_stats)


if __name__ == "__main__":
    main()
