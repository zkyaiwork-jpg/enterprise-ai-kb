from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


TEST_JWT_SECRET = "test-secret-key-for-current-user-dependency"


@pytest.fixture
def protected_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)

    from app.auth.dependency import get_current_user
    from app.auth.jwt import create_access_token
    from app.auth.password import hash_password
    from app.database.database import Base, get_db
    from app.models.user import User

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with testing_session() as database:
        user = User(
            username="identity_user",
            password_hash=hash_password("StrongPass123"),
            real_name="身份测试用户",
            status="active",
        )
        database.add(user)
        database.commit()
        database.refresh(user)
        user_id = user.id
        token_version = user.token_version

    app = FastAPI()

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/protected")
    def protected(current_user: User = Depends(get_current_user)):
        return {"id": current_user.id, "username": current_user.username}

    try:
        with TestClient(app) as client:
            yield client, user_id, token_version, create_access_token, testing_session
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_valid_token_returns_current_user(protected_context):
    client, user_id, token_version, create_access_token, _ = protected_context
    token = create_access_token(user_id, token_version)

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": user_id, "username": "identity_user"}


@pytest.mark.parametrize(
    "authorization",
    [None, "invalid-format", "Bearer not-a-jwt"],
)
def test_missing_or_invalid_token_is_rejected(protected_context, authorization):
    client, _, _, _, _ = protected_context
    headers = {"Authorization": authorization} if authorization else {}

    response = client.get("/protected", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_expired_token_is_rejected(protected_context):
    client, user_id, token_version, _, _ = protected_context
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "token_version": token_version,
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=1),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Token已过期"


def test_token_for_deleted_user_is_rejected(protected_context):
    client, _, _, create_access_token, _ = protected_context
    token = create_access_token(999999, 1)

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Token对应的用户不存在"


def test_missing_token_version_is_rejected(protected_context):
    client, user_id, _, _, _ = protected_context
    now = datetime.now(timezone.utc)
    old_token = jwt.encode(
        {"sub": str(user_id), "type": "access", "iat": now, "exp": now + timedelta(minutes=5)},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    assert client.get("/protected", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


def test_database_version_change_invalidates_old_token(protected_context):
    client, user_id, token_version, create_access_token, testing_session = protected_context
    from app.models.user import User

    token = create_access_token(user_id, token_version)
    assert client.get("/protected", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    with testing_session() as database:
        user = database.get(User, user_id)
        user.token_version += 1
        database.commit()
    assert client.get("/protected", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_forged_token_version_without_valid_signature_is_rejected(protected_context):
    client, user_id, token_version, _, _ = protected_context
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {"sub": str(user_id), "type": "access", "token_version": token_version, "iat": now, "exp": now + timedelta(minutes=5)},
        "attacker-controlled-secret-over-32-bytes",
        algorithm="HS256",
    )
    assert client.get("/protected", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
