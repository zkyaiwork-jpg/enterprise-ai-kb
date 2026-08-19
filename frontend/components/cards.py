"""Reusable card components for the Streamlit UI."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


def page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="page-kicker">{html.escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="page-subtitle">{html.escape(subtitle)}</div>', unsafe_allow_html=True)


def stat_card(label: str, value: str | int, hint: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{html.escape(icon)}&nbsp;&nbsp;{html.escape(label)}</div>
            <div class="stat-value">{html.escape(str(value))}</div>
            <div class="stat-hint">{html.escape(hint)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def document_card(document: dict[str, Any], key: str, show_delete: bool = True) -> bool:
    filename = str(document.get("filename", "未命名文档"))
    file_type = str(document.get("type") or ".docx").upper().lstrip(".")
    size = _format_file_size(document.get("size", 0))

    with st.container(border=True):
        if not show_delete:
            st.markdown(f"**📄 {filename}**")
            st.caption(f"{file_type} · {size} · 🟢 已存储")
            return False

        info_col, action_col = st.columns([7, 1.35], vertical_alignment="center")
        with info_col:
            st.markdown(f"**📄 {filename}**")
            st.caption(f"{file_type} · {size} · 🟢 已存储")
        with action_col:
            return st.button("删除", key=key, type="secondary", use_container_width=True)


def search_result_card(result: dict[str, Any], index: int) -> None:
    filename = str(result.get("filename", "未知来源"))
    content = str(result.get("content", "")).strip()
    distance = result.get("distance")
    distance_text = f"{float(distance):.4f}" if isinstance(distance, (int, float)) else "未知"

    with st.container(border=True):
        source_col, distance_col = st.columns([5, 1.3], vertical_alignment="center")
        with source_col:
            st.markdown(f"**📄 {filename}**")
            st.caption(f"检索结果 {index}")
        with distance_col:
            st.markdown(
                f'<div style="text-align:right"><span class="search-distance">距离 {distance_text}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown(content or "_该结果没有可展示的文本片段。_")
        st.caption("Distance 越低，表示语义相关度越高")


def empty_state(icon: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            <div style="font-size:1.7rem; margin-bottom:.5rem;">{html.escape(icon)}</div>
            <div style="font-weight:700; color:#344054; margin-bottom:.25rem;">{html.escape(title)}</div>
            <div style="font-size:.88rem;">{html.escape(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_file_size(value: Any) -> str:
    try:
        size = max(0, int(value))
    except (TypeError, ValueError):
        return "未知大小"

    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
