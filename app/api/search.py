from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.user import User
from app.services.document_permission import accessible_document_ids
from app.services.search_service import search_documents


router = APIRouter()


@router.get("/search")
def search(
    current_user: Annotated[User, Depends(require_permission("file_view"))],
    database: Annotated[Session, Depends(get_db)],
    query: str,
    limit: int = 3,
    folder_id: int | None = None,
    file_type: str | None = None,
):
    if not query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    normalized_limit = min(max(limit, 1), 20)
    allowed_ids = accessible_document_ids(database, current_user)

    return search_documents(
        query,
        top_k=normalized_limit,
        folder_id=folder_id,
        file_type=file_type,
        allowed_document_ids=allowed_ids,
    )
