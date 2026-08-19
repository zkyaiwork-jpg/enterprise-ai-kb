from fastapi.testclient import TestClient


def test_health_returns_all_components(client: TestClient, monkeypatch):
    from app.api import health

    expected = {
        "status": "healthy",
        "api": "ok",
        "vector_db": "ok",
        "chat_db": "ok",
        "ai": "configured",
    }
    monkeypatch.setattr(health, "get_health_status", lambda: expected)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == expected
