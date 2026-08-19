"""Authentication primitives for password hashing, JWT tokens and identity."""

from app.auth.dependency import get_current_user
from app.auth.permission import require_permission

__all__ = ["get_current_user", "require_permission"]
