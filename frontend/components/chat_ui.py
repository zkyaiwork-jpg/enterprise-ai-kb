"""Chat presentation helpers."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


WELCOME_MESSAGE = {
    "role": "assistant",
    "content": "你好，我是企业知识库助手。你可以向我询问已上传文档中的制度、流程或业务知识。",
    "sources": [],
}


def initialize_chat_history() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [WELCOME_MESSAGE.copy()]


def render_chat_history() -> None:
    for message in st.session_state.chat_messages:
        render_message(message)


def render_message(message: dict[str, Any]) -> None:
    role = message.get("role", "assistant")
    content = str(message.get("content", ""))

    if role == "user":
        spacer, bubble = st.columns([1.25, 3], vertical_alignment="top")
        with bubble:
            with st.container(border=True):
                st.markdown("**你**")
                st.markdown(content)
        return

    bubble, spacer = st.columns([3, 1.25], vertical_alignment="top")
    with bubble:
        with st.container(border=True):
            st.markdown("**✨ AI 助手**")
            st.markdown(content)
            render_sources(message.get("sources", []))


def render_sources(sources: list[Any]) -> None:
    if not sources:
        return

    st.caption("参考来源")
    chips = "".join(
        f'<span class="source-chip">📄 {html.escape(str(source))}</span>'
        for source in sources
    )
    st.markdown(chips, unsafe_allow_html=True)
