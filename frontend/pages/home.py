"""Product home page."""

from __future__ import annotations

import streamlit as st

from api_client import APIClientError, KnowledgeBaseAPI
from components.cards import empty_state
from components.dashboard_card import dashboard_card
from components.document_card import render_recent_document_card


def render(api: KnowledgeBaseAPI) -> None:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="page-kicker">Enterprise AI Workspace</div>
            <h1>企业AI知识库助手</h1>
            <p>让企业资料快速变成可问答的智能知识库。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    documents = []
    backend_online = api.check_health()
    documents_error = None
    if backend_online:
        try:
            documents = api.list_documents()
        except APIClientError as exc:
            documents_error = str(exc)

    total_chunk_count = _total_chunk_count(documents)

    stat_columns = st.columns(3)
    with stat_columns[0]:
        open_documents = dashboard_card(
            "文档数量",
            len(documents),
            "当前知识库中的资料",
            "📄",
            "查看全部文档",
            "dashboard_documents",
        )
    with stat_columns[1]:
        open_search = dashboard_card(
            "知识片段数量",
            total_chunk_count,
            "全部文档的 Chunk 总数",
            "🧩",
            "体验知识检索",
            "dashboard_chunks",
        )
    with stat_columns[2]:
        open_assistant = dashboard_card(
            "AI 状态",
            "在线" if backend_online else "离线",
            "FastAPI 服务连接状态",
            "✨" if backend_online else "⚠️",
            "进入 AI 助手",
            "dashboard_ai",
        )

    if open_documents:
        _navigate_to("知识库")
    if open_search:
        _navigate_to("知识检索")
    if open_assistant:
        _navigate_to("AI助手")

    st.markdown('<div class="section-title">最近上传文档</div>', unsafe_allow_html=True)

    if not backend_online:
        st.error("后端服务未连接")
        empty_state("🔌", "无法读取文档", "请先启动 FastAPI 后端服务。")
        return

    if documents_error:
        st.error(documents_error)
        return

    if not documents:
        empty_state("📭", "知识库还是空的", "前往“知识库”页面上传第一份 DOCX 文档。")
        return

    st.caption("根据文档 metadata 中的上传时间展示最近 6 个文档。")
    recent_documents = sorted(
        documents,
        key=lambda document: str(document.get("uploaded_at") or ""),
        reverse=True,
    )[:6]
    for row_start in range(0, len(recent_documents), 3):
        columns = st.columns(3)
        for column, document in zip(columns, recent_documents[row_start:row_start + 3]):
            with column:
                render_recent_document_card(document)


def _navigate_to(page: str) -> None:
    st.session_state.navigation_target = page
    st.rerun()


def _total_chunk_count(documents: list[dict]) -> int:
    total = 0

    for document in documents:
        try:
            chunk_count = int(document.get("chunk_count") or 0)
        except (TypeError, ValueError):
            chunk_count = 0

        total += max(0, chunk_count)

    return total
