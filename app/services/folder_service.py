from contextlib import closing
import logging
import sqlite3

from app.core.paths import CHAT_HISTORY_DB
from app.utils.datetime import normalize_aware_iso_datetime, serialize_utc_datetime, utc_now


logger = logging.getLogger(__name__)


def _serialize_folder(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "created_at": normalize_aware_iso_datetime(row["created_at"]),
    }


def _connect() -> sqlite3.Connection:
    CHAT_HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CHAT_HISTORY_DB, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_folders_db() -> None:
    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )


def list_folders() -> list[dict]:
    init_folders_db()
    with closing(_connect()) as connection:
        rows = connection.execute(
            "SELECT id, name, created_at FROM folders ORDER BY julianday(created_at) ASC, id ASC"
        ).fetchall()
    return [_serialize_folder(row) for row in rows]


def get_folder(folder_id: int) -> dict | None:
    init_folders_db()
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT id, name, created_at FROM folders WHERE id = ?",
            (folder_id,),
        ).fetchone()
    return _serialize_folder(row) if row else None


def create_folder(name: str) -> dict:
    normalized_name = name.strip()
    created_at = serialize_utc_datetime(utc_now())
    init_folders_db()
    try:
        with closing(_connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO folders(name, created_at) VALUES (?, ?)",
                    (normalized_name, created_at),
                )
                folder_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        logger.warning("Folder creation rejected duplicate_name=true")
        raise ValueError("文件夹名称已存在") from exc

    logger.info("Folder created folder_id=%s", folder_id)
    return {"id": folder_id, "name": normalized_name, "created_at": created_at}
