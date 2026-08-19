from types import SimpleNamespace


class StaticCollection:
    def __init__(self, documents, distances, metadatas):
        self.documents = documents
        self.distances = distances
        self.metadatas = metadatas
        self.query_calls = []

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return {
            "documents": [self.documents],
            "distances": [self.distances],
            "metadatas": [self.metadatas],
        }


def _prepare_search(monkeypatch, collection):
    from app.services import search_service

    monkeypatch.setattr(search_service, "collection", collection)
    monkeypatch.setattr(
        search_service,
        "encode_texts",
        lambda values: SimpleNamespace(tolist=lambda: [[0.0, 0.0]]),
    )
    return search_service


def test_search_calls_reranker_after_permission_check_and_before_threshold(monkeypatch):
    collection = StaticCollection(
        documents=["within threshold", "above threshold"],
        distances=[0.2, 0.9],
        metadatas=[
            {"document_id": 1, "filename": "first.docx"},
            {"document_id": 2, "filename": "second.docx"},
        ],
    )
    search_service = _prepare_search(monkeypatch, collection)
    captured = {}

    def recording_rerank(question, documents):
        captured["question"] = question
        captured["documents"] = documents
        return [
            {**document, "rerank_score": float(index)}
            for index, document in enumerate(reversed(documents), start=1)
        ]

    monkeypatch.setattr(
        search_service.reranker_service,
        "rerank_documents",
        recording_rerank,
    )

    result = search_service.search_documents(
        "policy question",
        allowed_document_ids={1, 2},
    )

    assert captured["question"] == "policy question"
    assert [item["filename"] for item in captured["documents"]] == [
        "first.docx",
        "second.docx",
    ]
    # The 0.9 candidate reaches Rerank, proving threshold filtering happens
    # after reranking, but it is still excluded from the returned results.
    assert [item["filename"] for item in result["results"]] == ["first.docx"]
    assert result["results"][0]["rerank_score"] == 2.0


def test_search_returns_reranked_order_and_preserves_existing_fields(monkeypatch):
    collection = StaticCollection(
        documents=["original first", "more relevant"],
        distances=[0.1, 0.2],
        metadatas=[
            {"document_id": 1, "filename": "original.docx", "chunk_index": 0},
            {"document_id": 2, "filename": "correct.docx", "chunk_index": 3},
        ],
    )
    search_service = _prepare_search(monkeypatch, collection)

    def reverse_with_scores(question, documents):
        return [
            {**documents[1], "rerank_score": 0.95},
            {**documents[0], "rerank_score": 0.10},
        ]

    monkeypatch.setattr(
        search_service.reranker_service,
        "rerank_documents",
        reverse_with_scores,
    )

    results = search_service.search_documents(
        "bad case",
        allowed_document_ids={1, 2},
    )["results"]

    assert [item["filename"] for item in results] == [
        "correct.docx",
        "original.docx",
    ]
    assert results[0]["content"] == "more relevant"
    assert results[0]["distance"] == 0.2
    assert results[0]["chunk_index"] == 3
    assert results[0]["metadata"]["document_id"] == 2
    assert results[0]["embedding_model"] == "BAAI/bge-small-zh-v1.5"
    assert results[0]["vector_database"] == "ChromaDB"
    assert results[0]["rerank_score"] == 0.95


def test_unauthorized_chroma_result_never_reaches_reranker(monkeypatch):
    collection = StaticCollection(
        documents=["allowed content", "forbidden secret content"],
        distances=[0.2, 0.1],
        metadatas=[
            {"document_id": 1, "filename": "allowed.docx"},
            {"document_id": 999, "filename": "forbidden.docx"},
        ],
    )
    search_service = _prepare_search(monkeypatch, collection)
    captured = {}

    def recording_rerank(question, documents):
        captured["documents"] = documents
        return [{**documents[0], "rerank_score": 0.5}]

    monkeypatch.setattr(
        search_service.reranker_service,
        "rerank_documents",
        recording_rerank,
    )

    results = search_service.search_documents(
        "policy",
        allowed_document_ids={1},
    )["results"]

    assert [item["filename"] for item in captured["documents"]] == ["allowed.docx"]
    assert [item["filename"] for item in results] == ["allowed.docx"]
    assert "forbidden secret content" not in [
        item["content"] for item in captured["documents"]
    ]


def test_reranker_failure_falls_back_to_original_chroma_order(monkeypatch, caplog):
    collection = StaticCollection(
        documents=["first", "second", "filtered"],
        distances=[0.2, 0.3, 0.9],
        metadatas=[
            {"document_id": 1, "filename": "first.docx"},
            {"document_id": 2, "filename": "second.docx"},
            {"document_id": 3, "filename": "filtered.docx"},
        ],
    )
    search_service = _prepare_search(monkeypatch, collection)

    def failing_rerank(question, documents):
        raise RuntimeError("sensitive internal failure")

    monkeypatch.setattr(
        search_service.reranker_service,
        "rerank_documents",
        failing_rerank,
    )

    results = search_service.search_documents(
        "policy",
        allowed_document_ids={1, 2, 3},
    )["results"]

    assert [item["filename"] for item in results] == ["first.docx", "second.docx"]
    assert all("rerank_score" not in item for item in results)
    assert "fallback=chroma_order" in caplog.text
    assert "sensitive internal failure" not in caplog.text
