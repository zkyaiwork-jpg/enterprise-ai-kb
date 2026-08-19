"""Streamlit entry point for the Enterprise AI Knowledge Base Assistant."""

from pathlib import Path
import sys

import streamlit as st


FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from api_client import KnowledgeBaseAPI  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402
from pages import chat, home, knowledge, search  # noqa: E402


st.set_page_config(
    page_title="企业AI知识库助手",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --kb-primary: #315b9a;
        --kb-primary-soft: #edf3fb;
        --kb-ink: #172033;
        --kb-muted: #667085;
        --kb-border: #e4e9f1;
        --kb-surface: #ffffff;
    }

    .stApp {
        background: #f7f9fc;
        color: var(--kb-ink);
    }

    [data-testid="stHeader"] {
        background: rgba(247, 249, 252, 0.88);
        backdrop-filter: blur(12px);
    }

    [data-testid="stSidebar"] {
        background: #101828;
        border-right: 1px solid #25324a;
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 0.48rem 0.65rem;
        border-radius: 0.65rem;
        margin-bottom: 0.22rem;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.08);
    }

    [data-testid="stSidebarNav"] {
        display: none;
    }

    .block-container {
        max-width: 1220px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: var(--kb-ink);
        letter-spacing: -0.025em;
    }

    .page-kicker {
        color: var(--kb-primary);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    .page-subtitle {
        color: var(--kb-muted);
        font-size: 1.02rem;
        line-height: 1.7;
        margin: -0.45rem 0 1.8rem;
    }

    .hero-panel {
        border: 1px solid var(--kb-border);
        background: linear-gradient(135deg, #ffffff 15%, #f1f6fd 100%);
        border-radius: 1.1rem;
        padding: 2rem 2.1rem;
        margin-bottom: 1.35rem;
        box-shadow: 0 12px 35px rgba(31, 51, 81, 0.06);
    }

    .hero-panel h1 {
        font-size: clamp(2rem, 4vw, 3.15rem);
        margin: 0 0 0.75rem;
    }

    .hero-panel p {
        color: var(--kb-muted);
        font-size: 1.08rem;
        margin: 0;
    }

    .stat-card {
        min-height: 138px;
        border: 1px solid var(--kb-border);
        background: var(--kb-surface);
        border-radius: 1rem;
        padding: 1.25rem 1.3rem;
        box-shadow: 0 8px 24px rgba(31, 51, 81, 0.045);
    }

    .dashboard-card-copy {
        min-height: 96px;
    }

    .dashboard-card-copy .stat-value {
        margin-top: 0.35rem;
    }

    .dashboard-card-copy .stat-hint {
        min-height: 1.2rem;
    }

    .document-tile-title {
        color: var(--kb-ink);
        font-size: 1rem;
        font-weight: 700;
        line-height: 1.45;
        min-height: 2.9rem;
        overflow-wrap: anywhere;
    }

    .document-meta {
        color: var(--kb-muted);
        font-size: 0.8rem;
        margin: 0.4rem 0 0.9rem;
    }

    .document-status {
        color: #18794e;
        background: #ecfdf3;
        border: 1px solid #d1fadf;
        border-radius: 999px;
        display: inline-block;
        font-size: 0.75rem;
        padding: 0.25rem 0.55rem;
    }

    .recent-document-card {
        border: 1px solid var(--kb-border);
        background: var(--kb-surface);
        border-radius: 0.95rem;
        padding: 1.05rem 1.1rem;
        min-height: 126px;
        box-shadow: 0 7px 22px rgba(31, 51, 81, 0.04);
    }

    .recent-document-name {
        color: var(--kb-ink);
        font-weight: 700;
        line-height: 1.45;
        margin-bottom: 0.75rem;
        overflow-wrap: anywhere;
    }

    .recent-document-meta {
        color: var(--kb-muted);
        font-size: 0.78rem;
    }

    .detail-label {
        color: var(--kb-muted);
        font-size: 0.76rem;
        margin-bottom: 0.18rem;
    }

    .detail-value {
        color: var(--kb-ink);
        font-size: 0.94rem;
        font-weight: 650;
        overflow-wrap: anywhere;
    }

    .stat-label {
        color: var(--kb-muted);
        font-size: 0.86rem;
        margin-bottom: 0.6rem;
    }

    .stat-value {
        color: var(--kb-ink);
        font-size: 1.85rem;
        font-weight: 700;
        line-height: 1.1;
    }

    .stat-hint {
        color: #8a94a6;
        font-size: 0.78rem;
        margin-top: 0.55rem;
    }

    .section-title {
        color: var(--kb-ink);
        font-size: 1.12rem;
        font-weight: 700;
        margin: 2rem 0 0.85rem;
    }

    .empty-state {
        border: 1px dashed #cfd7e5;
        background: rgba(255, 255, 255, 0.66);
        border-radius: 1rem;
        color: var(--kb-muted);
        padding: 2rem;
        text-align: center;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--kb-surface);
        border-color: var(--kb-border) !important;
        border-radius: 0.95rem;
        box-shadow: 0 7px 22px rgba(31, 51, 81, 0.04);
    }

    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 0.42rem;
        background: #22a06b;
        box-shadow: 0 0 0 3px rgba(34, 160, 107, 0.12);
    }

    .source-chip {
        display: inline-block;
        background: var(--kb-primary-soft);
        border: 1px solid #d8e5f6;
        color: #274d82;
        border-radius: 999px;
        font-size: 0.78rem;
        padding: 0.28rem 0.62rem;
        margin: 0.2rem 0.25rem 0 0;
    }

    .search-distance {
        display: inline-block;
        color: #315b9a;
        background: #edf3fb;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 650;
        padding: 0.26rem 0.58rem;
    }

    .stButton > button, .stFormSubmitButton > button {
        border-radius: 0.65rem;
        font-weight: 650;
    }

    /* Keep every Streamlit button readable before and during hover. */
    button[data-testid^="stBaseButton"],
    .stButton > button,
    .stFormSubmitButton > button,
    [data-testid="stFileUploader"] button {
        background: #ffffff !important;
        border: 1px solid #cfd7e5 !important;
        color: #253858 !important;
        opacity: 1 !important;
        transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
    }

    button[data-testid^="stBaseButton"] *,
    .stButton > button *,
    .stFormSubmitButton > button *,
    [data-testid="stFileUploader"] button * {
        color: inherit !important;
        fill: currentColor !important;
    }

    button[data-testid="stBaseButton-primary"],
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: var(--kb-primary) !important;
        border-color: var(--kb-primary) !important;
        color: #ffffff !important;
    }

    button[data-testid="stBaseButton-secondary"],
    .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        border-color: #cfd7e5 !important;
        color: #253858 !important;
    }

    button[data-testid="stBaseButton-tertiary"],
    .stButton > button[kind="tertiary"] {
        background: transparent !important;
        border-color: transparent !important;
        color: var(--kb-primary) !important;
    }

    button[data-testid="stBaseButton-primary"]:hover,
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover {
        background: #274d82 !important;
        border-color: #274d82 !important;
        color: #ffffff !important;
    }

    button[data-testid="stBaseButton-secondary"]:hover,
    .stButton > button[kind="secondary"]:hover,
    [data-testid="stFileUploader"] button:hover {
        background: var(--kb-primary-soft) !important;
        border-color: #9fb8da !important;
        color: #274d82 !important;
    }

    button[data-testid="stBaseButton-tertiary"]:hover,
    .stButton > button[kind="tertiary"]:hover {
        background: var(--kb-primary-soft) !important;
        border-color: transparent !important;
        color: #274d82 !important;
    }

    button[data-testid^="stBaseButton"]:focus-visible,
    .stButton > button:focus-visible,
    .stFormSubmitButton > button:focus-visible {
        outline: 3px solid rgba(49, 91, 154, 0.22) !important;
        outline-offset: 2px;
    }

    button[data-testid^="stBaseButton"]:disabled,
    .stButton > button:disabled,
    .stFormSubmitButton > button:disabled {
        background: #f2f4f7 !important;
        border-color: #e4e7ec !important;
        color: #98a2b3 !important;
        cursor: not-allowed;
    }

    /* Main-content category navigation stays dark on its light surface. */
    [data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label,
    [data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label p,
    [data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label span {
        color: #344054 !important;
    }

    [data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label {
        border-radius: 0.6rem;
        padding: 0.38rem 0.45rem;
    }

    [data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label:hover {
        background: var(--kb-primary-soft);
        color: #274d82 !important;
    }

    .stTextInput input, [data-testid="stFileUploader"] section {
        border-radius: 0.75rem;
    }

    @media (max-width: 720px) {
        .block-container { padding-top: 1.4rem; }
        .hero-panel { padding: 1.45rem; }
        .stat-card { min-height: 118px; }
        .document-tile-title { min-height: auto; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


api = KnowledgeBaseAPI()
selected_page = render_sidebar(api)

PAGES = {
    "首页": home.render,
    "知识库": knowledge.render,
    "AI助手": chat.render,
    "知识检索": search.render,
}

PAGES[selected_page](api)
