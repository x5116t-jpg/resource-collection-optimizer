"""Report configuration management module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class ReportConfigManager:
    """Manages report export configuration with validation."""

    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "map_settings": {
            "conditions_map": {
                "zoom_start": 13,
                "auto_zoom": True,
                "width_px": 1200,
                "height_px": 900,
                "dpi": 150,
                "tile_layer": "OpenStreetMap",
                "colors": {
                    "depot": "green",
                    "pickup": "blue",
                    "sink": "red"
                },
                "marker_sizes": {
                    "depot": 8,
                    "pickup": 6,
                    "sink": 8
                }
            },
            "route_map": {
                "zoom_start": 12,
                "auto_zoom": True,
                "width_px": 1400,
                "height_px": 1000,
                "dpi": 150,
                "tile_layer": "OpenStreetMap",
                "route_color": "#0066CC",
                "route_weight": 4,
                "route_opacity": 0.8
            }
        },
        "latex_settings": {
            "table_format": "booktabs",
            "number_format": "{:,.0f}",
            "float_precision": 2
        },
        "output_settings": {
            "image_format": "png",
            "include_html": True,
            "generate_latex": True
        }
    }

    def __init__(self, config_path: Path):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                return self._merge_config(self.DEFAULT_CONFIG, user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                print("Using default configuration")
                return self.DEFAULT_CONFIG.copy()
        else:
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()

    def _merge_config(self, base: Dict, override: Dict) -> Dict:
        """
        Recursively merge configuration dictionaries.

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def _save_config(self, config: Dict) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration to save
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def save(self) -> None:
        """Save current configuration to file."""
        self._save_config(self.config)

    def validate(self) -> bool:
        """
        Validate configuration values.

        Returns:
            True if configuration is valid
        """
        try:
            # Zoom level validation
            conditions_zoom = self.config["map_settings"]["conditions_map"]["zoom_start"]
            route_zoom = self.config["map_settings"]["route_map"]["zoom_start"]
            assert 1 <= conditions_zoom <= 18, f"conditions_map zoom_start must be 1-18, got {conditions_zoom}"
            assert 1 <= route_zoom <= 18, f"route_map zoom_start must be 1-18, got {route_zoom}"

            # Image dimensions validation
            for map_type in ["conditions_map", "route_map"]:
                width = self.config["map_settings"][map_type]["width_px"]
                height = self.config["map_settings"][map_type]["height_px"]
                assert width > 0, f"{map_type} width must be positive, got {width}"
                assert height > 0, f"{map_type} height must be positive, got {height}"

            # DPI validation
            for map_type in ["conditions_map", "route_map"]:
                dpi = self.config["map_settings"][map_type]["dpi"]
                assert dpi > 0, f"{map_type} dpi must be positive, got {dpi}"

            return True

        except (KeyError, AssertionError) as e:
            print(f"Configuration validation error: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Path to configuration key (e.g., "map_settings.conditions_map.zoom_start")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
