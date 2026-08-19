from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.document import DocumentVisibility
from app.models.user import User
from app.services.document_mutation_service import (
    delete_owned_document,
    update_owned_document_metadata,
)
from app.services.audit_service import write_audit_log
from app.utils.datetime import serialize_utc_datetime


router = APIRouter()


class DocumentUpdateRequest(BaseModel):
    original_name: str | None = None
    visibility: DocumentVisibility | None = None
    team_id: int | None = None


@router.delete("/documents/{filename}")
def remove_document(
    filename: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("file_delete"))],
    database: Annotated[Session, Depends(get_db)],
):
    try:
        result = delete_owned_document(database, current_user, filename)
    except Exception as exc:
        write_audit_log(
            database,
            action="document_delete",
            resource_type="document",
            user_id=current_user.id,
            resource_name=filename,
            result="failed",
            detail=f"operation_failed:{type(exc).__name__}",
            ip_address=request.client.host if request.client else None,
        )
        raise
    write_audit_log(
        database,
        action="document_delete",
        resource_type="document",
        user_id=current_user.id,
        resource_id=result["document_id"],
        resource_name=result["filename"],
        result="success",
        detail=f"vectors_deleted={result['delete_vector']}",
        ip_address=request.client.host if request.client else None,
    )
    return {**result, "message": "删除成功"}


@router.patch("/documents/{document_id}")
def update_document(
    document_id: int,
    request: DocumentUpdateRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_permission("file_edit"))],
    database: Annotated[Session, Depends(get_db)],
):
    old_visibility = None
    old_original_name = None
    try:
        from app.models.document import Document
        existing = database.get(Document, document_id)
        if existing is not None:
            old_visibility = existing.visibility.value
            old_original_name = existing.original_name
        document = update_owned_document_metadata(
            database,
            current_user,
            document_id,
            original_name=request.original_name,
            visibility=request.visibility,
            team_id=request.team_id,
            team_id_supplied="team_id" in request.model_fields_set,
        )
    except Exception as exc:
        write_audit_log(
            database,
            action="document_update",
            resource_type="document",
            user_id=current_user.id,
            resource_id=document_id,
            result="failed",
            detail=f"operation_failed:{type(exc).__name__}",
            ip_address=http_request.client.host if http_request.client else None,
        )
        raise
    changes = []
    if request.visibility is not None:
        changes.append(f"visibility:{old_visibility}->{request.visibility.value}")
    if request.original_name is not None:
        changes.append(f"original_name_changed={old_original_name != request.original_name.strip()}")
    write_audit_log(
        database,
        action="document_update",
        resource_type="document",
        user_id=current_user.id,
        resource_id=document.id,
        resource_name=document.filename,
        result="success",
        detail=";".join(changes) or "no_fields_changed",
        ip_address=http_request.client.host if http_request.client else None,
    )
    return {
        "document_id": document.id,
        "filename": document.filename,
        "original_name": document.original_name,
        "visibility": document.visibility.value,
        "team_id": document.team_id,
        "updated_time": serialize_utc_datetime(document.updated_time),
    }
