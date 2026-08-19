from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.user import User
from app.services.audit_service import list_audit_logs, serialize_audit_log


router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
def get_audit_logs(
    current_user: Annotated[User, Depends(require_permission("audit_view"))],
    database: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = None,
    user_id: int | None = None,
    result: str | None = Query(default=None, pattern="^(success|failed)$"),
):
    items, total = list_audit_logs(
        database,
        page=page,
        page_size=page_size,
        action=action,
        user_id=user_id,
        result=result,
    )
    return {
        "items": [serialize_audit_log(item) for item in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
