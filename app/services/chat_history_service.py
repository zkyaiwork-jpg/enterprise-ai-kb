from contextlib import closing
from functools import wraps
import json
import logging
import sqlite3

from app.core.paths import CHAT_HISTORY_DB
from app.utils.datetime import normalize_aware_iso_datetime, serialize_utc_datetime, utc_now

logger = logging.getLogger(__name__)


def _log_database_errors(operation):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except sqlite3.Error as exc:
                logger.error(
                    "Chat database operation failed operation=%s error_type=%s",
                    operation, type(exc).__name__,
                )
                raise
        return wrapper
    return decorator


def _connect() -> sqlite3.Connection:
    CHAT_HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CHAT_HISTORY_DB, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


@_log_database_errors("initialize")
def init_chat_history_db() -> None:
    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sources TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_session_created
                ON chat_history(session_id, created_at)
                """
            )
            connection.execute("PRAGMA optimize")


@_log_database_errors("save")
def save_chat_history(
    session_id: str,
    question: str,
    answer: str,
    sources: list,
) -> dict:
    init_chat_history_db()
    created_at = serialize_utc_datetime(utc_now())
    sources_json = json.dumps(sources, ensure_ascii=False)

    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO chat_history(session_id, question, answer, sources, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, question, answer, sources_json, created_at),
            )
            record_id = cursor.lastrowid

    logger.info("Chat history saved session_id=%s record_id=%s source_count=%s", session_id, record_id, len(sources))
    return {
        "id": record_id,
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "sources": sources,
        "created_at": created_at,
    }


@_log_database_errors("list")
def list_chat_sessions() -> list[dict]:
    init_chat_history_db()
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, question, answer, sources, created_at
            FROM chat_history
            ORDER BY julianday(created_at) ASC, id ASC
            """
        ).fetchall()

    sessions_by_id: dict[str, dict] = {}
    for row in rows:
        created_at = normalize_aware_iso_datetime(row["created_at"])
        try:
            sources = json.loads(row["sources"])
        except (TypeError, json.JSONDecodeError):
            sources = []

        session = sessions_by_id.setdefault(
            row["session_id"],
            {
                "session_id": row["session_id"],
                "title": row["question"],
                "created_at": created_at,
                "updated_at": created_at,
                "messages": [],
            },
        )
        session["updated_at"] = created_at
        session["messages"].append(
            {
                "id": row["id"],
                "question": row["question"],
                "answer": row["answer"],
                "sources": sources,
                "created_at": created_at,
            }
        )

    sessions = sorted(
        sessions_by_id.values(),
        key=lambda session: session["updated_at"],
        reverse=True,
    )
    logger.info("Chat history listed session_count=%s record_count=%s", len(sessions), len(rows))
    return sessions


@_log_database_errors("count")
def count_chat_questions() -> int:
    init_chat_history_db()
    with closing(_connect()) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM chat_history").fetchone()
    return int(row["count"] if row else 0)
