from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.chat_message import ChatMessage, ChatRole
from app.models.conversation import Conversation
from app.models.user import User
from app.utils.datetime import serialize_utc_datetime, utc_now


def _title_from_question(question: str, limit: int = 50) -> str:
    normalized = " ".join(question.split())
    if not normalized:
        return "新对话"
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}…"


def get_owned_conversation(
    database: Session,
    user: User,
    conversation_id: int,
    *,
    include_messages: bool = False,
) -> Conversation:
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    if include_messages:
        statement = statement.options(selectinload(Conversation.messages))
    conversation = database.scalar(statement)
    if conversation is None:
        # The same response is used for missing and foreign conversations so an
        # attacker cannot enumerate another user's conversation identifiers.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    return conversation


def create_conversation(database: Session, user: User, question: str) -> Conversation:
    conversation = Conversation(
        user_id=user.id,
        title=_title_from_question(question),
    )
    database.add(conversation)
    database.flush()
    return conversation


def add_message(
    database: Session,
    conversation: Conversation,
    role: ChatRole,
    content: str,
    sources: list[dict] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        sources=sources or [],
    )
    database.add(message)
    conversation.updated_time = utc_now()
    database.flush()
    return message


def list_user_conversations(database: Session, user: User) -> list[Conversation]:
    return list(database.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_time.desc(), Conversation.id.desc())
    ).all())


def serialize_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role.value,
        "content": message.content,
        "sources": message.sources or [],
        "created_time": serialize_utc_datetime(message.created_time),
    }


def serialize_conversation(conversation: Conversation, *, include_messages: bool = False) -> dict:
    result = {
        "id": conversation.id,
        "conversation_id": conversation.id,
        "title": conversation.title,
        "created_time": serialize_utc_datetime(conversation.created_time),
        "updated_time": serialize_utc_datetime(conversation.updated_time),
    }
    if include_messages:
        result["messages"] = [serialize_message(message) for message in conversation.messages]
    return result
