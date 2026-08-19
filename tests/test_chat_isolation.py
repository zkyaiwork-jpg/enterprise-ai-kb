import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def isolated_users(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "chat-isolation-test-secret")

    from app.auth.jwt import create_access_token
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models import Role, User
    from app.api import chat

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as database:
        seed_default_permissions(database)
        employee_role = database.scalar(select(Role).where(Role.name == "employee"))
        users = [
            User(username="chat_user_a", password_hash="x", real_name="User A", role=employee_role, status="active"),
            User(username="chat_user_b", password_hash="x", real_name="User B", role=employee_role, status="active"),
        ]
        database.add_all(users)
        database.commit()
        tokens = {user.username: create_access_token(user.id, user.token_version) for user in users}
        user_ids = {user.username: user.id for user in users}

    def override_get_db():
        with testing_session() as database:
            yield database

    monkeypatch.setattr(chat, "ask_ai", lambda question, **kwargs: {
        "answer": f"Private answer for {question}",
        "sources": [{"filename": f"{question}.docx", "document_id": 1}],
    })
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, tokens, user_ids, testing_session
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_user_can_create_and_continue_own_conversation(isolated_users):
    client, tokens, _, _ = isolated_users
    headers = _auth(tokens["chat_user_a"])

    created = client.post("/chat", headers=headers, json={"question": "first"})
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]
    continued = client.post(
        "/chat",
        headers=headers,
        json={"question": "second", "conversation_id": conversation_id},
    )
    assert continued.status_code == 200
    assert continued.json()["conversation_id"] == conversation_id

    detail = client.get(f"/chat/conversations/{conversation_id}", headers=headers).json()
    assert [message["role"] for message in detail["messages"]] == [
        "user", "assistant", "user", "assistant",
    ]


def test_other_user_cannot_read_or_append_to_conversation(isolated_users):
    client, tokens, _, _ = isolated_users
    created = client.post(
        "/chat",
        headers=_auth(tokens["chat_user_a"]),
        json={"question": "secret"},
    ).json()
    conversation_id = created["conversation_id"]
    user_b_headers = _auth(tokens["chat_user_b"])

    read_response = client.get(f"/chat/conversations/{conversation_id}", headers=user_b_headers)
    append_response = client.post(
        "/chat",
        headers=user_b_headers,
        json={"question": "intrusion", "conversation_id": conversation_id},
    )

    assert read_response.status_code == 404
    assert append_response.status_code == 404
    assert read_response.json() == append_response.json()


def test_conversation_lists_and_sources_are_owner_isolated(isolated_users):
    client, tokens, _, _ = isolated_users
    for username, question in (("chat_user_a", "alpha-secret"), ("chat_user_b", "beta-secret")):
        response = client.post(
            "/chat",
            headers=_auth(tokens[username]),
            json={"question": question},
        )
        assert response.status_code == 200

    list_a = client.get("/chat/conversations", headers=_auth(tokens["chat_user_a"])).json()["conversations"]
    list_b = client.get("/chat/conversations", headers=_auth(tokens["chat_user_b"])).json()["conversations"]
    assert [item["title"] for item in list_a] == ["alpha-secret"]
    assert [item["title"] for item in list_b] == ["beta-secret"]

    detail_a = client.get(
        f"/chat/conversations/{list_a[0]['id']}",
        headers=_auth(tokens["chat_user_a"]),
    ).json()
    assert detail_a["messages"][1]["sources"][0]["filename"] == "alpha-secret.docx"
    assert "beta-secret" not in str(detail_a)


def test_chat_messages_are_written_with_owner_and_order(isolated_users):
    client, tokens, user_ids, testing_session = isolated_users
    from app.models.chat_message import ChatMessage, ChatRole
    from app.models.conversation import Conversation

    client.post(
        "/chat",
        headers=_auth(tokens["chat_user_a"]),
        json={"question": "database-order"},
    )
    with testing_session() as database:
        conversation = database.scalar(select(Conversation))
        messages = list(database.scalars(
            select(ChatMessage).where(ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.id)
        ).all())

    assert conversation.user_id == user_ids["chat_user_a"]
    assert [message.role for message in messages] == [ChatRole.USER, ChatRole.ASSISTANT]
    assert messages[1].sources == [{"filename": "database-order.docx", "document_id": 1}]


def test_deleting_conversation_cascades_messages(isolated_users):
    client, tokens, _, testing_session = isolated_users
    from app.models.chat_message import ChatMessage
    from app.models.conversation import Conversation

    created = client.post(
        "/chat",
        headers=_auth(tokens["chat_user_a"]),
        json={"question": "temporary"},
    ).json()
    with testing_session() as database:
        conversation = database.get(Conversation, created["conversation_id"])
        database.delete(conversation)
        database.commit()
        assert database.scalar(
            select(ChatMessage).where(ChatMessage.conversation_id == created["conversation_id"])
        ) is None


def test_chat_and_history_require_token(isolated_users):
    client, _, _, _ = isolated_users
    assert client.post("/chat", json={"question": "anonymous"}).status_code == 401
    assert client.get("/chat/conversations").status_code == 401
    assert client.get("/chat/conversations/1").status_code == 401
    assert client.get("/chat/history").status_code == 401
