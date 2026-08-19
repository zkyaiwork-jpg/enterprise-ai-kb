import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_app_data_dir() -> Path:
    configured_dir = os.getenv("APP_DATA_DIR")
    if configured_dir:
        return Path(configured_dir).expanduser().resolve()
    return PROJECT_ROOT / "data"


APP_DATA_DIR = _resolve_app_data_dir()
VECTOR_DB_DIR = APP_DATA_DIR / "vector_db"
DOCUMENTS_DIR = APP_DATA_DIR / "documents"
CHAT_HISTORY_DB = APP_DATA_DIR / "chat_history.db"
LOG_DIR = APP_DATA_DIR / "logs"


def ensure_app_data_dirs() -> Path:
    """Create every writable application directory outside packaged resources."""
    for directory in (APP_DATA_DIR, VECTOR_DB_DIR, DOCUMENTS_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    return APP_DATA_DIR


ensure_app_data_dirs()
