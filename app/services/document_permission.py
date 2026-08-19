from app.models.document import Document, DocumentVisibility
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload


def _role_name(user: User) -> str | None:
    role = user.role
    if role is None:
        return None
    return role.name.strip().lower()


def _same_user(user: User, document: Document) -> bool:
    if document.uploader is user:
        return True
    return user.id is not None and document.uploader_id == user.id


def _same_department(user: User, document: Document) -> bool:
    return (
        user.department_id is not None
        and document.department_id is not None
        and user.department_id == document.department_id
    )


def _same_team(user: User, document: Document) -> bool:
    return (
        user.team_id is not None
        and document.team_id is not None
        and user.team_id == document.team_id
    )


def _uploader_role_name(document: Document) -> str | None:
    uploader = document.uploader
    return _role_name(uploader) if uploader is not None else None


def _visibility(document: Document) -> DocumentVisibility:
    visibility = document.visibility
    if isinstance(visibility, DocumentVisibility):
        return visibility
    try:
        return DocumentVisibility(visibility)
    except (TypeError, ValueError):
        return DocumentVisibility.PRIVATE


def can_view_document(user: User, document: Document) -> bool:
    """Return whether role, ownership and visibility allow reading a document."""
    role_name = _role_name(user)
    if role_name == "admin" or _same_user(user, document):
        return True

    visibility = _visibility(document)
    if visibility is DocumentVisibility.COMPANY:
        return True

    if role_name == "manager" and _same_department(user, document):
        return True
    if role_name == "leader" and _same_team(user, document) and _uploader_role_name(document) == "employee":
        return True

    if visibility is DocumentVisibility.TEAM:
        return _same_team(user, document)
    if visibility is DocumentVisibility.DEPARTMENT:
        return _same_department(user, document)
    return False


def can_edit_document(user: User, document: Document) -> bool:
    """Return whether a user can edit document metadata/content ownership scope."""
    role_name = _role_name(user)
    if role_name == "admin":
        return True
    if role_name == "manager":
        return _same_department(user, document)
    if role_name == "leader":
        return _same_user(user, document) or (
            _same_team(user, document)
            and _uploader_role_name(document) == "employee"
        )
    return False


def can_delete_document(user: User, document: Document) -> bool:
    """Return whether a user can delete a document within organizational scope."""
    return can_edit_document(user, document)


VISIBILITY_PERMISSION = {
    DocumentVisibility.TEAM: "file_publish_team",
    DocumentVisibility.DEPARTMENT: "file_publish_department",
    DocumentVisibility.COMPANY: "file_publish_company",
}


def can_publish_visibility(user: User, visibility: DocumentVisibility) -> bool:
    if visibility is DocumentVisibility.PRIVATE:
        return True
    required_code = VISIBILITY_PERMISSION[visibility]
    return bool(user.role) and any(permission.code == required_code for permission in user.role.permissions)


def require_publish_visibility(user: User, visibility: DocumentVisibility) -> None:
    if not can_publish_visibility(user, visibility):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权将文件发布到该可见范围")


def accessible_document_ids(database: Session, user: User) -> set[int]:
    """Return an explicit SQL-backed document allow-list for every role."""
    documents = database.scalars(
        select(Document).options(
            joinedload(Document.uploader).joinedload(User.role),
            joinedload(Document.department),
        )
    ).unique().all()
    return {
        document.id
        for document in documents
        if can_view_document(user, document)
    }
