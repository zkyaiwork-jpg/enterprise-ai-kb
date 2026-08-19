"""Semantic retrieval exploration page."""

from __future__ import annotations

import streamlit as st

from api_client import APIClientError, BackendUnavailableError, KnowledgeBaseAPI
from components.cards import empty_state, page_header, search_result_card


def render(api: KnowledgeBaseAPI) -> None:
    page_header(
        "Semantic Retrieval",
        "知识检索",
        "查看问题如何命中知识片段，直观展示 RAG 的语义检索过程。",
    )

    with st.form("semantic_search_form", clear_on_submit=False):
        query = st.text_input(
            "检索内容",
            placeholder="例如：员工请假需要经过哪些审批？",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("🔎 开始检索", type="primary")

    if not submitted:
        empty_state("🔎", "探索企业知识", "输入问题或关键词，查看最相关的知识片段和检索距离。")
        return

    clean_query = query.strip()
    if not clean_query:
        st.warning("请输入检索关键词。")
        return

    with st.spinner("正在计算语义相似度…"):
        try:
            results = api.search(clean_query)
        except BackendUnavailableError:
            st.error("后端服务未连接")
            return
        except APIClientError as exc:
            st.error(f"检索失败：{exc}")
            return

    if not results:
        empty_state("🗂️", "没有找到相关内容", "尝试换一种表达，或先向知识库上传相关文档。")
        return

    st.markdown(f'<div class="section-title">检索结果 · {len(results)} 个知识片段</div>', unsafe_allow_html=True)
    for index, result in enumerate(results, start=1):
        search_result_card(result, index)
