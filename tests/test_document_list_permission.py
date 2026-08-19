import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def document_list_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-for-document-list-filtering")

    from app.api import document as document_api
    from app.auth.jwt import create_access_token
    from app.database.database import Base, get_db
    from app.main import app
    from app.models import Department, Document, DocumentVisibility, Permission, Role, User

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with testing_session() as database:
        department_a = Department(name="研发部")
        department_b = Department(name="市场部")
        roles = {name: Role(name=name) for name in ("admin", "manager", "leader", "employee")}
        file_view = Permission(code="file_view", name="File view")
        for role in roles.values():
            role.permissions.append(file_view)
        no_view_role = Role(name="no_file_view")
        users = {
            "admin": User(username="list_admin", password_hash="hash", real_name="管理员", role=roles["admin"], department=department_b),
            "manager": User(username="list_manager", password_hash="hash", real_name="主管", role=roles["manager"], department=department_a),
            "leader": User(username="list_leader", password_hash="hash", real_name="组长", role=roles["leader"], department=department_a),
            "employee": User(username="list_employee", password_hash="hash", real_name="员工", role=roles["employee"], department=department_a),
            "other_employee": User(username="list_other_employee", password_hash="hash", real_name="其他员工", role=roles["employee"], department=department_a),
            "outside_employee": User(username="list_outside_employee", password_hash="hash", real_name="外部员工", role=roles["employee"], department=department_b),
            "no_view": User(username="list_no_view", password_hash="hash", real_name="No view", role=no_view_role),
        }
        database.add_all([department_a, department_b, file_view, no_view_role, *roles.values(), *users.values()])
        database.flush()

        documents = {
            "employee_own": Document(filename="employee-own.docx", original_name="员工自己的文件.docx", uploader=users["employee"], department=department_a, visibility=DocumentVisibility.PRIVATE),
            "employee_peer": Document(filename="employee-peer.docx", original_name="同部门员工文件.docx", uploader=users["other_employee"], department=department_a, visibility=DocumentVisibility.DEPARTMENT),
            "leader_own": Document(filename="leader-own.docx", original_name="组长文件.docx", uploader=users["leader"], department=department_a, visibility=DocumentVisibility.PRIVATE),
            "manager_own": Document(filename="manager-own.docx", original_name="主管文件.docx", uploader=users["manager"], department=department_a, visibility=DocumentVisibility.DEPARTMENT),
            "outside_private": Document(filename="outside-private.docx", original_name="外部私有文件.docx", uploader=users["outside_employee"], department=department_b, visibility=DocumentVisibility.PRIVATE),
            "outside_company": Document(filename="outside-company.docx", original_name="公司文件.docx", uploader=users["outside_employee"], department=department_b, visibility=DocumentVisibility.COMPANY),
        }
        database.add_all(documents.values())
        database.commit()
        tokens = {role: create_access_token(users[role].id, users[role].token_version) for role in ("admin", "manager", "leader", "employee", "no_view")}
        document_ids = {name: document.id for name, document in documents.items()}

    chroma_documents = [
        {"document_id": document_id, "filename": documents[name].filename}
        for name, document_id in document_ids.items()
    ]
    chroma_documents.append({"document_id": "legacy-document", "filename": "legacy.docx"})
    monkeypatch.setattr(document_api, "list_documents", lambda: chroma_documents)

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, tokens
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _listed_filenames(client: TestClient, token: str) -> set[str]:
    response = client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    return {document["filename"] for document in response.json()["documents"]}


def test_employee_document_list_filter(document_list_context):
    client, tokens = document_list_context
    assert _listed_filenames(client, tokens["employee"]) == {
        "employee-own.docx",
        "employee-peer.docx",
        "manager-own.docx",
        "outside-company.docx",
    }


def test_leader_document_list_filter(document_list_context):
    client, tokens = document_list_context
    assert _listed_filenames(client, tokens["leader"]) == {
        "employee-peer.docx",
        "leader-own.docx",
        "manager-own.docx",
        "outside-company.docx",
    }


def test_manager_document_list_filter(document_list_context):
    client, tokens = document_list_context
    assert _listed_filenames(client, tokens["manager"]) == {
        "employee-own.docx",
        "employee-peer.docx",
        "leader-own.docx",
        "manager-own.docx",
        "outside-company.docx",
    }


def test_admin_document_list_only_includes_sql_backed_documents(document_list_context):
    client, tokens = document_list_context
    assert _listed_filenames(client, tokens["admin"]) == {
        "employee-own.docx",
        "employee-peer.docx",
        "leader-own.docx",
        "manager-own.docx",
        "outside-private.docx",
        "outside-company.docx",
    }


def test_document_list_requires_authentication(document_list_context):
    client, _ = document_list_context
    assert client.get("/documents").status_code == 401


def test_document_list_requires_file_view_permission(document_list_context):
    client, tokens = document_list_context
    response = client.get("/documents", headers={"Authorization": f"Bearer {tokens['no_view']}"})
    assert response.status_code == 403
