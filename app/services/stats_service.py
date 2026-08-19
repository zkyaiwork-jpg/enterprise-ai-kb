import os

from sqlalchemy import func, select

from app.database.database import SessionLocal
from app.models.chat_message import ChatMessage, ChatRole
from app.services.vector_store import collection


def count_chat_questions() -> int:
    """Count user-authored messages from the ownership-aware chat store."""
    with SessionLocal() as database:
        return int(database.scalar(
            select(func.count(ChatMessage.id)).where(ChatMessage.role == ChatRole.USER)
        ) or 0)


def get_system_stats():
    """Return dashboard statistics from the current persistent data sources."""
    result = collection.get(include=["metadatas"])
    metadatas = result.get("metadatas") or []

    document_keys = set()
    for metadata in metadatas:
        if not isinstance(metadata, dict):
            continue
        document_key = metadata.get("document_id") or metadata.get("filename")
        if document_key:
            document_keys.add(str(document_key))

    return {
        "document_count": len(document_keys),
        "chunk_count": collection.count(),
        "question_count": count_chat_questions(),
        # 这里只检查 DeepSeek 配置是否存在，不执行外部网络探活。
        "ai_status": "online" if os.getenv("DEEPSEEK_API_KEY") else "offline",
    }
