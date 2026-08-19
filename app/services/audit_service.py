import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.datetime import serialize_utc_datetime


logger = logging.getLogger(__name__)
AuditResult = Literal["success", "failed"]


def write_audit_log(
    database: Session,
    *,
    action: str,
    resource_type: str,
    result: AuditResult,
    user_id: int | None = None,
    resource_id: int | str | None = None,
    resource_name: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> AuditLog | None:
    """Persist a security audit event without breaking the completed operation."""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            actor_name=(
                database.scalar(select(User.username).where(User.id == user_id))
                if user_id is not None else None
            ),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            resource_name=resource_name,
            result=result,
            detail=detail,
            ip_address=ip_address,
        )
        database.add(audit_log)
        database.commit()
        database.refresh(audit_log)
        return audit_log
    except Exception as exc:
        database.rollback()
        logger.error(
            "Audit write failed action=%s resource_type=%s result=%s error_type=%s",
            action, resource_type, result, type(exc).__name__,
        )
        return None


def list_audit_logs(
    database: Session,
    *,
    page: int,
    page_size: int,
    action: str | None = None,
    user_id: int | None = None,
    result: str | None = None,
) -> tuple[list[AuditLog], int]:
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)
    if result:
        filters.append(AuditLog.result == result)
    statement = select(AuditLog).where(*filters)
    total = len(database.scalars(statement).all())
    items = list(database.scalars(
        statement.order_by(AuditLog.created_time.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    return items, total


def serialize_audit_log(item: AuditLog) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "actor_name": item.actor_name,
        "action": item.action,
        "resource_type": item.resource_type,
        "resource_id": item.resource_id,
        "resource_name": item.resource_name,
        "result": item.result,
        "detail": item.detail,
        "ip_address": item.ip_address,
        "created_time": serialize_utc_datetime(item.created_time),
    }
