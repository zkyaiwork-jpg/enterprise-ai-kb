from fastapi.testclient import TestClient


def test_chat_creates_conversation_and_persists_messages(authorized_client: TestClient, monkeypatch):
    from app.api import chat

    monkeypatch.setattr(chat, "ask_ai", lambda question, **kwargs: {
        "answer": "Employees receive paid annual leave.",
        "sources": [{"filename": "policy.docx", "chunk_index": 1}],
    })

    response = authorized_client.post("/chat", json={"question": "What is the leave policy?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Employees receive paid annual leave."
    assert payload["conversation_id"]
    assert payload["session_id"] == str(payload["conversation_id"])
    assert payload["created_at"].endswith("Z")

    detail = authorized_client.get(f"/chat/conversations/{payload['conversation_id']}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert [message["content"] for message in messages] == [
        "What is the leave policy?",
        "Employees receive paid annual leave.",
    ]
    assert messages[0]["sources"] == []
    assert messages[1]["sources"] == [{"filename": "policy.docx", "chunk_index": 1}]
    assert all(message["created_time"].endswith("Z") for message in messages)
    assert detail.json()["created_time"].endswith("Z")
    assert detail.json()["updated_time"].endswith("Z")


def test_chat_history_compatibility_returns_only_authenticated_users_new_conversations(
    authorized_client: TestClient,
    isolated_chat_db,
    monkeypatch,
):
    from app.api import chat
    from app.services.chat_history_service import save_chat_history

    # An unowned row in the legacy global database must never appear.
    save_chat_history("legacy-global", "Legacy question", "Legacy answer", [{"filename": "private.docx"}])
    monkeypatch.setattr(chat, "ask_ai", lambda question, **kwargs: {"answer": f"Answer: {question}", "sources": []})

    first = authorized_client.post("/chat", json={"question": "Question one"}).json()
    authorized_client.post("/chat", json={
        "question": "Question two",
        "conversation_id": first["conversation_id"],
    })

    response = authorized_client.get("/chat/history")

    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert [session["session_id"] for session in sessions] == [str(first["conversation_id"])]
    assert [message["question"] for message in sessions[0]["messages"]] == ["Question one", "Question two"]
    assert "Legacy question" not in str(sessions)
    assert sessions[0]["created_at"].endswith("Z")
    assert sessions[0]["updated_at"].endswith("Z")
    assert all(message["created_at"].endswith("Z") for message in sessions[0]["messages"])
