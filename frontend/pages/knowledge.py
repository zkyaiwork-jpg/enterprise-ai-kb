"""Knowledge-base document management page."""

from __future__ import annotations

import streamlit as st

from api_client import APIClientError, BackendUnavailableError, KnowledgeBaseAPI
from components.cards import empty_state
from components.document_card import (
    render_document_details,
    render_library_document_card,
)


CATEGORY_ORDER = ["公司制度", "项目资料", "技术文档", "AI学习", "未分类", "其他"]
CATEGORY_ICONS = {
    "全部文档": "📚",
    "公司制度": "📁",
    "项目资料": "📁",
    "技术文档": "📁",
    "AI学习": "📁",
    "未分类": "📁",
    "其他": "📁",
}


def render(api: KnowledgeBaseAPI) -> None:
    title_col, upload_col = st.columns([5, 1.25], vertical_alignment="bottom")
    with title_col:
        st.markdown('<div class="page-kicker">Knowledge Base</div>', unsafe_allow_html=True)
        st.title("知识库")
        st.markdown('<div class="page-subtitle">管理企业文档和AI知识来源。</div>', unsafe_allow_html=True)
    with upload_col:
        if st.button("＋ 上传文档", type="primary", use_container_width=True):
            st.session_state.show_upload_panel = not st.session_state.get("show_upload_panel", False)

    if st.session_state.get("show_upload_panel", False):
        _render_upload_panel(api)

    try:
        documents = api.list_documents()
    except BackendUnavailableError:
        st.error("后端服务未连接")
        empty_state("🔌", "无法加载文档", "请确认 FastAPI 已在 8000 端口启动。")
        return
    except APIClientError as exc:
        st.error(str(exc))
        return

    category_col, content_col = st.columns([1.25, 4.75], gap="large")
    with category_col:
        selected_category = _render_categories(documents)
    with content_col:
        _render_document_workspace(api, documents, selected_category)


def _render_upload_panel(api: KnowledgeBaseAPI) -> None:
    with st.container(border=True):
        st.markdown("### 上传新文档")
        st.caption("当前支持 DOCX 格式。上传后将自动完成解析、切分和向量化。")
        uploaded_file = st.file_uploader(
            "选择 DOCX 文档",
            type=["docx"],
            accept_multiple_files=False,
            label_visibility="collapsed",
        )
        upload_clicked = st.button(
            "⬆️ 上传并构建知识库",
            type="primary",
            disabled=uploaded_file is None,
        )

        if upload_clicked and uploaded_file is not None:
            with st.spinner("正在解析文档并生成知识向量…"):
                try:
                    result = api.upload_document(uploaded_file)
                except BackendUnavailableError:
                    st.error("后端服务未连接")
                except APIClientError as exc:
                    st.error(f"上传失败：{exc}")
                else:
                    chunks = result.get("chunks", [])
                    chunk_count = len(chunks) if isinstance(chunks, list) else 0
                    vector_count = result.get("vector_count", 0)
                    st.success("文档已成功加入知识库")
                    success_columns = st.columns(3)
                    success_columns[0].metric("文件名称", result.get("filename", uploaded_file.name))
                    success_columns[1].metric("文本片段", chunk_count)
                    success_columns[2].metric("向量数量", vector_count)
                    st.session_state.show_upload_panel = False


def _render_categories(documents: list[dict]) -> str:
    st.markdown("**文档分类**")
    backend_categories = {
        _document_category(document)
        for document in documents
    }
    ordered_categories = [
        category
        for category in CATEGORY_ORDER
        if category in backend_categories
    ]
    ordered_categories.extend(
        sorted(backend_categories.difference(CATEGORY_ORDER))
    )
    categories = ["全部文档", *ordered_categories]

    counts = {category: 0 for category in categories}
    counts["全部文档"] = len(documents)
    for document in documents:
        category = _document_category(document)
        counts[category] += 1

    return st.radio(
        "文档分类",
        categories,
        format_func=lambda category: f"{CATEGORY_ICONS.get(category, '📁')}  {category}  ·  {counts[category]}",
        label_visibility="collapsed",
        key="knowledge_category",
    )


def _render_document_workspace(
    api: KnowledgeBaseAPI,
    documents: list[dict],
    selected_category: str,
) -> None:
    filtered_documents = [
        document
        for document in documents
        if selected_category == "全部文档"
        or _document_category(document) == selected_category
    ]

    header_col, count_col = st.columns([4, 1], vertical_alignment="center")
    header_col.markdown(f"### {selected_category}")
    count_col.markdown(f"<div style='text-align:right;color:#667085'>{len(filtered_documents)} 份文档</div>", unsafe_allow_html=True)

    if not filtered_documents:
        empty_state("📂", "该分类暂无文档", "上传文档并设置分类后，文档会显示在这里。")
        return

    for row_start in range(0, len(filtered_documents), 2):
        columns = st.columns(2)
        for index, (column, document) in enumerate(
            zip(columns, filtered_documents[row_start:row_start + 2]),
            start=row_start,
        ):
            filename = str(document.get("filename") or "")
            with column:
                action = render_library_document_card(document, key=f"document_{index}_{filename}")
            if action == "view":
                st.session_state.selected_document = document
            elif action == "delete":
                _delete_document(api, filename)

    selected_document = st.session_state.get("selected_document")
    if selected_document:
        st.markdown('<div class="section-title">文档信息</div>', unsafe_allow_html=True)
        render_document_details(selected_document)


def _delete_document(api: KnowledgeBaseAPI, filename: str) -> None:
    try:
        result = api.delete_document(filename)
    except BackendUnavailableError:
        st.error("后端服务未连接")
    except APIClientError as exc:
        st.error(f"删除失败：{exc}")
    else:
        selected = st.session_state.get("selected_document", {})
        if selected.get("filename") == filename:
            st.session_state.pop("selected_document", None)
        if result.get("file_deleted"):
            st.success(f"已删除：{filename}")
        else:
            st.warning(f"向量删除请求已完成，但本地文件不存在：{filename}")
        st.rerun()


def _document_category(document: dict) -> str:
    category = document.get("category")

    if category is None or not str(category).strip():
        return "未分类"

    return str(category).strip()
