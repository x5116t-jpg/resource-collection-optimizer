"""Result presentation components."""

from __future__ import annotations

from typing import Any, Callable, Optional


def render_results(solution: Any, download_handler: Optional[Callable[[str], None]] = None) -> None:
    try:
        import streamlit as st  # type: ignore
    except ModuleNotFoundError:
        return

    st.subheader("最適化結果")
    if not solution or not getattr(solution, "is_feasible", False):
        st.info("結果がありません。")
        return

    st.metric("総距離 (km)", f"{solution.total_distance_m / 1000:.2f}")
    st.metric("総コスト (円)", f"{solution.cost_breakdown.get('total_cost', 0):,.0f}")
    st.write("ルート順:", " → ".join(solution.order))

    if download_handler:
        if st.button("結果をエクスポート"):
            download_handler("export")
