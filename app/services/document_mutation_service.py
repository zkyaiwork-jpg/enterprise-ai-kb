import logging
from pathlib import Path
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentVisibility
from app.models.user import User
from app.models.team import Team
from app.services.document_permission import can_delete_document, can_edit_document
from app.services.document_service import UPLOAD_DIR
from app.services.vector_store import collection


logger = logging.getLogger(__name__)


def _get_sql_document(database: Session, *, document_id: int | None = None, filename: str | None = None) -> Document:
    statement = select(Document).options(
        joinedload(Document.uploader).joinedload(User.role),
        joinedload(Document.department),
        joinedload(Document.team),
    )
    if document_id is not None:
        statement = statement.where(Document.id == document_id)
    elif filename is not None:
        statement = statement.where(Document.filename == Path(filename).name)
    else:
        raise ValueError("document_id或filename必须提供")
    document = database.scalar(statement)
    if document is None:
        # Chroma-only legacy records deliberately cannot be mutated here.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在或需要先迁移")
    return document


def _snapshot_vectors(document_id: int) -> dict:
    return collection.get(
        where={"document_id": document_id},
        include=["documents", "embeddings", "metadatas"],
    )


def _restore_vectors(snapshot: dict) -> None:
    ids = snapshot.get("ids") or []
    if not ids:
        return
    existing = set(collection.get(ids=ids).get("ids") or [])
    indexes = [index for index, item_id in enumerate(ids) if item_id not in existing]
    if not indexes:
        return
    kwargs = {
        "ids": [ids[index] for index in indexes],
        "documents": [snapshot["documents"][index] for index in indexes],
        "metadatas": [snapshot["metadatas"][index] for index in indexes],
    }
    embeddings = snapshot.get("embeddings")
    if embeddings is not None:
        kwargs["embeddings"] = [embeddings[index] for index in indexes]
    collection.add(**kwargs)


def delete_owned_document(database: Session, current_user: User, filename: str) -> dict:
    document = _get_sql_document(database, filename=filename)
    if not can_delete_document(current_user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除该文档")

    snapshot = _snapshot_vectors(document.id)
    vector_ids = snapshot.get("ids") or []
    file_path = UPLOAD_DIR / document.filename
    quarantined_path = file_path.with_name(f".{file_path.name}.deleting-{uuid.uuid4().hex}")
    file_was_moved = False

    logger.info(
        "Document deletion started user_id=%s document_id=%s filename=%s vector_count=%s",
        current_user.id, document.id, document.filename, len(vector_ids),
    )
    try:
        if file_path.exists():
            file_path.replace(quarantined_path)
            file_was_moved = True
        if vector_ids:
            collection.delete(ids=vector_ids)
        database.delete(document)
        database.commit()
    except Exception as exc:
        database.rollback()
        recovery_errors = []
        try:
            _restore_vectors(snapshot)
        except Exception as recovery_exc:
            recovery_errors.append(type(recovery_exc).__name__)
        try:
            if file_was_moved and quarantined_path.exists():
                quarantined_path.replace(file_path)
        except Exception as recovery_exc:
            recovery_errors.append(type(recovery_exc).__name__)
        logger.error(
            "Document deletion failed user_id=%s document_id=%s error_type=%s recovery_errors=%s",
            current_user.id, document.id, type(exc).__name__, recovery_errors,
        )
        raise HTTPException(status_code=500, detail="文档删除失败，已尝试恢复原数据") from exc

    # At this point SQL and vectors are committed absent. Failure to remove the
    # quarantined file is reported rather than silently swallowed; it contains
    # no active filename and can be cleaned by a later maintenance task.
    if file_was_moved:
        try:
            quarantined_path.unlink()
        except OSError as exc:
            logger.error(
                "Deleted document quarantine cleanup failed document_id=%s error_type=%s",
                document.id, type(exc).__name__,
            )
            raise HTTPException(status_code=500, detail="文档已删除，但隔离文件清理失败") from exc

    logger.info(
        "Document deletion completed user_id=%s document_id=%s filename=%s vector_count=%s",
        current_user.id, document.id, document.filename, len(vector_ids),
    )
    return {
        "document_id": document.id,
        "filename": document.filename,
        "file_deleted": file_was_moved,
        "delete_vector": len(vector_ids),
    }


def update_owned_document_metadata(
    database: Session,
    current_user: User,
    document_id: int,
    *,
    original_name: str | None = None,
    visibility: DocumentVisibility | None = None,
    team_id: int | None = None,
    team_id_supplied: bool = False,
) -> Document:
    document = _get_sql_document(database, document_id=document_id)
    if not can_edit_document(current_user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该文档")
    target_visibility = visibility or document.visibility
    if team_id_supplied and target_visibility is not DocumentVisibility.TEAM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非team文档不能通过该接口修改所属小组",
        )
    if visibility is not None or team_id_supplied:
        from app.services.document_permission import require_publish_visibility
        require_publish_visibility(current_user, target_visibility)

    target_team_id = team_id if team_id_supplied else document.team_id
    if target_visibility is DocumentVisibility.TEAM:
        role_name = current_user.role.name.strip().lower() if current_user.role else ""
        if target_team_id is None:
            raise HTTPException(status_code=400, detail="小组可见文件必须指定目标小组")
        target_team = database.get(Team, target_team_id)
        if target_team is None:
            raise HTTPException(status_code=400, detail="目标小组不存在")
        if role_name == "leader" and target_team.id != current_user.team_id:
            raise HTTPException(status_code=403, detail="组长只能选择自己的小组")
        if role_name == "manager" and target_team.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="主管只能选择本部门小组")
        if role_name not in {"leader", "manager", "admin"}:
            raise HTTPException(status_code=403, detail="无权设置目标小组")
        target_department_id = target_team.department_id
    else:
        target_department_id = document.department_id

    snapshot = _snapshot_vectors(document.id)
    vector_ids = snapshot.get("ids") or []
    original_metadatas = snapshot.get("metadatas") or []
    updated_metadatas = [dict(metadata) for metadata in original_metadatas]
    if target_visibility is DocumentVisibility.TEAM:
        for metadata in updated_metadatas:
            metadata["visibility"] = target_visibility.value
            metadata["team_id"] = target_team_id
            metadata["department_id"] = target_department_id
    else:
        for metadata in updated_metadatas:
            if visibility is not None:
                metadata["visibility"] = visibility.value

    try:
        metadata_changed = visibility is not None or team_id_supplied or (
            target_visibility is DocumentVisibility.TEAM
            and document.department_id != target_department_id
        )
        if metadata_changed and vector_ids:
            collection.update(ids=vector_ids, metadatas=updated_metadatas)
        if original_name is not None:
            normalized_name = original_name.strip()
            if not normalized_name:
                raise HTTPException(status_code=400, detail="original_name不能为空")
            document.original_name = normalized_name
        if visibility is not None:
            document.visibility = visibility
        if target_visibility is DocumentVisibility.TEAM:
            document.team_id = target_team_id
            document.department_id = target_department_id
        database.commit()
        database.refresh(document)
    except Exception as exc:
        database.rollback()
        try:
            if vector_ids and original_metadatas:
                collection.update(ids=vector_ids, metadatas=original_metadatas)
        except Exception as recovery_exc:
            logger.error(
                "Document metadata rollback failed document_id=%s error_type=%s",
                document_id, type(recovery_exc).__name__,
            )
        if isinstance(exc, HTTPException):
            raise
        logger.error(
            "Document metadata update failed user_id=%s document_id=%s error_type=%s",
            current_user.id, document_id, type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="文档修改失败，已尝试恢复原数据") from exc

    logger.info(
        "Document metadata updated user_id=%s document_id=%s visibility_changed=%s name_changed=%s",
        current_user.id, document_id, visibility is not None, original_name is not None,
    )
    return document
