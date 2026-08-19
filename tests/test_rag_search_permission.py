from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def permission_search_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "rag-search-permission-test-secret")

    from app.auth.jwt import create_access_token
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models import Department, Document, Role, Team, User
    from app.models.document import DocumentVisibility

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
        department_a = Department(name="Department A")
        department_b = Department(name="Department B")
        database.add_all([department_a, department_b])
        database.flush()
        team_a = Team(name="Team A", department=department_a)

        users = {
            "employee": User(username="employee_a", password_hash="x", real_name="Employee A", role=roles["employee"], department=department_a, team=team_a),
            "employee_other": User(username="employee_a2", password_hash="x", real_name="Employee A2", role=roles["employee"], department=department_a, team=team_a),
            "leader": User(username="leader_a", password_hash="x", real_name="Leader A", role=roles["leader"], department=department_a, team=team_a),
            "manager": User(username="manager_a", password_hash="x", real_name="Manager A", role=roles["manager"], department=department_a),
            "manager_other": User(username="manager_b", password_hash="x", real_name="Manager B", role=roles["manager"], department=department_b),
            "admin": User(username="admin", password_hash="x", real_name="Admin", role=roles["admin"]),
        }
        database.add_all(users.values())
        database.flush()

        documents = {
            "own_private": Document(filename="own.docx", original_name="own.docx", uploader=users["employee"], department=department_a, team=team_a, visibility=DocumentVisibility.PRIVATE),
            "other_employee_private": Document(filename="employee-other.docx", original_name="employee-other.docx", uploader=users["employee_other"], department=department_a, team=team_a, visibility=DocumentVisibility.PRIVATE),
            "company": Document(filename="company.docx", original_name="company.docx", uploader=users["manager_other"], department=department_b, visibility=DocumentVisibility.COMPANY),
            "manager_private": Document(filename="manager.docx", original_name="manager.docx", uploader=users["manager"], department=department_a, visibility=DocumentVisibility.PRIVATE),
            "other_department_private": Document(filename="other-department.docx", original_name="other-department.docx", uploader=users["manager_other"], department=department_b, visibility=DocumentVisibility.PRIVATE),
        }
        database.add_all(documents.values())
        database.commit()
        user_ids = {name: user.id for name, user in users.items()}
        document_ids = {name: document.id for name, document in documents.items()}

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(
                client=client,
                session=testing_session,
                user_ids=user_ids,
                document_ids=document_ids,
                tokens={name: create_access_token(user_id, 1) for name, user_id in user_ids.items()},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.mark.parametrize(
    ("user_name", "visible", "hidden"),
    [
        ("employee", {"own_private", "company"}, {"other_employee_private"}),
        ("leader", {"own_private", "other_employee_private", "company"}, {"manager_private"}),
        ("manager", {"own_private", "other_employee_private", "manager_private", "company"}, {"other_department_private"}),
    ],
)
def test_non_admin_search_scope_reuses_document_permissions(permission_search_context, user_name, visible, hidden):
    from app.models.user import User
    from app.services.document_permission import accessible_document_ids

    context = permission_search_context
    with context.session() as database:
        user = database.get(User, context.user_ids[user_name])
        allowed_ids = accessible_document_ids(database, user)

    assert {context.document_ids[name] for name in visible}.issubset(allowed_ids)
    assert {context.document_ids[name] for name in hidden}.isdisjoint(allowed_ids)


def test_admin_scope_is_explicit_and_only_includes_sql_documents(permission_search_context):
    from app.models.user import User
    from app.services.document_permission import accessible_document_ids

    context = permission_search_context
    with context.session() as database:
        admin = database.get(User, context.user_ids["admin"])
        allowed_ids = accessible_document_ids(database, admin)
        assert allowed_ids == set(context.document_ids.values())


class RecordingCollection:
    def __init__(self):
        self.query_calls = []

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return {
            "documents": [["permitted content"]],
            "distances": [[0.1]],
            "metadatas": [[{"document_id": 7, "filename": "allowed.docx", "chunk_index": 0}]],
        }


def test_chroma_receives_document_allow_list_before_similarity_search(monkeypatch):
    from app.services import search_service

    collection = RecordingCollection()
    monkeypatch.setattr(search_service, "collection", collection)
    monkeypatch.setattr(search_service, "encode_texts", lambda values: SimpleNamespace(tolist=lambda: [[0.0, 0.0]]))

    result = search_service.search_documents("policy", allowed_document_ids={9, 7})

    assert result["results"][0]["filename"] == "allowed.docx"
    assert collection.query_calls[0]["where"] == {"document_id": {"$in": [7, 9]}}


def test_search_discards_chroma_results_outside_allowed_ids(monkeypatch):
    from app.services import search_service

    class BrokenFilterCollection:
        def query(self, **kwargs):
            return {
                "documents": [["allowed content", "forbidden content"]],
                "distances": [[0.1, 0.1]],
                "metadatas": [[
                    {"document_id": 1, "filename": "allowed.docx"},
                    {"document_id": 999, "filename": "forbidden.docx"},
                ]],
            }

    monkeypatch.setattr(search_service, "collection", BrokenFilterCollection())
    monkeypatch.setattr(search_service, "encode_texts", lambda values: SimpleNamespace(tolist=lambda: [[0.0, 0.0]]))

    result = search_service.search_documents("policy", allowed_document_ids={1})
    assert [item["filename"] for item in result["results"]] == ["allowed.docx"]


def test_out_of_scope_chroma_result_cannot_reach_rag_sources_or_prompt(monkeypatch):
    from app.services import rag_service, search_service

    class BrokenFilterCollection:
        def query(self, **kwargs):
            return {
                "documents": [["allowed prompt content", "forbidden prompt content"]],
                "distances": [[0.1, 0.1]],
                "metadatas": [[
                    {"document_id": 1, "filename": "allowed.docx"},
                    {"document_id": 999, "filename": "forbidden.docx"},
                ]],
            }

    captured = {}
    monkeypatch.setattr(search_service, "collection", BrokenFilterCollection())
    monkeypatch.setattr(search_service, "encode_texts", lambda values: SimpleNamespace(tolist=lambda: [[0.0, 0.0]]))
    monkeypatch.setattr(rag_service, "resolve_runtime_model_config", lambda database: SimpleNamespace(provider="test", model_name="test", source="test"))
    monkeypatch.setattr(rag_service, "create_model_client", lambda config: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: (
            captured.update(kwargs) or SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))])
        )))
    ))

    result = rag_service.ask_ai("policy?", allowed_document_ids={1}, database=object())
    prompt = "\n".join(str(message["content"]) for message in captured["messages"])
    assert [source["filename"] for source in result["sources"]] == ["allowed.docx"]
    assert "allowed prompt content" in prompt
    assert "forbidden prompt content" not in prompt


def test_empty_permission_scope_skips_embedding_and_chroma(monkeypatch):
    from app.services import search_service

    collection = RecordingCollection()
    monkeypatch.setattr(search_service, "collection", collection)
    monkeypatch.setattr(search_service, "encode_texts", lambda values: pytest.fail("embedding must not run"))

    assert search_service.search_documents("policy", allowed_document_ids=set()) == {"results": []}
    assert collection.query_calls == []


def test_missing_permission_scope_is_fail_closed(monkeypatch):
    from app.services import search_service

    collection = RecordingCollection()
    monkeypatch.setattr(search_service, "collection", collection)
    monkeypatch.setattr(search_service, "encode_texts", lambda values: pytest.fail("embedding must not run"))

    assert search_service.search_documents("policy", allowed_document_ids=None) == {"results": []}
    assert collection.query_calls == []


def test_admin_chroma_query_uses_sql_ids_and_excludes_orphan_chunk(monkeypatch, permission_search_context):
    from app.models.user import User
    from app.services import search_service
    from app.services.document_permission import accessible_document_ids

    context = permission_search_context
    with context.session() as database:
        admin = database.get(User, context.user_ids["admin"])
        allowed_ids = accessible_document_ids(database, admin)

    collection = RecordingCollection()
    monkeypatch.setattr(search_service, "collection", collection)
    monkeypatch.setattr(search_service, "encode_texts", lambda values: SimpleNamespace(tolist=lambda: [[0.0, 0.0]]))
    search_service.search_documents("policy", allowed_document_ids=allowed_ids)

    assert collection.query_calls[0]["where"] == {
        "document_id": {"$in": sorted(context.document_ids.values())}
    }
    assert 999999 not in allowed_ids


def test_admin_orphan_chunk_cannot_reach_rag_result_or_prompt(monkeypatch, permission_search_context):
    from app.models.user import User
    from app.services import rag_service, search_service
    from app.services.document_permission import accessible_document_ids

    context = permission_search_context
    with context.session() as database:
        admin = database.get(User, context.user_ids["admin"])
        allowed_ids = accessible_document_ids(database, admin)

    allowed_id = next(iter(allowed_ids))

    class ScopedCollection:
        def query(self, **kwargs):
            requested = set(kwargs["where"]["document_id"]["$in"])
            records = [
                (allowed_id, "allowed SQL content", "allowed.docx"),
                (999999, "orphan secret content", "orphan.docx"),
            ]
            selected = [record for record in records if record[0] in requested]
            return {
                "documents": [[record[1] for record in selected]],
                "distances": [[0.1 for _ in selected]],
                "metadatas": [[{"document_id": record[0], "filename": record[2]} for record in selected]],
            }

    captured = {}
    monkeypatch.setattr(search_service, "collection", ScopedCollection())
    monkeypatch.setattr(search_service, "encode_texts", lambda values: SimpleNamespace(tolist=lambda: [[0.0, 0.0]]))
    monkeypatch.setattr(rag_service, "resolve_runtime_model_config", lambda database: SimpleNamespace(provider="test", model_name="test", source="test"))
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: (
        captured.update(kwargs) or SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))])
    ))))
    monkeypatch.setattr(rag_service, "create_model_client", lambda config: fake_client)

    result = rag_service.ask_ai("policy?", allowed_document_ids=allowed_ids, database=object())
    prompt = "\n".join(str(message["content"]) for message in captured["messages"])
    assert [source["filename"] for source in result["sources"]] == ["allowed.docx"]
    assert "allowed SQL content" in prompt
    assert "orphan secret content" not in prompt


def test_sql_deleted_chroma_residue_is_not_in_admin_scope(permission_search_context):
    from app.models.document import Document
    from app.models.user import User
    from app.services.document_permission import accessible_document_ids

    context = permission_search_context
    deleted_id = context.document_ids["other_department_private"]
    with context.session() as database:
        database.delete(database.get(Document, deleted_id))
        database.commit()
    with context.session() as database:
        admin = database.get(User, context.user_ids["admin"])
        assert deleted_id not in accessible_document_ids(database, admin)


def test_empty_rag_scope_does_not_call_model(monkeypatch):
    from app.services import rag_service

    monkeypatch.setattr(rag_service, "search_documents", lambda *args, **kwargs: {"results": []})
    monkeypatch.setattr(rag_service, "create_model_client", lambda config: pytest.fail("LLM must not run"))
    result = rag_service.ask_ai("policy?", allowed_document_ids=set())
    assert result == {"answer": "知识库中没有找到相关资料。", "sources": []}


def test_rag_passes_scope_to_search_and_only_uses_returned_chunks(monkeypatch):
    from app.services import rag_service

    captured = {}

    def scoped_search(question, **kwargs):
        captured["allowed_document_ids"] = kwargs["allowed_document_ids"]
        return {"results": [{
            "content": "permitted policy",
            "filename": "allowed.docx",
            "chunk_index": 1,
            "distance": 0.1,
        }]}

    def completion(**kwargs):
        captured["messages"] = kwargs["messages"]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Allowed answer"))])

    monkeypatch.setattr(rag_service, "search_documents", scoped_search)
    monkeypatch.setattr(rag_service, "create_model_client", lambda config: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))))

    result = rag_service.ask_ai("policy?", allowed_document_ids={7})

    assert captured["allowed_document_ids"] == {7}
    prompt = "\n".join(str(message["content"]) for message in captured["messages"])
    assert "permitted policy" in prompt
    assert "forbidden policy" not in prompt
    assert [source["filename"] for source in result["sources"]] == ["allowed.docx"]


def test_chat_requires_token(client):
    response = client.post("/chat", json={"question": "policy?"})
    assert response.status_code == 401


def test_search_and_chat_require_file_view_permission(permission_search_context):
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.user import User

    context = permission_search_context
    with context.session() as database:
        role = Role(name="no_file_view", description="No file view")
        upload = database.scalar(select(Permission).where(Permission.code == "file_upload"))
        role.permissions.append(upload)
        user = User(username="no_view", password_hash="x", real_name="No View", role=role, status="active")
        database.add(user)
        database.commit()
        database.refresh(user)
        token = __import__("app.auth.jwt", fromlist=["create_access_token"]).create_access_token(user.id, user.token_version)

    headers = {"Authorization": f"Bearer {token}"}
    search_response = context.client.get(
        "/search",
        headers=headers,
        params={"query": "policy"},
    )
    chat_response = context.client.post(
        "/chat",
        headers=headers,
        json={"question": "policy?"},
    )
    assert search_response.status_code == 403
    assert chat_response.status_code == 403


def test_employee_seed_includes_upload_and_view(permission_search_context):
    from app.models.role import Role

    with permission_search_context.session() as database:
        employee = database.scalar(select(Role).where(Role.name == "employee"))
        assert {permission.code for permission in employee.permissions} >= {"file_upload", "file_view"}
