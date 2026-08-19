from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.chat_message import ChatRole
from app.models.user import User
from app.services.conversation_service import (
    add_message,
    create_conversation,
    get_owned_conversation,
    list_user_conversations,
    serialize_conversation,
)
from app.services.document_permission import accessible_document_ids
from app.services.rag_service import ask_ai
from app.utils.datetime import serialize_utc_datetime


router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    # Temporary request compatibility for clients that still send session_id.
    # Only numeric IDs issued by this API are accepted as conversation IDs.
    session_id: str | None = None


def _requested_conversation_id(request: ChatRequest) -> int | None:
    if request.conversation_id is not None:
        return request.conversation_id
    if request.session_id and request.session_id.isdigit():
        return int(request.session_id)
    return None


@router.post("/chat")
def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(require_permission("file_view"))],
    database: Annotated[Session, Depends(get_db)],
):
    conversation_id = _requested_conversation_id(request)
    conversation = (
        get_owned_conversation(database, current_user, conversation_id)
        if conversation_id is not None
        else create_conversation(database, current_user, request.question)
    )
    add_message(database, conversation, ChatRole.USER, request.question)

    allowed_ids = accessible_document_ids(database, current_user)
    result = ask_ai(request.question, allowed_document_ids=allowed_ids, database=database)
    assistant_message = add_message(
        database,
        conversation,
        ChatRole.ASSISTANT,
        result["answer"],
        result["sources"],
    )
    database.commit()

    return {
        "id": assistant_message.id,
        "conversation_id": conversation.id,
        # Response compatibility while desktop/web clients migrate terminology.
        "session_id": str(conversation.id),
        "answer": result["answer"],
        "question": request.question,
        "sources": result["sources"],
        "created_at": serialize_utc_datetime(assistant_message.created_time),
    }


@router.get("/chat/conversations")
def get_conversations(
    current_user: Annotated[User, Depends(require_permission("file_view"))],
    database: Annotated[Session, Depends(get_db)],
):
    return {
        "conversations": [
            serialize_conversation(conversation)
            for conversation in list_user_conversations(database, current_user)
        ]
    }


@router.get("/chat/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: Annotated[User, Depends(require_permission("file_view"))],
    database: Annotated[Session, Depends(get_db)],
):
    conversation = get_owned_conversation(
        database,
        current_user,
        conversation_id,
        include_messages=True,
    )
    return serialize_conversation(conversation, include_messages=True)


@router.get("/chat/history")
def get_chat_history_compatibility(
    current_user: Annotated[User, Depends(require_permission("file_view"))],
    database: Annotated[Session, Depends(get_db)],
):
    """Authenticated compatibility view; legacy global SQLite rows stay hidden."""
    sessions = []
    for conversation in list_user_conversations(database, current_user):
        owned = get_owned_conversation(
            database,
            current_user,
            conversation.id,
            include_messages=True,
        )
        paired_messages = []
        pending_user = None
        for message in owned.messages:
            if message.role is ChatRole.USER:
                pending_user = message
            elif message.role is ChatRole.ASSISTANT and pending_user is not None:
                paired_messages.append({
                    "id": message.id,
                    "question": pending_user.content,
                    "answer": message.content,
                    "sources": message.sources or [],
                    "created_at": serialize_utc_datetime(message.created_time),
                })
                pending_user = None
        serialized = serialize_conversation(owned)
        sessions.append({
            "session_id": str(owned.id),
            "title": owned.title,
            "created_at": serialized["created_time"],
            "updated_at": serialized["updated_time"],
            "messages": paired_messages,
        })
    return {"sessions": sessions}
