"""Pickup attribute table components."""

from __future__ import annotations

from typing import Any


def render_pickup_table(registry: Any) -> None:
    try:
        import streamlit as st  # type: ignore
    except ModuleNotFoundError:
        return

    st.subheader("回収地点属性")
    pickups = registry.list_points() if hasattr(registry, "list_points") else []
    st.table([
        {
            "id": p.id if hasattr(p, "id") else p.get("id"),
            "lat": getattr(p, "lat", None),
            "lon": getattr(p, "lon", None),
        }
        for p in pickups
    ])
