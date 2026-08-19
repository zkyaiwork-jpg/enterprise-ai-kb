import logging
from threading import Lock
from typing import Any


MODEL_NAME = "BAAI/bge-reranker-base"
MAX_LENGTH = 512
DEVICE = "cpu"

logger = logging.getLogger(__name__)

_reranker: Any | None = None
_reranker_lock = Lock()
_reranker_ready = False
_reranker_error: str | None = None


class RerankerLoadError(RuntimeError):
    """Raised when the CrossEncoder model cannot be loaded."""


class RerankerInferenceError(RuntimeError):
    """Raised when the CrossEncoder model cannot score documents."""


def mark_reranker_unavailable(error: BaseException) -> None:
    """Record degraded state without retaining sensitive exception details."""
    global _reranker_ready, _reranker_error
    _reranker_ready = False
    _reranker_error = type(error).__name__


def get_reranker_status() -> dict[str, bool | str | None]:
    """Return a non-sensitive snapshot of the process-local Reranker state."""
    return {
        "reranker_ready": _reranker_ready,
        "reranker_error": _reranker_error,
    }


def get_reranker() -> Any:
    """Load the CrossEncoder on first use and reuse it for this process."""
    global _reranker
    if _reranker is None:
        with _reranker_lock:
            if _reranker is None:
                logger.info("Reranker model loading model=%s", MODEL_NAME)
                try:
                    from sentence_transformers import CrossEncoder

                    _reranker = CrossEncoder(
                        MODEL_NAME,
                        max_length=MAX_LENGTH,
                        device=DEVICE,
                    )
                except Exception as exc:
                    mark_reranker_unavailable(exc)
                    logger.error(
                        "Reranker model loading failed model=%s error_type=%s",
                        MODEL_NAME,
                        type(exc).__name__,
                    )
                    raise RerankerLoadError(
                        f"Reranker模型加载失败: {MODEL_NAME}"
                    ) from exc
                logger.info("Reranker model loaded model=%s", MODEL_NAME)
    return _reranker


def load_reranker() -> Any:
    """Proactively load and cache the process-local Reranker model."""
    global _reranker_error
    model = get_reranker()
    _reranker_error = None
    return model


def _validate_inputs(question: str, documents: list[dict]) -> None:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question不能为空")
    if not isinstance(documents, list):
        raise TypeError("documents必须是list[dict]")

    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise TypeError(f"documents[{index}]必须是dict")
        if "content" not in document:
            raise ValueError(f"documents[{index}]缺少content字段")
        content = document["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"documents[{index}].content不能为空")


def rerank_documents(question: str, documents: list[dict]) -> list[dict]:
    """Return copies of documents sorted by descending CrossEncoder score."""
    _validate_inputs(question, documents)
    if not documents:
        return []

    pairs = [(question, document["content"]) for document in documents]
    try:
        raw_scores = get_reranker().predict(pairs)
        scores = raw_scores.tolist() if hasattr(raw_scores, "tolist") else list(raw_scores)
        if len(scores) != len(documents):
            raise ValueError(
                f"Reranker返回的score数量与文档数量不一致: "
                f"{len(scores)} != {len(documents)}"
            )
        ranked_documents = [
            {**document, "rerank_score": float(score)}
            for document, score in zip(documents, scores)
        ]
    except RerankerLoadError:
        raise
    except Exception as exc:
        mark_reranker_unavailable(exc)
        logger.error(
            "Reranker inference failed model=%s document_count=%s error_type=%s",
            MODEL_NAME,
            len(documents),
            type(exc).__name__,
        )
        raise RerankerInferenceError("Reranker模型推理失败") from exc

    return sorted(
        ranked_documents,
        key=lambda document: document["rerank_score"],
        reverse=True,
    )


def warmup_reranker() -> None:
    """Run one synthetic prediction and mark the process Reranker as ready."""
    global _reranker_ready, _reranker_error
    rerank_documents(
        "测试问题",
        [{"content": "测试文本"}],
    )
    _reranker_ready = True
    _reranker_error = None
