from io import BytesIO

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def authenticated_upload_context(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-upload-permission")

    from app.auth.jwt import create_access_token
    from app.auth.password import hash_password
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models import Department, Document, Role, User
    from app.services import document_service, folder_service

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as database:
        seed_default_permissions(database)
        department = Department(name="测试部门")
        database.add(department)
        database.flush()
        leader_role = database.scalar(select(Role).where(Role.name == "leader"))
        employee_role = database.scalar(select(Role).where(Role.name == "employee"))
        no_upload_role = Role(name="viewer_only", description="View-only test role")
        no_upload_role.permissions = [
            permission for permission in employee_role.permissions
            if permission.code == "file_view"
        ]
        database.add(no_upload_role)
        database.flush()
        uploader = User(
            username="upload_employee",
            password_hash=hash_password("StrongPass123"),
            real_name="上传员工",
            role=database.scalar(select(Role).where(Role.name == "manager")),
            department=department,
            status="active",
        )
        no_upload_user = User(
            username="no_upload_employee",
            password_hash=hash_password("StrongPass123"),
            real_name="无上传权限员工",
            role=no_upload_role,
            department=department,
            status="active",
        )
        database.add_all([uploader, no_upload_user])
        database.commit()
        database.refresh(uploader)
        database.refresh(no_upload_user)
        tokens = {
            "uploader": create_access_token(uploader.id, uploader.token_version),
            "no_upload": create_access_token(no_upload_user.id, no_upload_user.token_version),
        }
        expected = {"user_id": uploader.id, "department_id": department.id}

    monkeypatch.setattr(document_service, "UPLOAD_DIR", tmp_path / "documents")
    monkeypatch.setattr(folder_service, "CHAT_HISTORY_DB", tmp_path / "folders.db")
    parser = type("TestParser", (), {"parse": lambda self, path: "employee policy text"})()
    monkeypatch.setattr(document_service, "get_parser", lambda path: parser)
    monkeypatch.setattr(document_service, "split_text", lambda content: ["chunk one", "chunk two"])
    captured = {}

    def fake_save_chunks(chunks, metadata):
        captured.update(metadata)
        return {"count": len(chunks)}

    monkeypatch.setattr(document_service, "save_chunks", fake_save_chunks)

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client, tokens, testing_session, Document, captured, expected
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_docx_upload_returns_metadata_and_creates_document(authenticated_upload_context):
    client, tokens, testing_session, Document, captured, expected = authenticated_upload_context
    folder = client.post("/folders", json={"name": "AI知识"}).json()
    login = client.post("/auth/login", json={
        "username": "upload_employee",
        "password": "StrongPass123",
    })
    assert login.status_code == 200
    login_token = login.json()["access_token"]
    response = client.post(
        "/upload",
        data={"folder_id": folder["id"], "visibility": "department"},
        headers={"Authorization": f"Bearer {login_token}"},
        files={"file": ("policy.docx", b"fake-docx-content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"]
    assert payload["filename"] == "policy.docx"
    assert payload["vector_count"] == 2
    assert captured["document_id"] == payload["document_id"]
    assert captured["filename"] == "policy.docx"
    assert captured["file_type"] == "docx"
    assert captured["status"] == "indexed"
    assert captured["folder_id"] == folder["id"]
    assert captured["folder_name"] == "AI知识"
    assert payload["folder_name"] == "AI知识"
    assert payload["uploaded_at"].endswith("Z")
    assert captured["uploaded_at"] == payload["uploaded_at"]
    assert captured["document_id"] == payload["document_id"]
    assert captured["uploader_id"] == expected["user_id"]
    assert captured["department_id"] == expected["department_id"]
    assert captured["visibility"] == "department"

    with testing_session() as database:
        from app.models.audit_log import AuditLog
        document = database.scalar(select(Document).where(Document.filename == "policy.docx"))
        assert document is not None
        assert document.id == payload["document_id"]
        assert document.original_name == "policy.docx"
        assert document.uploader_id == expected["user_id"]
        assert document.department_id == expected["department_id"]
        assert document.visibility.value == "department"
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "document_upload"))
        assert audit is not None
        assert audit.user_id == expected["user_id"]
        assert audit.resource_id == str(document.id)
        assert audit.resource_name == "policy.docx"
        assert audit.result == "success"


def test_upload_requires_token(authenticated_upload_context):
    client, _, _, _, _, _ = authenticated_upload_context
    response = client.post(
        "/upload",
        files={"file": ("policy.docx", b"content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 401


def test_upload_requires_file_upload_permission(authenticated_upload_context):
    client, tokens, _, _, _, _ = authenticated_upload_context
    response = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {tokens['no_upload']}"},
        files={"file": ("policy.docx", b"content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 403


def test_upload_visibility_is_rejected_before_document_processing(authenticated_upload_context, monkeypatch):
    client, _, testing_session, Document, _, _ = authenticated_upload_context
    from app.auth.jwt import create_access_token
    from app.models import Role, User
    from app.services import document_service

    with testing_session() as database:
        employee_role = database.scalar(select(Role).where(Role.name == "employee"))
        employee = User(username="visibility_employee", password_hash="x", real_name="Employee", role=employee_role)
        database.add(employee)
        database.commit()
        token = create_access_token(employee.id, employee.token_version)
    called = {"save": False}
    monkeypatch.setattr(document_service, "save_document", lambda *args, **kwargs: called.update(save=True))
    response = client.post(
        "/upload",
        data={"visibility": "company"},
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("forbidden-company.docx", b"content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 403
    assert called["save"] is False
    with testing_session() as database:
        assert database.scalar(select(Document).where(Document.filename == "forbidden-company.docx")) is None


def test_employee_with_cross_department_team_cannot_upload(authenticated_upload_context):
    client, _, testing_session, Document, _, _ = authenticated_upload_context
    from app.auth.jwt import create_access_token
    from app.models import Department, Role, Team, User

    with testing_session() as database:
        department_a = database.scalar(select(Department).where(Department.name == "测试部门"))
        department_b = Department(name="其他部门")
        team_b = Team(name="Other Team", department=department_b)
        employee_role = database.scalar(select(Role).where(Role.name == "employee"))
        database.add_all([department_b, team_b])
        database.flush()
        employee = User(
            username="dirty_org_employee", password_hash="x", real_name="Dirty Org",
            role=employee_role, department=department_a, team=team_b,
        )
        database.add(employee)
        database.commit()
        token = create_access_token(employee.id, employee.token_version)

    response = client.post(
        "/upload",
        data={"visibility": "private"},
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("dirty-org.docx", b"content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400
    assert "小组与部门归属不一致" in response.json()["detail"]
    with testing_session() as database:
        assert database.scalar(select(Document).where(Document.filename == "dirty-org.docx")) is None


def test_duplicate_filename_returns_409_without_changing_owner(authenticated_upload_context):
    client, tokens, testing_session, Document, _, expected = authenticated_upload_context
    headers = {"Authorization": f"Bearer {tokens['uploader']}"}
    first = client.post(
        "/upload", data={"visibility": "private"}, headers=headers,
        files={"file": ("duplicate.docx", b"first", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert first.status_code == 200
    second = client.post(
        "/upload", data={"visibility": "department"}, headers=headers,
        files={"file": ("duplicate.docx", b"second", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert second.status_code == 409
    with testing_session() as database:
        document = database.scalar(select(Document).where(Document.filename == "duplicate.docx"))
        assert document.uploader_id == expected["user_id"]
        assert document.department_id == expected["department_id"]
        assert document.visibility.value == "private"


def test_unsupported_upload_is_rejected(authenticated_upload_context):
    client, tokens, _, _, _, _ = authenticated_upload_context
    response = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {tokens['uploader']}"},
        files={"file": ("archive.zip", b"not a document", "application/zip")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "当前仅支持DOCX、TXT和PDF文件"


def test_parse_failure_preserves_old_file_and_vectors(tmp_path, monkeypatch):
    from app.services import document_service
    from conftest import FakeCollection

    upload_dir = tmp_path / "documents"
    upload_dir.mkdir()
    old_file = upload_dir / "policy.docx"
    old_file.write_bytes(b"old-version")

    collection = FakeCollection()
    collection.add(
        ids=["old-document:0"],
        documents=["old chunk"],
        metadatas=[{"document_id": "old-document", "filename": "policy.docx"}],
    )
    monkeypatch.setattr(document_service, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(document_service, "collection", collection)
    parser = type(
        "FailingParser",
        (),
        {"parse": lambda self, path: (_ for _ in ()).throw(ValueError("parse failed"))},
    )()
    monkeypatch.setattr(document_service, "get_parser", lambda path: parser)

    upload = UploadFile(filename="policy.docx", file=BytesIO(b"broken-new-version"))

    try:
        document_service.save_document(upload)
        raise AssertionError("save_document should fail")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 422

    assert old_file.read_bytes() == b"old-version"
    assert collection.get(ids=["old-document:0"])["ids"] == ["old-document:0"]
    assert collection.deleted_ids == []
