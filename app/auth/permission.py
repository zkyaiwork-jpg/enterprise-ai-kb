from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependency import get_current_user
from app.database.database import get_db
from app.models.permission import Permission
from app.models.role import role_permissions
from app.models.user import User


def require_permission(permission_code: str) -> Callable[..., User]:
    """Build a FastAPI dependency that requires one permission code."""
    normalized_code = permission_code.strip()
    if not normalized_code:
        raise ValueError("permission_code不能为空")

    def permission_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        database: Annotated[Session, Depends(get_db)],
    ) -> User:
        if current_user.role_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前用户没有所需权限",
            )

        permission_id = database.scalar(
            select(Permission.id)
            .join(
                role_permissions,
                Permission.id == role_permissions.c.permission_id,
            )
            .where(
                role_permissions.c.role_id == current_user.role_id,
                Permission.code == normalized_code,
            )
            .limit(1)
        )
        if permission_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前用户没有所需权限",
            )
        return current_user

    return permission_dependency
