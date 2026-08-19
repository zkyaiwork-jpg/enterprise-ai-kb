import logging
from threading import Lock
from typing import Any, Sequence


MODEL_NAME = "BAAI/bge-small-zh-v1.5"
logger = logging.getLogger(__name__)

_model: Any | None = None
_model_lock = Lock()


def get_embedding_model() -> Any:
    """Load the embedding model on first use and reuse it for this process."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("Embedding model loading model=%s", MODEL_NAME)
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME)
                logger.info("Embedding model loaded model=%s", MODEL_NAME)
    return _model


def encode_texts(texts: Sequence[str]):
    return get_embedding_model().encode(list(texts))
