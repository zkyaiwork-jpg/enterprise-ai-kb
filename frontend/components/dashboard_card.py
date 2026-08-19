"""Interactive metric cards used by the product dashboard."""

from __future__ import annotations

import html

import streamlit as st


def dashboard_card(
    label: str,
    value: str | int,
    hint: str,
    icon: str,
    action_label: str,
    key: str,
) -> bool:
    """Render a metric card with a clear navigation action."""
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="dashboard-card-copy">
                <div class="stat-label">{html.escape(icon)}&nbsp;&nbsp;{html.escape(label)}</div>
                <div class="stat-value">{html.escape(str(value))}</div>
                <div class="stat-hint">{html.escape(hint)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return st.button(
            f"{action_label}  →",
            key=key,
            type="tertiary",
            use_container_width=True,
        )
