from datetime import datetime, timedelta, timezone
import os
from typing import Any

import jwt
from jwt import InvalidTokenError


JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60


class JWTConfigurationError(RuntimeError):
    """Raised when required JWT configuration is missing or invalid."""


def _secret_key() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if not secret:
        raise JWTConfigurationError("JWT_SECRET_KEY未配置")
    return secret


def access_token_expire_minutes() -> int:
    configured = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "").strip()
    if not configured:
        return DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
    try:
        minutes = int(configured)
    except ValueError as exc:
        raise JWTConfigurationError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES必须为整数") from exc
    if minutes <= 0:
        raise JWTConfigurationError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES必须大于0")
    return minutes


def create_access_token(
    subject: str | int,
    token_version: int,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed access token using environment-based configuration."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=access_token_expire_minutes())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "token_version": token_version,
        "iat": now,
        "exp": expires_at,
    }
    if additional_claims:
        if "token_version" in additional_claims:
            raise ValueError("token_version must come from the server-side User record")
        payload.update(additional_claims)
    return jwt.encode(payload, _secret_key(), algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict[str, Any]:
    """Validate a JWT access token and return its claims."""
    payload = jwt.decode(token, _secret_key(), algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "access" or not payload.get("sub"):
        raise InvalidTokenError("无效的访问令牌")
    return payload
