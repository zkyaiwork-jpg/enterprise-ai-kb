import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_fastapi_lifespan_loads_and_warms_reranker(monkeypatch):
    from app import main

    calls = []
    monkeypatch.setattr(
        main.reranker_service,
        "load_reranker",
        lambda: calls.append("load") or object(),
    )
    monkeypatch.setattr(
        main.reranker_service,
        "warmup_reranker",
        lambda: calls.append("warmup"),
    )

    with TestClient(main.app) as client:
        assert client.get("/").status_code == 200

    assert calls == ["load", "warmup"]


def test_warmup_reranker_runs_prediction_and_marks_ready(monkeypatch):
    from app.services import reranker_service

    captured = {}

    class RecordingReranker:
        def predict(self, pairs):
            captured["pairs"] = pairs
            return [0.5]

    monkeypatch.setattr(reranker_service, "_reranker", RecordingReranker())
    monkeypatch.setattr(reranker_service, "_reranker_ready", False)
    monkeypatch.setattr(reranker_service, "_reranker_error", "PreviousError")

    reranker_service.warmup_reranker()

    assert captured["pairs"] == [("测试问题", "测试文本")]
    assert reranker_service.get_reranker_status() == {
        "reranker_ready": True,
        "reranker_error": None,
    }


def test_reranker_load_failure_keeps_fastapi_available_and_marks_degraded(
    monkeypatch,
):
    from app import main

    monkeypatch.setattr(main.reranker_service, "_reranker_ready", True)
    monkeypatch.setattr(main.reranker_service, "_reranker_error", None)

    def failing_load():
        raise OSError("model file unavailable")

    monkeypatch.setattr(main.reranker_service, "load_reranker", failing_load)
    monkeypatch.setattr(
        main.reranker_service,
        "warmup_reranker",
        lambda: (_ for _ in ()).throw(
            AssertionError("warmup must not run after loading fails")
        ),
    )

    with TestClient(main.app) as client:
        response = client.get("/")
        status = main.reranker_service.get_reranker_status()

    assert response.status_code == 200
    assert status == {
        "reranker_ready": False,
        "reranker_error": "OSError",
    }


def test_first_search_after_lifespan_reuses_warmed_model(monkeypatch):
    from app import main
    from app.services import reranker_service, search_service

    counters = {"loads": 0, "predictions": 0}

    class RecordingCrossEncoder:
        def __init__(self, model_name, **kwargs):
            counters["loads"] += 1

        def predict(self, pairs):
            counters["predictions"] += 1
            return [0.5 for _ in pairs]

    monkeypatch.setattr(
        sys.modules["sentence_transformers"],
        "CrossEncoder",
        RecordingCrossEncoder,
        raising=False,
    )
    monkeypatch.setattr(reranker_service, "_reranker", None)
    monkeypatch.setattr(reranker_service, "_reranker_ready", False)
    monkeypatch.setattr(reranker_service, "_reranker_error", None)
    monkeypatch.setattr(
        search_service,
        "encode_texts",
        lambda values: SimpleNamespace(tolist=lambda: [[0.0, 0.0]]),
    )

    class OneResultCollection:
        def query(self, **kwargs):
            return {
                "documents": [["authorized content"]],
                "distances": [[0.2]],
                "metadatas": [[{"document_id": 1, "filename": "allowed.docx"}]],
            }

    monkeypatch.setattr(search_service, "collection", OneResultCollection())

    with TestClient(main.app):
        assert reranker_service.get_reranker_status()["reranker_ready"] is True
        result = search_service.search_documents(
            "first request",
            allowed_document_ids={1},
        )

    assert result["results"][0]["filename"] == "allowed.docx"
    assert counters == {
        "loads": 1,
        # One startup warmup plus one first-search inference.
        "predictions": 2,
    }
