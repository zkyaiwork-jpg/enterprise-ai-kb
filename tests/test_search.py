from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_search_returns_structured_result(authorized_client: TestClient, monkeypatch):
    from app.api import search

    monkeypatch.setattr(search, "search_documents", lambda query, **kwargs: {
        "results": [{
            "filename": "policy.docx",
            "folder_id": 1,
            "folder_name": "员工制度",
            "file_type": "docx",
            "content": "Employees receive annual leave.",
            "chunk_index": 2,
            "distance": 0.12,
        }]
    })

    response = authorized_client.get("/search", params={"query": "annual leave"})

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["filename"] == "policy.docx"
    assert result["content"]
    assert result["distance"] == 0.12
    assert result["folder_name"] == "员工制度"
    assert result["file_type"] == "docx"


def test_search_rejects_empty_query(authorized_client: TestClient, monkeypatch):
    from app.api import search

    def reject_empty(query):
        if not query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")

    monkeypatch.setattr(search, "search_documents", reject_empty)
    response = authorized_client.get("/search", params={"query": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "查询内容不能为空"


def test_search_returns_empty_results(authorized_client: TestClient, monkeypatch):
    from app.api import search

    monkeypatch.setattr(search, "search_documents", lambda query, **kwargs: {"results": []})
    response = authorized_client.get("/search", params={"query": "missing knowledge"})

    assert response.status_code == 200
    assert response.json() == {"results": []}
