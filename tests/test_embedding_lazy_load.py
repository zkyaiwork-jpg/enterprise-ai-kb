import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType


def test_fastapi_import_does_not_import_sentence_transformers(tmp_path):
    environment = os.environ.copy()
    environment["DEEPSEEK_API_KEY"] = "test-key-not-used"
    environment["APP_DATA_DIR"] = str(tmp_path / "data")
    environment["APP_LOG_DIR"] = str(tmp_path / "logs")

    script = """
import importlib.abc
import sys
from types import ModuleType

class SentenceTransformersBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "sentence_transformers" or fullname.startswith("sentence_transformers."):
            raise AssertionError("sentence-transformers imported during FastAPI startup")
        return None

class FakeCollection:
    def count(self): return 0
    def get(self, *args, **kwargs):
        return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}

class FakeClient:
    def __init__(self, *args, **kwargs): self.collection = FakeCollection()
    def get_or_create_collection(self, *args, **kwargs): return self.collection
    def get_collection(self, *args, **kwargs): return self.collection

fake_chromadb = ModuleType("chromadb")
fake_chromadb.PersistentClient = FakeClient
sys.modules["chromadb"] = fake_chromadb
sys.meta_path.insert(0, SentenceTransformersBlocker())

import app.main
print("fastapi import completed without embedding model")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert completed.returncode == 0, completed.stderr
    assert "fastapi import completed without embedding model" in completed.stdout


def test_first_encode_loads_model_and_later_calls_reuse_it(monkeypatch):
    from app.services import embedding_service

    class FakeSentenceTransformer:
        load_count = 0

        def __init__(self, model_name):
            assert model_name == embedding_service.MODEL_NAME
            type(self).load_count += 1

        def encode(self, texts):
            return [f"encoded:{text}" for text in texts]

    fake_module = ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setattr(embedding_service, "_model", None)

    first_result = embedding_service.encode_texts(["first"])
    first_model = embedding_service.get_embedding_model()
    second_result = embedding_service.encode_texts(["second"])
    second_model = embedding_service.get_embedding_model()

    assert first_result == ["encoded:first"]
    assert second_result == ["encoded:second"]
    assert first_model is second_model
    assert FakeSentenceTransformer.load_count == 1
