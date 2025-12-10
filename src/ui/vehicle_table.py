"""Vehicle table rendering utilities."""

from __future__ import annotations

from typing import Any


def render_vehicle_table(catalog: Any) -> None:
    try:
        import streamlit as st  # type: ignore
    except ModuleNotFoundError:
        return

    st.subheader("車種候補")
    vehicles = catalog.list_vehicles() if hasattr(catalog, "list_vehicles") else []
    st.table([
        {
            "name": v.name,
            "capacity_kg": v.capacity_kg,
            "fixed_cost": v.fixed_cost,
            "per_km_cost": v.per_km_cost,
        }
        for v in vehicles
    ])
