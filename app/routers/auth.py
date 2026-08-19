from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt import (
    JWTConfigurationError,
    access_token_expire_minutes,
    create_access_token,
)
from app.auth.password import hash_password, verify_password
from app.auth.dependency import get_current_user
from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserLogin, UserRegister, UserResponse
from app.services.user_management_service import create_managed_user
from app.services.audit_service import write_audit_log


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "role": (
            {"id": current_user.role.id, "name": current_user.role.name}
            if current_user.role else None
        ),
        "department": (
            {"id": current_user.department.id, "name": current_user.department.name}
            if current_user.department else None
        ),
        "team": (
            {"id": current_user.team.id, "name": current_user.team.name}
            if current_user.team else None
        ),
        "status": current_user.status,
        "permissions": sorted(
            permission.code
            for permission in (current_user.role.permissions if current_user.role else [])
        ),
    }


@router.get("/test-permission")
def test_file_delete_permission(
    current_user: User = Depends(require_permission("file_delete")),
) -> dict[str, str | int]:
    return {
        "message": "file_delete权限验证通过",
        "user_id": current_user.id,
        "username": current_user.username,
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserRegister,
    current_user: User = Depends(require_permission("user_manage")),
    database: Session = Depends(get_db),
) -> User:
    if payload.role_id is None:
        raise HTTPException(status_code=400, detail="管理员创建用户时必须指定角色")
    return create_managed_user(
        database,
        username=payload.username,
        password=payload.password,
        real_name=payload.real_name,
        role_id=payload.role_id,
        department_id=payload.department_id,
    )


@router.post("/login", response_model=Token)
def login_user(payload: UserLogin, request: Request, database: Session = Depends(get_db)) -> Token:
    ip_address = request.client.host if request.client else None
    user = database.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        write_audit_log(
            database,
            action="auth_login_failed",
            resource_type="auth",
            resource_name=payload.username,
            result="failed",
            detail="invalid_credentials",
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != "active":
        write_audit_log(
            database,
            action="auth_login_failed",
            resource_type="auth",
            user_id=user.id,
            resource_id=user.id,
            resource_name=user.username,
            result="failed",
            detail="inactive_user",
            ip_address=ip_address,
        )
        # Keep the public failure response indistinguishable from bad credentials.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token = create_access_token(
            user.id,
            user.token_version,
            {"username": user.username},
        )
        expires_in = access_token_expire_minutes() * 60
    except JWTConfigurationError as exc:
        raise HTTPException(status_code=500, detail="JWT服务未正确配置") from exc

    write_audit_log(
        database,
        action="auth_login_success",
        resource_type="auth",
        user_id=user.id,
        resource_id=user.id,
        resource_name=user.username,
        result="success",
        detail="authenticated",
        ip_address=ip_address,
    )

    return Token(access_token=token, expires_in=expires_in)
