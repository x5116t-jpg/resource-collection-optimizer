"""Export controls for Streamlit UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def render_export_controls(persistence_service: Any) -> None:
    try:
        import streamlit as st  # type: ignore
    except ModuleNotFoundError:
        return

    st.sidebar.subheader("エクスポート")
    filename = st.sidebar.text_input("ファイル名", value="scenario")
    if st.sidebar.button("JSONに保存"):
        persistence_service.save_json(Path(filename))
    if st.sidebar.button("CSVに保存"):
        persistence_service.save_csv(Path(filename))
