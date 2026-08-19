from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class MutationCollection:
    def __init__(self, records):
        self.records = records

    @staticmethod
    def _matches(metadata, where):
        return all(metadata.get(key) == value for key, value in (where or {}).items())

    def get(self, ids=None, where=None, include=None):
        selected = [
            (item_id, record) for item_id, record in self.records.items()
            if (ids is None or item_id in ids) and self._matches(record["metadata"], where)
        ]
        return {
            "ids": [item_id for item_id, _ in selected],
            "documents": [record["document"] for _, record in selected],
            "metadatas": [record["metadata"].copy() for _, record in selected],
            "embeddings": [record["embedding"] for _, record in selected],
        }

    def delete(self, ids):
        for item_id in ids:
            self.records.pop(item_id, None)

    def add(self, ids, documents, metadatas, embeddings=None):
        for index, item_id in enumerate(ids):
            self.records[item_id] = {
                "document": documents[index],
                "metadata": metadatas[index].copy(),
                "embedding": embeddings[index] if embeddings is not None else None,
            }

    def update(self, ids, metadatas):
        for index, item_id in enumerate(ids):
            self.records[item_id]["metadata"] = metadatas[index].copy()


@pytest.fixture
def mutation_context(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "document-mutation-test-secret-long-enough")

    from app.auth.jwt import create_access_token
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models import Department, Document, DocumentVisibility, Permission, Role, Team, User
    from app.services import document_mutation_service

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
        no_delete = Role(name="editor_without_delete", description="test")
        no_delete.permissions.append(database.scalar(select(Permission).where(Permission.code == "file_edit")))
        no_edit = Role(name="deleter_without_edit", description="test")
        no_edit.permissions.append(database.scalar(select(Permission).where(Permission.code == "file_delete")))
        departments = {"a": Department(name="A"), "b": Department(name="B")}
        database.add_all([no_delete, no_edit, *departments.values()])
        database.flush()
        team_a = Team(name="Team A", department=departments["a"])
        team_a2 = Team(name="Team A2", department=departments["a"])
        team_b = Team(name="Team B", department=departments["b"])
        database.add(team_a2)
        users = {
            "employee": User(username="mut_employee", password_hash="x", real_name="Employee", role=roles["employee"], department=departments["a"]),
            "employee2": User(username="mut_employee2", password_hash="x", real_name="Employee2", role=roles["employee"], department=departments["a"], team=team_a),
            "outside_employee": User(username="mut_outside", password_hash="x", real_name="Outside", role=roles["employee"], department=departments["b"], team=team_b),
            "leader": User(username="mut_leader", password_hash="x", real_name="Leader", role=roles["leader"], department=departments["a"], team=team_a),
            "manager": User(username="mut_manager", password_hash="x", real_name="Manager", role=roles["manager"], department=departments["a"]),
            "admin": User(username="mut_admin", password_hash="x", real_name="Admin", role=roles["admin"]),
            "no_delete": User(username="mut_no_delete", password_hash="x", real_name="NoDelete", role=no_delete),
            "no_edit": User(username="mut_no_edit", password_hash="x", real_name="NoEdit", role=no_edit),
        }
        database.add_all(users.values())
        database.flush()
        documents = {
            "leader_own": Document(filename="leader.docx", original_name="leader.docx", uploader=users["leader"], department=departments["a"], visibility=DocumentVisibility.PRIVATE),
            "employee": Document(filename="employee.docx", original_name="employee.docx", uploader=users["employee2"], department=departments["a"], team=team_a, visibility=DocumentVisibility.PRIVATE),
            "manager": Document(filename="manager.docx", original_name="manager.docx", uploader=users["manager"], department=departments["a"], visibility=DocumentVisibility.PRIVATE),
            "outside": Document(filename="outside.docx", original_name="outside.docx", uploader=users["outside_employee"], department=departments["b"], visibility=DocumentVisibility.PRIVATE),
        }
        database.add_all(documents.values())
        database.commit()
        ids = {name: document.id for name, document in documents.items()}
        tokens = {name: create_access_token(user.id, user.token_version) for name, user in users.items()}

    records = {}
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    for name, document_id in ids.items():
        filename = f"{name.replace('_own', '')}.docx"
        (documents_dir / filename).write_bytes(b"source")
        records[f"{document_id}:0"] = {
            "document": f"content-{name}",
            "metadata": {"document_id": document_id, "filename": filename, "visibility": "private", "chunk_index": 0},
            "embedding": [0.1, 0.2],
        }
    collection = MutationCollection(records)
    monkeypatch.setattr(document_mutation_service, "collection", collection)
    monkeypatch.setattr(document_mutation_service, "UPLOAD_DIR", documents_dir)

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, tokens, ids, testing_session, collection, documents_dir
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("actor", "filename", "expected"),
    [
        ("employee", "employee.docx", 403),
        ("leader", "leader.docx", 200),
        ("leader", "employee.docx", 200),
        ("leader", "manager.docx", 403),
        ("leader", "outside.docx", 403),
        ("manager", "employee.docx", 200),
        ("manager", "outside.docx", 403),
        ("admin", "outside.docx", 200),
    ],
)
def test_delete_rbac_and_document_scope(mutation_context, actor, filename, expected):
    client, tokens, ids, testing_session, collection, documents_dir = mutation_context
    from app.models.document import Document

    document_id = ids["leader_own" if filename == "leader.docx" else filename.removesuffix(".docx")]
    response = client.delete(f"/documents/{filename}", headers=_headers(tokens[actor]))
    assert response.status_code == expected
    with testing_session() as database:
        exists = database.get(Document, document_id) is not None
    if expected == 200:
        assert not exists
        assert collection.get(where={"document_id": document_id})["ids"] == []
        assert not (documents_dir / filename).exists()
        with testing_session() as database:
            from app.models.audit_log import AuditLog
            audit = database.scalar(select(AuditLog).where(
                AuditLog.action == "document_delete",
                AuditLog.result == "success",
            ))
            assert audit is not None
            assert audit.resource_id == str(document_id)
            assert audit.resource_name == filename
    else:
        assert exists
        assert collection.get(where={"document_id": document_id})["ids"]


def test_employee_cannot_edit_document(mutation_context):
    client, tokens, ids, _, _, _ = mutation_context
    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens["employee"]),
        json={"visibility": "company"},
    )
    assert response.status_code == 403


def test_visibility_update_synchronizes_sql_and_chroma(mutation_context):
    client, tokens, ids, testing_session, collection, _ = mutation_context
    from app.models.document import Document, DocumentVisibility

    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens["manager"]),
        json={"visibility": "company", "original_name": "Updated employee policy.docx"},
    )
    assert response.status_code == 200
    assert response.json()["updated_time"].endswith("Z")
    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        assert document.visibility is DocumentVisibility.COMPANY
        assert document.original_name == "Updated employee policy.docx"
    metadata = collection.get(where={"document_id": ids["employee"]})["metadatas"]
    assert metadata and {item["visibility"] for item in metadata} == {"company"}
    with testing_session() as database:
        from app.models.audit_log import AuditLog
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "document_update"))
        assert audit is not None
        assert audit.resource_id == str(ids["employee"])
        assert "visibility:private->company" in audit.detail


def test_team_visibility_repairs_final_department_and_chroma_without_new_team_id(mutation_context):
    client, tokens, ids, testing_session, collection, _ = mutation_context
    from app.models import Department, Document, DocumentVisibility, Team

    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        department_b = database.query(Department).filter_by(name="B").one()
        team_b = database.query(Team).filter_by(name="Team B").one()
        document.department_id = department_b.id - 1
        document.team_id = team_b.id
        database.commit()
        expected_department_id = team_b.department_id
        expected_team_id = team_b.id
    for metadata in collection.get(where={"document_id": ids["employee"]})["metadatas"]:
        metadata["department_id"] = expected_department_id - 1
        metadata["team_id"] = expected_team_id
        metadata["visibility"] = "private"
    for record in collection.records.values():
        if record["metadata"].get("document_id") == ids["employee"]:
            record["metadata"]["department_id"] = expected_department_id - 1
            record["metadata"]["team_id"] = expected_team_id

    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens["admin"]),
        json={"visibility": "team"},
    )
    assert response.status_code == 200
    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        assert document.visibility is DocumentVisibility.TEAM
        assert document.team_id == expected_team_id
        assert document.department_id == expected_department_id
    metadata = collection.get(where={"document_id": ids["employee"]})["metadatas"]
    assert metadata
    assert {(item["visibility"], item["team_id"], item["department_id"]) for item in metadata} == {
        ("team", expected_team_id, expected_department_id)
    }


def test_non_team_patch_rejects_explicit_team_id_without_writes(mutation_context):
    client, tokens, ids, testing_session, collection, _ = mutation_context
    from app.models import Document, Team

    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        team_b = database.scalar(select(Team).where(Team.name == "Team B"))
        original = (document.team_id, document.department_id, document.visibility.value)
        target_team_id = team_b.id
    original_metadata = collection.get(where={"document_id": ids["employee"]})["metadatas"]

    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens["leader"]),
        json={"team_id": target_team_id},
    )

    assert response.status_code == 400
    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        assert (document.team_id, document.department_id, document.visibility.value) == original
    assert collection.get(where={"document_id": ids["employee"]})["metadatas"] == original_metadata


@pytest.mark.parametrize("actor", ["leader", "manager", "admin"])
def test_non_team_visibility_rejects_team_id_for_every_editor(mutation_context, actor):
    client, tokens, ids, testing_session, collection, _ = mutation_context
    from app.models import Document, Team

    with testing_session() as database:
        team_a = database.scalar(select(Team).where(Team.name == "Team A"))
        document = database.get(Document, ids["employee"])
        original = (document.team_id, document.department_id, document.visibility.value)
    original_metadata = collection.get(where={"document_id": ids["employee"]})["metadatas"]
    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens[actor]),
        json={"visibility": "private", "team_id": team_a.id},
    )
    assert response.status_code == 400
    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        assert (document.team_id, document.department_id, document.visibility.value) == original
    assert collection.get(where={"document_id": ids["employee"]})["metadatas"] == original_metadata


@pytest.mark.parametrize(
    ("actor", "team_name", "expected"),
    [
        ("leader", "Team A", 200),
        ("leader", "Team A2", 403),
        ("manager", "Team A2", 200),
        ("manager", "Team B", 403),
        ("admin", "Team B", 200),
    ],
)
def test_team_target_scope_and_metadata_sync(mutation_context, actor, team_name, expected):
    client, tokens, ids, testing_session, collection, _ = mutation_context
    from app.models import Document, DocumentVisibility, Team

    with testing_session() as database:
        target_team = database.scalar(select(Team).where(Team.name == team_name))
        target_team_id = target_team.id
        target_department_id = target_team.department_id
    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens[actor]),
        json={"visibility": "team", "team_id": target_team_id},
    )
    assert response.status_code == expected
    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        if expected == 200:
            assert document.visibility is DocumentVisibility.TEAM
            assert document.team_id == target_team_id
            assert document.department_id == target_department_id
        else:
            assert document.visibility is DocumentVisibility.PRIVATE
    metadata = collection.get(where={"document_id": ids["employee"]})["metadatas"]
    if expected == 200:
        assert {(item["visibility"], item["team_id"], item["department_id"]) for item in metadata} == {
            ("team", target_team_id, target_department_id)
        }
    else:
        assert {item["visibility"] for item in metadata} == {"private"}


@pytest.mark.parametrize(("visibility", "expected"), [("team", 200), ("department", 403), ("company", 403)])
def test_leader_visibility_publish_scope(mutation_context, visibility, expected):
    client, tokens, ids, testing_session, collection, _ = mutation_context
    from app.models.document import Document

    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens["leader"]),
        json={"visibility": visibility},
    )
    assert response.status_code == expected
    with testing_session() as database:
        stored = database.get(Document, ids["employee"]).visibility.value
    metadata = collection.get(where={"document_id": ids["employee"]})["metadatas"]
    if expected == 200:
        assert stored == visibility
        assert {item["visibility"] for item in metadata} == {visibility}
    else:
        assert stored == "private"
        assert {item["visibility"] for item in metadata} == {"private"}


def test_name_only_patch_does_not_require_existing_visibility_publish_permission(mutation_context):
    client, tokens, ids, testing_session, _, _ = mutation_context
    from app.models.document import Document, DocumentVisibility
    with testing_session() as database:
        document = database.get(Document, ids["employee"])
        document.visibility = DocumentVisibility.COMPANY
        database.commit()
    response = client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens["leader"]),
        json={"original_name": "Renamed only.docx"},
    )
    assert response.status_code == 200


def test_missing_token_and_missing_function_permissions(mutation_context):
    client, tokens, ids, _, _, _ = mutation_context
    assert client.delete("/documents/employee.docx").status_code == 401
    assert client.patch(f"/documents/{ids['employee']}", json={"visibility": "company"}).status_code == 401
    assert client.delete(
        "/documents/employee.docx", headers=_headers(tokens["no_delete"]),
    ).status_code == 403
    assert client.patch(
        f"/documents/{ids['employee']}",
        headers=_headers(tokens["no_edit"]),
        json={"visibility": "company"},
    ).status_code == 403


def test_chroma_only_legacy_document_cannot_be_deleted(mutation_context):
    client, tokens, _, _, collection, documents_dir = mutation_context
    collection.records["legacy:0"] = {
        "document": "legacy",
        "metadata": {"document_id": "legacy", "filename": "legacy.docx"},
        "embedding": [0.0],
    }
    (documents_dir / "legacy.docx").write_bytes(b"legacy")
    response = client.delete("/documents/legacy.docx", headers=_headers(tokens["admin"]))
    assert response.status_code == 404
    assert collection.get(ids=["legacy:0"])["ids"] == ["legacy:0"]
    assert (documents_dir / "legacy.docx").exists()
