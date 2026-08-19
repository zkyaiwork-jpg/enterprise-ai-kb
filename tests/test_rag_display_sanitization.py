from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]


def test_search_preview_uses_clean_content_but_technical_panel_keeps_raw_chunk():
    utility = (
        PROJECT_ROOT / "frontend-react" / "src" / "utils" / "knowledgeContent.ts"
    ).read_text(encoding="utf-8")
    result_card = (
        PROJECT_ROOT
        / "frontend-react"
        / "src"
        / "components"
        / "search"
        / "SearchResultCard.tsx"
    ).read_text(encoding="utf-8")

    assert "ruleHeadingPattern" in utility
    assert "chineseChapterPrefixPattern" in utility
    assert "hierarchicalNumberPrefixPattern" in utility
    assert "const displayContent = cleanKnowledgeContent(result.content)" in result_card
    assert "{displayContent || '暂无可展示的匹配文本'}" in result_card
    assert "原始Chunk内容" in result_card
    assert "{result.content || '暂无原始Chunk内容'}" in result_card


def test_rag_prompt_still_prohibits_internal_and_retrieval_markers():
    rag_service = (PROJECT_ROOT / "app" / "services" / "rag_service.py").read_text(
        encoding="utf-8"
    )

    assert "RULE 编号、章节编号" in rag_service
    assert "不要输出 Chunk 编号" in rag_service
    assert "不要描述向量检索过程" in rag_service
