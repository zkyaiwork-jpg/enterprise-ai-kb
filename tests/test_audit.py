import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def audit_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "audit-access-test-secret-at-least-32-bytes")
    from app.auth.jwt import create_access_token
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models import AuditLog, Role, User

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as database:
        seed_default_permissions(database)
        roles = {role.name: role for role in database.scalars(select(Role)).all()}
        users = {
            name: User(username=f"audit_{name}", password_hash="x", real_name=name, role=roles[name], status="active")
            for name in ("admin", "manager", "leader", "employee")
        }
        database.add_all(users.values())
        database.flush()
        database.add(AuditLog(
            user_id=users["admin"].id,
            action="document_delete",
            resource_type="document",
            resource_id="42",
            resource_name="removed.docx",
            result="success",
            detail="vectors_deleted=2",
        ))
        database.commit()
        tokens = {name: create_access_token(user.id, user.token_version) for name, user in users.items()}

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, tokens, testing_session
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_only_admin_can_read_paginated_audit_logs(audit_context):
    client, tokens, _ = audit_context
    assert client.get("/audit-logs").status_code == 401
    for role in ("employee", "leader", "manager"):
        assert client.get("/audit-logs", headers=_headers(tokens[role])).status_code == 403

    response = client.get(
        "/audit-logs",
        headers=_headers(tokens["admin"]),
        params={"page": 1, "page_size": 10, "action": "document_delete", "result": "success"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["resource_id"] == "42"
    assert payload["items"][0]["resource_name"] == "removed.docx"
    assert payload["items"][0]["created_time"].endswith("Z")
    assert "password" not in str(payload).lower()
    assert "authorization" not in str(payload).lower()


def test_audit_seed_is_idempotent_and_admin_only(audit_context):
    _, _, testing_session = audit_context
    from app.database.seed_permissions import seed_default_permissions
    from app.models.role import Role

    with testing_session() as database:
        seed_default_permissions(database)
        seed_default_permissions(database)
        roles = {role.name: [permission.code for permission in role.permissions] for role in database.scalars(select(Role)).all()}
    assert roles["admin"].count("audit_view") == 1
    assert all("audit_view" not in roles[name] for name in ("manager", "leader", "employee"))


def test_audit_write_failure_is_logged_and_not_raised(caplog):
    from app.services.audit_service import write_audit_log

    class FailingSession:
        def add(self, item):
            raise RuntimeError("test database unavailable")

        def rollback(self):
            self.rolled_back = True

    session = FailingSession()
    with caplog.at_level(logging.ERROR):
        result = write_audit_log(
            session,
            action="document_upload",
            resource_type="document",
            result="success",
            user_id=1,
            resource_id=2,
            resource_name="safe.docx",
        )
    assert result is None
    assert session.rolled_back
    assert "Audit write failed" in caplog.text


def test_audit_log_survives_user_deletion(audit_context):
    _, _, testing_session = audit_context
    from app.models.audit_log import AuditLog
    from app.models.user import User

    with testing_session() as database:
        audit = database.scalar(select(AuditLog))
        user = database.get(User, audit.user_id)
        database.delete(user)
        database.commit()
        surviving = database.get(AuditLog, audit.id)
        assert surviving is not None
