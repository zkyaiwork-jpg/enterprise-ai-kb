"""Sidebar navigation and service status."""

from __future__ import annotations

import streamlit as st

from api_client import KnowledgeBaseAPI


NAVIGATION = ["首页", "知识库", "AI助手", "知识检索"]
NAV_ICONS = {
    "首页": "🏠",
    "知识库": "📚",
    "AI助手": "✨",
    "知识检索": "🔎",
}


def render_sidebar(api: KnowledgeBaseAPI) -> str:
    navigation_target = st.session_state.pop("navigation_target", None)
    if navigation_target in NAVIGATION:
        st.session_state.active_page = navigation_target

    with st.sidebar:
        st.markdown(
            """
            <div style="padding: .7rem .15rem 1.25rem;">
                <div style="font-size:1.45rem; font-weight:750; letter-spacing:-.03em;">🧠 企业AI知识库助手</div>
                <div style="font-size:.78rem; color:#98a2b3; margin-top:.42rem;">Enterprise Knowledge Copilot</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_label = st.radio(
            "主导航",
            options=NAVIGATION,
            format_func=lambda item: f"{NAV_ICONS[item]}  {item}",
            label_visibility="collapsed",
            key="active_page",
        )

        st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
        is_online = api.check_health()
        status_text = "后端服务已连接" if is_online else "后端服务未连接"
        status_color = "#75d8ae" if is_online else "#fda29b"
        st.markdown(
            f"""
            <div style="border-top:1px solid #25324a; padding-top:1rem;">
                <div style="font-size:.78rem; color:{status_color};">●&nbsp;&nbsp;{status_text}</div>
                <div style="font-size:.7rem; color:#667085; margin-top:.35rem;">{api.base_url}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected_label
