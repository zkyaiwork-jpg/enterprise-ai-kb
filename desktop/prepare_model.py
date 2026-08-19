import os
from pathlib import Path
import shutil


MODEL_ID = "BAAI/bge-small-zh-v1.5"
MODEL_CACHE_NAME = "models--BAAI--bge-small-zh-v1.5"
TARGET_HOME = Path(__file__).resolve().parent / "model-cache"
TARGET_MODEL = TARGET_HOME / "hub" / MODEL_CACHE_NAME


def prepare_model() -> None:
    if TARGET_MODEL.exists():
        print(f"Embedding model already prepared: {TARGET_MODEL}")
        return

    from huggingface_hub.constants import HF_HUB_CACHE

    source_model = Path(HF_HUB_CACHE) / MODEL_CACHE_NAME
    if source_model.exists():
        TARGET_MODEL.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_model, TARGET_MODEL)
        print(f"Copied cached embedding model to: {TARGET_MODEL}")
        return

    # Build machines without a local cache download once during packaging,
    # never during the end user's first desktop launch.
    os.environ["HF_HOME"] = str(TARGET_HOME)
    from sentence_transformers import SentenceTransformer

    SentenceTransformer(MODEL_ID)
    print(f"Downloaded embedding model to: {TARGET_MODEL}")


if __name__ == "__main__":
    prepare_model()
