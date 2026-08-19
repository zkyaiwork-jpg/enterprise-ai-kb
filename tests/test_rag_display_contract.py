from types import SimpleNamespace


def test_rag_prompt_hides_retrieval_details_and_keeps_technical_sources(monkeypatch):
    from app.services import rag_service

    source = {
        "filename": "editing-rules.docx",
        "folder_name": "AI知识",
        "file_type": "docx",
        "chunk_index": 7,
        "content": "RULE 03: 素材使用时长为十秒。",
        "distance": 0.603,
        "metadata": {"chunk_id": "document:7"},
        "embedding_model": "BAAI/bge-small-zh-v1.5",
        "vector_database": "ChromaDB",
    }
    monkeypatch.setattr(rag_service, "search_documents", lambda question, **kwargs: {"results": [source]})

    captured = {}

    def create_completion(**kwargs):
        captured.update(kwargs)
        message = SimpleNamespace(content="素材使用时长为十秒。")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_completion))
    )
    monkeypatch.setattr(rag_service, "create_model_client", lambda config: fake_client)

    result = rag_service.ask_ai("素材可以使用多久？", allowed_document_ids={1})

    system_prompt = captured["messages"][0]["content"]
    assert "不要输出 Chunk 编号" in system_prompt
    assert "不要描述向量检索过程" in system_prompt
    assert result["answer"] == "素材使用时长为十秒。"
    assert result["sources"][0]["folder_name"] == "AI知识"
    assert result["sources"][0]["chunk_index"] == 7
    assert result["sources"][0]["distance"] == 0.603
    assert result["sources"][0]["embedding_model"] == "BAAI/bge-small-zh-v1.5"
