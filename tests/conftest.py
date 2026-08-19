import os
import sys
import tempfile
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class FakeCollection:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self.deleted_ids: list[str] = []

    def add(self, ids, documents, metadatas, embeddings=None):
        for index, item_id in enumerate(ids):
            self.records[item_id] = {
                "document": documents[index],
                "metadata": metadatas[index],
                "embedding": embeddings[index] if embeddings is not None else None,
            }

    def delete(self, ids=None, where=None):
        target_ids = list(ids or [])
        if where:
            target_ids.extend(
                item_id
                for item_id, record in self.records.items()
                if all(record["metadata"].get(key) == value for key, value in where.items())
            )
        for item_id in set(target_ids):
            self.records.pop(item_id, None)
            self.deleted_ids.append(item_id)

    def get(self, ids=None, where=None, include=None):
        selected = []
        for item_id, record in self.records.items():
            if ids is not None and item_id not in ids:
                continue
            if where and not all(record["metadata"].get(key) == value for key, value in where.items()):
                continue
            selected.append((item_id, record))
        return {
            "ids": [item_id for item_id, _ in selected],
            "documents": [record["document"] for _, record in selected],
            "metadatas": [record["metadata"] for _, record in selected],
            "embeddings": [record["embedding"] for _, record in selected],
        }

    def query(self, **kwargs):
        return {"documents": [[]], "distances": [[]], "metadatas": [[]]}

    def count(self):
        return len(self.records)


class FakeChromaClient:
    def __init__(self, *args, **kwargs):
        self.collection = FakeCollection()

    def get_or_create_collection(self, *args, **kwargs):
        return self.collection

    def get_collection(self, *args, **kwargs):
        return self.collection


class FakeSentenceTransformer:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, values):
        class Encoded:
            def tolist(self):
                return [[0.0, 0.0] for _ in values]

        return Encoded()


# Install in-memory dependency doubles before app.main imports vector services.
fake_chromadb = ModuleType("chromadb")
fake_chromadb.PersistentClient = FakeChromaClient
sys.modules["chromadb"] = fake_chromadb

fake_transformers = ModuleType("sentence_transformers")
fake_transformers.SentenceTransformer = FakeSentenceTransformer
sys.modules["sentence_transformers"] = fake_transformers

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-not-used")
_test_app_data_dir = tempfile.mkdtemp(prefix="enterprise-ai-kb-test-data-")
os.environ.setdefault("APP_DATA_DIR", _test_app_data_dir)
os.environ.setdefault("APP_LOG_DIR", os.path.join(_test_app_data_dir, "logs"))


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def isolated_chat_db(tmp_path, monkeypatch):
    from app.services import chat_history_service

    database_path = tmp_path / "chat_history.db"
    monkeypatch.setattr(chat_history_service, "CHAT_HISTORY_DB", database_path)
    return database_path


@pytest.fixture
def authorized_client(monkeypatch):
    """Client backed by an isolated SQL database and a file_view user."""
    from app.auth.dependency import get_current_user
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models.role import Role
    from app.models.user import User

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
        user = User(
            username="api_test_employee",
            password_hash="not-used",
            real_name="API Test Employee",
            role_id=employee_role.id,
            status="active",
        )
        database.add(user)
        database.commit()
        database.refresh(user)
        user_id = user.id

    def override_get_db():
        with testing_session() as database:
            yield database

    def override_current_user():
        with testing_session() as database:
            yield database.get(User, user_id)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
