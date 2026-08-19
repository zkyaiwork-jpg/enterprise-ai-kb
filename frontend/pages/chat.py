"""RAG chat page."""

from __future__ import annotations

import streamlit as st

from api_client import APIClientError, BackendUnavailableError, KnowledgeBaseAPI
from components.cards import page_header
from components.chat_ui import initialize_chat_history, render_chat_history


def render(api: KnowledgeBaseAPI) -> None:
    page_header(
        "RAG Assistant",
        "AI 助手",
        "基于企业知识库内容回答问题，并展示答案参考来源。",
    )

    initialize_chat_history()

    action_col, note_col = st.columns([1, 5], vertical_alignment="center")
    with action_col:
        if st.button("清空对话", use_container_width=True):
            del st.session_state.chat_messages
            st.rerun()
    with note_col:
        st.caption("回答由 AI 生成，请结合来源文档核验重要信息。")

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    render_chat_history()

    question = st.chat_input("向企业知识库提问…")
    if not question:
        return

    clean_question = question.strip()
    if not clean_question:
        st.warning("请输入有效问题。")
        return

    st.session_state.chat_messages.append({"role": "user", "content": clean_question})

    with st.spinner("正在检索知识库并生成回答…"):
        try:
            result = api.chat(clean_question)
        except BackendUnavailableError:
            answer = "后端服务未连接"
            sources = []
        except APIClientError as exc:
            answer = f"请求失败：{exc}"
            sources = []
        else:
            answer = str(result.get("answer") or "暂时没有获得有效回答。")
            raw_sources = result.get("sources", [])
            sources = raw_sources if isinstance(raw_sources, list) else []

    st.session_state.chat_messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
    st.rerun()
