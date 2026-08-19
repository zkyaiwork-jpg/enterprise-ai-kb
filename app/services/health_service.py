import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from app.services.chat_history_service import CHAT_HISTORY_DB, init_chat_history_db
from app.services.vector_store import client


COLLECTION_NAME = "enterprise_documents"


def _check_vector_db() -> str:
    """Confirm the configured collection exists and accepts a read operation."""
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        collection.count()
        return "ok"
    except Exception:
        return "error"


def _check_chat_db() -> str:
    """Initialize the lazy SQLite store, then verify its file and table are readable."""
    database_path = Path(CHAT_HISTORY_DB)

    try:
        # Chat history uses lazy initialization, so an empty installation is healthy
        # once its database and schema can be created successfully.
        init_chat_history_db()
        if not database_path.is_file():
            return "error"
        database_uri = f"{database_path.resolve().as_uri()}?mode=rw"
        with sqlite3.connect(database_uri, uri=True, timeout=5) as connection:
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'chat_history'"
            ).fetchone()
        return "ok" if row else "error"
    except (OSError, sqlite3.Error):
        return "error"


def get_health_status() -> dict[str, str]:
    """Return dependency health without making a billable AI provider request."""
    load_dotenv()
    vector_db = _check_vector_db()
    chat_db = _check_chat_db()
    ai = "configured" if os.getenv("DEEPSEEK_API_KEY") else "not_configured"

    return {
        "status": "healthy" if vector_db == "ok" and chat_db == "ok" and ai == "configured" else "degraded",
        "api": "ok",
        "vector_db": vector_db,
        "chat_db": chat_db,
        "ai": ai,
    }
