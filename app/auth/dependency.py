from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from app.auth.jwt import JWTConfigurationError, verify_access_token
from app.database.database import get_db
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def _authentication_error(detail: str = "身份认证失败") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    database: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the authenticated User from a valid Authorization Bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error("未提供有效的Bearer Token")

    try:
        payload = verify_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        token_version = int(payload["token_version"])
        if user_id <= 0:
            raise ValueError
    except ExpiredSignatureError as exc:
        raise _authentication_error("Token已过期") from exc
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise _authentication_error("Token无效") from exc
    except JWTConfigurationError as exc:
        raise _authentication_error("身份认证服务未正确配置") from exc

    user = database.get(User, user_id)
    if user is None:
        raise _authentication_error("Token对应的用户不存在")
    if user.status != "active":
        # JWT identifies the account, but current database state remains the
        # authority. This immediately revokes previously issued access tokens.
        raise _authentication_error("用户账号已停用")
    if token_version != user.token_version:
        raise _authentication_error("Token已失效，请重新登录")
    return user
