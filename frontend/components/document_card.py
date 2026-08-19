"""Product-style document cards and detail panel."""

from __future__ import annotations

import html
from typing import Any, Literal

import streamlit as st


DocumentAction = Literal["view", "delete"]


def render_library_document_card(
    document: dict[str, Any],
    key: str,
) -> DocumentAction | None:
    filename = str(document.get("filename") or "未命名文档")
    file_type = _file_type(document)
    file_size = format_file_size(_metadata_value(document, "file_size", "size"))
    category = _optional_value(document.get("category"))
    chunk_count = _optional_value(document.get("chunk_count"))
    status = _status_label(document.get("status"))

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="document-tile-title">📄 {html.escape(filename)}</div>
            <div class="document-meta">类型：{html.escape(file_type)}&nbsp;&nbsp;·&nbsp;&nbsp;大小：{html.escape(file_size)}</div>
            <div class="document-meta">分类：{html.escape(category)}&nbsp;&nbsp;·&nbsp;&nbsp;知识片段：{html.escape(chunk_count)}</div>
            <span class="document-status">● {html.escape(status)}</span>
            <div style="height:.8rem"></div>
            """,
            unsafe_allow_html=True,
        )
        view_col, delete_col = st.columns(2)
        if view_col.button("查看", key=f"view_{key}", use_container_width=True):
            return "view"
        if delete_col.button("删除", key=f"delete_{key}", use_container_width=True):
            return "delete"
    return None


def render_recent_document_card(document: dict[str, Any]) -> None:
    filename = str(document.get("filename") or "未命名文档")
    file_type = _file_type(document)
    status = _status_label(document.get("status"))
    st.markdown(
        f"""
        <div class="recent-document-card">
            <div class="recent-document-name">📄 {html.escape(filename)}</div>
            <div class="recent-document-meta">{html.escape(file_type)}</div>
            <div style="height:.45rem"></div>
            <span class="document-status">● {html.escape(status)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_document_details(document: dict[str, Any]) -> None:
    filename = str(document.get("filename") or "未命名文档")
    fields = (
        ("Document ID", _optional_value(document.get("document_id"))),
        ("文件名称", filename),
        ("文件类型", _file_type(document)),
        ("分类", _optional_value(document.get("category"))),
        ("上传时间", _optional_value(document.get("uploaded_at"))),
        ("文件大小", format_file_size(_metadata_value(document, "file_size", "size"))),
        ("Chunk 数量", _optional_value(document.get("chunk_count"))),
        ("索引状态", _status_label(document.get("status"))),
    )

    with st.container(border=True):
        header_col, close_col = st.columns([6, 1], vertical_alignment="center")
        header_col.markdown("### 文档详情")
        if close_col.button("关闭", key="close_document_details", use_container_width=True):
            st.session_state.pop("selected_document", None)
            st.rerun()

        detail_columns = st.columns(2)
        for index, (label, value) in enumerate(fields):
            with detail_columns[index % 2]:
                st.markdown(
                    f"""
                    <div style="padding:.65rem 0; border-bottom:1px solid #eef1f5;">
                        <div class="detail-label">{html.escape(label)}</div>
                        <div class="detail-value">{html.escape(str(value))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def format_file_size(value: Any) -> str:
    if value is None:
        return "暂无数据"
    try:
        size = max(0, int(value))
    except (TypeError, ValueError):
        return "暂无数据"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _file_type(document: dict[str, Any]) -> str:
    value = str(_metadata_value(document, "file_type", "type") or "").strip().lstrip(".")
    if value:
        return value.upper()
    return "暂无数据"


def _optional_value(value: Any) -> str:
    if value is None or value == "":
        return "暂无数据"
    return str(value)


def _metadata_value(document: dict[str, Any], primary: str, legacy: str) -> Any:
    value = document.get(primary)
    return value if value is not None else document.get(legacy)


def _status_label(value: Any) -> str:
    status = str(value or "").strip().lower()
    labels = {
        "indexed": "已索引",
        "processing": "处理中",
        "failed": "索引失败",
    }
    return labels.get(status, _optional_value(value))
