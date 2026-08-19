from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def auth_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-auth-tests-only")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    from app.database.database import Base, get_db
    from app.main import app
    from app.models.user import User

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, testing_session, User
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_anonymous_register_is_disabled(auth_context):
    client, _, _ = auth_context
    response = client.post("/auth/register", json={
        "username": "alice",
        "password": "StrongPass123",
        "real_name": "测试用户",
    })
    assert response.status_code == 401


def test_login_returns_verifiable_expiring_jwt(auth_context):
    client, testing_session, User = auth_context
    from app.models.audit_log import AuditLog
    from app.auth.password import hash_password
    with testing_session() as database:
        database.add(User(username="alice", password_hash=hash_password("StrongPass123"), real_name="测试用户", status="active"))
        database.commit()

    response = client.post("/auth/login", json={
        "username": "alice",
        "password": "StrongPass123",
    })

    assert response.status_code == 200
    token_response = response.json()
    assert token_response["token_type"] == "bearer"
    assert token_response["expires_in"] == 1800
    claims = jwt.decode(
        token_response["access_token"],
        "test-secret-key-for-auth-tests-only",
        algorithms=["HS256"],
    )
    assert claims["username"] == "alice"
    assert claims["type"] == "access"
    assert claims["token_version"] == 1
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] < claims["exp"]
    assert datetime.fromtimestamp(claims["exp"], tz=timezone.utc) > datetime.now(timezone.utc)
    with testing_session() as database:
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "auth_login_success"))
        assert audit is not None
        assert audit.user_id == int(claims["sub"])
        assert audit.result == "success"
        assert "StrongPass123" not in str(audit.detail)


def test_duplicate_registration_and_invalid_login_are_rejected(auth_context):
    client, testing_session, User = auth_context
    from app.models.audit_log import AuditLog
    from app.auth.password import hash_password
    with testing_session() as database:
        database.add(User(username="alice", password_hash=hash_password("StrongPass123"), real_name="测试用户", status="active"))
        database.commit()

    invalid_login = client.post("/auth/login", json={
        "username": "alice",
        "password": "WrongPassword",
    })
    assert invalid_login.status_code == 401
    assert invalid_login.json()["detail"] == "用户名或密码错误"
    with testing_session() as database:
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "auth_login_failed"))
        assert audit is not None
        assert audit.detail == "invalid_credentials"
        serialized = f"{audit.resource_name} {audit.detail}"
        assert "WrongPassword" not in serialized
        assert "password" not in serialized.lower()


def test_password_helpers_and_missing_jwt_secret(monkeypatch):
    from app.auth.jwt import JWTConfigurationError, create_access_token
    from app.auth.password import hash_password, verify_password

    password_hash = hash_password("StrongPass123")
    assert verify_password("StrongPass123", password_hash)
    assert not verify_password("WrongPassword", password_hash)

    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(JWTConfigurationError, match="JWT_SECRET_KEY未配置"):
        create_access_token("1", 1)
