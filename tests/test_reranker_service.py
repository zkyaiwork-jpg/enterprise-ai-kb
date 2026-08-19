import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def real_reranker_result():
    """Exercise the real dependency outside conftest's in-memory test double."""
    script = r'''
import json

from app.services.reranker_service import get_reranker, rerank_documents

first_model = get_reranker()
second_model = get_reranker()
documents = [
    {
        "content": "客户产品故障时，应先指导客户完成基础排查。",
        "filename": "售后规范.docx",
        "metadata": {"source": "test"},
    },
    {
        "content": "发现疑似病毒，应立即停止操作，并第一时间向负责人或技术人员报告。",
        "filename": "信息安全规范.docx",
        "metadata": {"source": "test"},
    },
]
ranked = rerank_documents("电脑中了病毒怎么办？", documents)
print(json.dumps({
    "model_type": type(first_model).__name__,
    "same_instance": first_model is second_model,
    "ranked": ranked,
    "inputs_unchanged": all("rerank_score" not in item for item in documents),
}, ensure_ascii=False))
'''
    environment = os.environ.copy()
    # The model was downloaded by the completed offline experiments. Keeping
    # this verification offline makes it deterministic and proves the cached
    # production model can be loaded without a network dependency.
    environment["HF_HUB_OFFLINE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_get_reranker_loads_cross_encoder(real_reranker_result):
    assert real_reranker_result["model_type"] == "CrossEncoder"


def test_rerank_documents_orders_more_relevant_content_first(real_reranker_result):
    result = real_reranker_result["ranked"]
    assert result[0]["filename"] == "信息安全规范.docx"
    assert result[1]["filename"] == "售后规范.docx"
    assert result[0]["rerank_score"] > result[1]["rerank_score"]
    assert result[0]["metadata"] == {"source": "test"}
    assert real_reranker_result["inputs_unchanged"] is True


@pytest.mark.parametrize("question", [None, "", "   "])
def test_rerank_documents_rejects_empty_question(question):
    from app.services.reranker_service import rerank_documents

    with pytest.raises(ValueError, match="question不能为空"):
        rerank_documents(question, [{"content": "valid"}])


def test_rerank_documents_returns_empty_list_without_loading_model(monkeypatch):
    from app.services import reranker_service

    monkeypatch.setattr(
        reranker_service,
        "get_reranker",
        lambda: pytest.fail("空文档列表不应调用模型"),
    )

    assert reranker_service.rerank_documents("question", []) == []


@pytest.mark.parametrize(
    ("documents", "message"),
    [
        ([{}], "缺少content字段"),
        ([{"content": ""}], "content不能为空"),
        ([{"content": "   "}], "content不能为空"),
    ],
)
def test_rerank_documents_rejects_missing_or_empty_content(documents, message):
    from app.services.reranker_service import rerank_documents

    with pytest.raises(ValueError, match=message):
        rerank_documents("question", documents)


def test_get_reranker_returns_same_instance(real_reranker_result):
    assert real_reranker_result["same_instance"] is True


def test_get_reranker_uses_experiment_configuration(monkeypatch):
    from app.services import reranker_service

    captured = {}

    class RecordingCrossEncoder:
        def __init__(self, model_name, **kwargs):
            captured["model_name"] = model_name
            captured.update(kwargs)

    fake_module = SimpleNamespace(CrossEncoder=RecordingCrossEncoder)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setattr(reranker_service, "_reranker", None)

    model = reranker_service.get_reranker()

    assert isinstance(model, RecordingCrossEncoder)
    assert captured == {
        "model_name": "BAAI/bge-reranker-base",
        "max_length": 512,
        "device": "cpu",
    }


def test_model_loading_error_preserves_cause(monkeypatch):
    from app.services import reranker_service

    class FailingCrossEncoder:
        def __init__(self, *args, **kwargs):
            raise OSError("model cache unavailable")

    fake_module = SimpleNamespace(CrossEncoder=FailingCrossEncoder)
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", fake_module)
    monkeypatch.setattr(reranker_service, "_reranker", None)

    with pytest.raises(reranker_service.RerankerLoadError) as exc_info:
        reranker_service.get_reranker()

    assert isinstance(exc_info.value.__cause__, OSError)


def test_model_inference_error_preserves_cause(monkeypatch):
    from app.services import reranker_service

    class FailingReranker:
        def predict(self, pairs):
            raise RuntimeError("prediction failed")

    monkeypatch.setattr(reranker_service, "get_reranker", lambda: FailingReranker())

    with pytest.raises(reranker_service.RerankerInferenceError) as exc_info:
        reranker_service.rerank_documents("question", [{"content": "content"}])

    assert isinstance(exc_info.value.__cause__, RuntimeError)
