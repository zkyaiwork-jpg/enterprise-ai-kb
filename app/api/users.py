from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.user import User
from app.models.role import Role
from sqlalchemy import select
from app.schemas.user_management import ManagedUserCreate, ManagedUserUpdate, PasswordResetRequest
from app.services.audit_service import write_audit_log
from app.services.user_management_service import (
    create_managed_user,
    delete_managed_user,
    get_managed_user,
    list_managed_users,
    reset_managed_user_password,
    serialize_managed_user,
    update_managed_user,
)


router = APIRouter(tags=["users"])


@router.get("/roles")
def get_roles(
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    roles = database.scalars(select(Role).order_by(Role.name)).all()
    return {"items": [
        {"id": role.id, "name": role.name, "description": role.description}
        for role in roles
    ]}


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: ManagedUserCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    user = create_managed_user(database, **payload.model_dump())
    write_audit_log(
        database, action="user_create", resource_type="user", result="success",
        user_id=current_user.id, resource_id=user.id, resource_name=user.username,
        detail=f"role_id={user.role_id};department_id={user.department_id};status=active", ip_address=_ip(request),
    )
    return serialize_managed_user(user)


@router.get("/users")
def get_users(
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|inactive)$"),
    department_id: int | None = None,
    role_id: int | None = None,
):
    users, total = list_managed_users(
        database, page=page, page_size=page_size, status_filter=status_filter,
        department_id=department_id, role_id=role_id,
    )
    return {"items": [serialize_managed_user(user) for user in users], "page": page, "page_size": page_size, "total": total}


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    return serialize_managed_user(get_managed_user(database, user_id))


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: ManagedUserUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    target = get_managed_user(database, user_id)
    old_status = target.status
    changes = payload.model_dump(exclude_unset=True)
    target, changed_fields = update_managed_user(database, current_user, target, changes=changes)
    write_audit_log(
        database,
        action="user_status_change" if "status" in changed_fields else "user_update",
        resource_type="user", result="success", user_id=current_user.id,
        resource_id=target.id, resource_name=target.username,
        detail=(f"status:{old_status}->{target.status};" if "status" in changed_fields else "") + f"fields={','.join(changed_fields)}",
        ip_address=_ip(request),
    )
    return serialize_managed_user(target)


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: PasswordResetRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    target = get_managed_user(database, user_id)
    reset_managed_user_password(database, target, payload.new_password)
    write_audit_log(
        database, action="user_password_reset", resource_type="user", result="success",
        user_id=current_user.id, resource_id=target.id, resource_name=target.username,
        detail="password_reset;tokens_invalidated=true", ip_address=_ip(request),
    )
    return {"user_id": target.id, "message": "密码已重置"}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
) -> Response:
    target = get_managed_user(database, user_id)
    delete_managed_user(
        database,
        current_user,
        target,
        ip_address=_ip(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
