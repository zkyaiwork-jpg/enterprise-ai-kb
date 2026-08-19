from fastapi.testclient import TestClient


def test_stats_returns_real_shape(client: TestClient, monkeypatch):
    from app.api import stats

    monkeypatch.setattr(stats, "get_system_stats", lambda: {
        "document_count": 2,
        "chunk_count": 14,
        "question_count": 3,
        "ai_status": "online",
    })

    response = client.get("/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_count"] == 2
    assert payload["chunk_count"] == 14
    assert payload["question_count"] == 3
