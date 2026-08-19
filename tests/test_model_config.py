from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def model_config_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "model-config-test-jwt-secret-over-32-bytes")
    encryption_key = Fernet.generate_key().decode()
    monkeypatch.setenv("MODEL_CONFIG_ENCRYPTION_KEY", encryption_key)

    from app.auth.jwt import create_access_token
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models import Role, User

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as database:
        seed_default_permissions(database)
        roles = {role.name: role for role in database.scalars(select(Role)).all()}
        users = {
            role: User(username=f"model_{role}", password_hash="x", real_name=role, role=roles[role], status="active")
            for role in ("admin", "manager", "leader", "employee")
        }
        database.add_all(users.values())
        database.commit()
        tokens = {role: create_access_token(user.id, user.token_version) for role, user in users.items()}

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, tokens, testing_session, encryption_key
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _payload(api_key="sk-enterprise-secret"):
    payload = {
        "provider": "deepseek",
        "model_name": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "is_active": True,
    }
    if api_key is not None:
        payload["api_key"] = api_key
    return payload


def test_admin_encrypts_key_and_get_never_exposes_it(model_config_context):
    client, tokens, testing_session, _ = model_config_context
    from app.models.audit_log import AuditLog
    from app.models.model_config import ModelConfig
    from app.services.model_config_crypto import decrypt_api_key

    response = client.put("/model-config", headers=_headers(tokens["admin"]), json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["api_key_configured"] is True
    assert body["updated_time"].endswith("Z")
    assert "api_key" not in body and "encrypted_api_key" not in body
    with testing_session() as database:
        config = database.scalar(select(ModelConfig))
        assert config.encrypted_api_key != "sk-enterprise-secret"
        assert "sk-enterprise-secret" not in config.encrypted_api_key
        assert decrypt_api_key(config.encrypted_api_key) == "sk-enterprise-secret"
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "model_config_update"))
        assert "sk-enterprise-secret" not in str(audit.__dict__)
        assert "api_key_rotated=true" in audit.detail

    get_response = client.get("/model-config", headers=_headers(tokens["admin"]))
    assert get_response.status_code == 200
    assert get_response.json()["updated_time"].endswith("Z")
    assert "api_key" not in get_response.json() and "encrypted_api_key" not in get_response.json()


def test_update_without_key_preserves_ciphertext_and_rotation_replaces_key(model_config_context):
    client, tokens, testing_session, _ = model_config_context
    from app.models.model_config import ModelConfig
    from app.services.model_config_crypto import decrypt_api_key

    client.put("/model-config", headers=_headers(tokens["admin"]), json=_payload("first-secret"))
    with testing_session() as database:
        first_ciphertext = database.scalar(select(ModelConfig)).encrypted_api_key
    payload = _payload(None)
    payload["model_name"] = "deepseek-reasoner"
    assert client.put("/model-config", headers=_headers(tokens["admin"]), json=payload).status_code == 200
    with testing_session() as database:
        config = database.scalar(select(ModelConfig))
        assert config.encrypted_api_key == first_ciphertext
    assert client.put("/model-config", headers=_headers(tokens["admin"]), json=_payload("second-secret")).status_code == 200
    with testing_session() as database:
        assert decrypt_api_key(database.scalar(select(ModelConfig)).encrypted_api_key) == "second-secret"


def test_missing_encryption_key_rejects_new_secret_without_leaking(model_config_context, monkeypatch):
    client, tokens, testing_session, _ = model_config_context
    from app.models.audit_log import AuditLog
    from app.models.model_config import ModelConfig

    monkeypatch.delenv("MODEL_CONFIG_ENCRYPTION_KEY")
    response = client.put("/model-config", headers=_headers(tokens["admin"]), json=_payload("never-store-me"))
    assert response.status_code == 503
    assert "never-store-me" not in str(response.json())
    with testing_session() as database:
        assert database.scalar(select(ModelConfig)) is None
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "model_config_update"))
        assert audit.result == "failed" and "never-store-me" not in str(audit.__dict__)


def test_only_admin_default_role_can_manage_model_config(model_config_context):
    client, tokens, _, _ = model_config_context
    assert client.get("/model-config").status_code == 401
    for role in ("employee", "leader", "manager"):
        assert client.get("/model-config", headers=_headers(tokens[role])).status_code == 403
    assert client.get("/model-config", headers=_headers(tokens["admin"])).status_code == 200


def test_connection_test_is_mocked_and_errors_are_safe(model_config_context, monkeypatch):
    client, tokens, testing_session, _ = model_config_context
    from app.api import model_config as api
    from app.models.audit_log import AuditLog

    client.put("/model-config", headers=_headers(tokens["admin"]), json=_payload())
    monkeypatch.setattr(api, "test_model_connection", lambda database: None)
    assert client.post("/model-config/test", headers=_headers(tokens["admin"])).json() == {"success": True}
    monkeypatch.setattr(api, "test_model_connection", lambda database: (_ for _ in ()).throw(RuntimeError("provider secret header")))
    failed = client.post("/model-config/test", headers=_headers(tokens["admin"]))
    assert failed.status_code == 502 and failed.json() == {"detail": "模型连接测试失败"}
    with testing_session() as database:
        audits = database.scalars(select(AuditLog).where(AuditLog.action == "model_config_test")).all()
        assert {audit.result for audit in audits} == {"success", "failed"}
        assert "provider secret header" not in str([audit.detail for audit in audits])


def test_rag_uses_database_config_without_exposing_key(model_config_context, monkeypatch):
    _, _, testing_session, _ = model_config_context
    from app.services import rag_service
    from app.services.model_config_service import upsert_model_config

    captured = {}
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: (
        captured.update(kwargs) or SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))])
    ))))
    monkeypatch.setattr(rag_service, "search_documents", lambda *args, **kwargs: {"results": [{"content": "allowed", "filename": "safe.docx"}]})
    monkeypatch.setattr(rag_service, "create_model_client", lambda config: captured.update({"runtime": config}) or fake_client)
    with testing_session() as database:
        upsert_model_config(database, **{**_payload("database-secret"), "base_url": "https://api.deepseek.com/"})
        result = rag_service.ask_ai("question", allowed_document_ids={1}, database=database)
    assert result["answer"] == "answer"
    assert captured["runtime"].source == "database"
    assert captured["runtime"].api_key == "database-secret"
    assert "database-secret" not in str(result)


def test_no_database_or_environment_config_returns_safe_503(model_config_context, monkeypatch):
    _, _, testing_session, _ = model_config_context
    from app.services import rag_service
    from fastapi import HTTPException

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(rag_service, "search_documents", lambda *args, **kwargs: {"results": [{"content": "allowed"}]})
    with testing_session() as database, pytest.raises(HTTPException) as error:
        rag_service.ask_ai("question", allowed_document_ids={1}, database=database)
    assert error.value.status_code == 503
    assert error.value.detail == "模型服务尚未配置"
