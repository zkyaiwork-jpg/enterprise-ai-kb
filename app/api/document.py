from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.document import Document, DocumentVisibility
from app.models.user import User
from app.models.team import Team
from app.services.document_permission import can_view_document, require_publish_visibility
from app.services.document_service import save_document, list_documents
from app.services.audit_service import write_audit_log


router = APIRouter()

@router.post("/upload")
async def upload_document(
        request: Request,
        current_user: Annotated[User, Depends(require_permission("file_upload"))],
        database: Annotated[Session, Depends(get_db)],
        file: UploadFile = File(...),
        folder_id: int | None = Form(default=None),
        visibility: DocumentVisibility = Form(default=DocumentVisibility.PRIVATE),
        team_id: int | None = Form(default=None),
):
    original_name = file.filename or ""
    filename = Path(original_name).name
    require_publish_visibility(current_user, visibility)
    role_name = current_user.role.name.strip().lower() if current_user.role else ""
    document_team_id = current_user.team_id
    document_department_id = current_user.department_id
    if role_name in {"employee", "leader"} and current_user.team_id is not None:
        own_team = database.get(Team, current_user.team_id)
        if own_team is None or own_team.department_id != current_user.department_id:
            raise HTTPException(status_code=400, detail="当前用户的小组与部门归属不一致，请联系管理员处理")
    if visibility is DocumentVisibility.TEAM:
        if role_name in {"employee", "leader"}:
            if current_user.team_id is None:
                raise HTTPException(status_code=400, detail="当前用户尚未分配小组")
            if team_id is not None and team_id != current_user.team_id:
                raise HTTPException(status_code=403, detail="无权向其他小组发布文件")
            document_team_id = current_user.team_id
        elif role_name in {"manager", "admin"}:
            if team_id is None:
                raise HTTPException(status_code=400, detail="发布小组文件必须选择目标小组")
            target_team = database.get(Team, team_id)
            if target_team is None:
                raise HTTPException(status_code=400, detail="目标小组不存在")
            if role_name == "manager" and target_team.department_id != current_user.department_id:
                raise HTTPException(status_code=403, detail="无权向其他部门的小组发布文件")
            document_team_id = target_team.id
            if role_name == "admin":
                document_department_id = target_team.department_id
        else:
            raise HTTPException(status_code=403, detail="无权发布小组文件")
    document = database.scalar(select(Document).where(Document.filename == filename))
    if document is not None:
        raise HTTPException(status_code=409, detail="文件已存在，请使用文档编辑/更新流程")
    document = Document(
        filename=filename,
        original_name=original_name,
        uploader_id=current_user.id,
        department_id=document_department_id,
        team_id=document_team_id,
        visibility=visibility,
    )
    database.add(document)

    try:
        database.flush()
        result = save_document(
            file,
            folder_id=folder_id,
            access_metadata={
                "document_id": document.id,
                "uploader_id": current_user.id,
                "department_id": document_department_id or 0,
                "team_id": document_team_id or 0,
                "visibility": visibility.value,
            },
        )
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        write_audit_log(
            database, action="document_upload", resource_type="document",
            user_id=current_user.id, resource_name=filename, result="failed",
            detail="filename_conflict", ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=409, detail="文件已存在，请使用文档编辑/更新流程") from exc
    except Exception as exc:
        database.rollback()
        write_audit_log(
            database,
            action="document_upload",
            resource_type="document",
            user_id=current_user.id,
            resource_id=document.id,
            resource_name=filename,
            result="failed",
            detail=f"processing_failed:{type(exc).__name__}",
            ip_address=request.client.host if request.client else None,
        )
        raise

    write_audit_log(
        database,
        action="document_upload",
        resource_type="document",
        user_id=current_user.id,
        resource_id=document.id,
        resource_name=filename,
        result="success",
        detail=f"visibility={visibility.value}",
        ip_address=request.client.host if request.client else None,
    )

    return {
        "filename": result["filename"],
        "path":str(result["file_path"]),
        "content":result["content"],
        "chunks":result["chunks"],
        "vector_count": result["vector_count"],
        "document_id": result["document_id"],
        "category": result["category"],
        "folder_id": result["folder_id"],
        "folder_name": result["folder_name"],
        "status": result["status"],
        "file_type": result["file_type"],
        "file_size": result["file_size"],
        "uploaded_at": result["uploaded_at"],
        "uploader_id": result["uploader_id"],
        "department_id": result["department_id"],
        "team_id": result["team_id"],
        "visibility": result["visibility"],
        "message": "文件上传成功"
    }


@router.get("/documents")
def get_documents(
    current_user: Annotated[User, Depends(require_permission("file_view"))],
    database: Annotated[Session, Depends(get_db)],
):
    chroma_documents = list_documents()

    permission_documents = database.scalars(
        select(Document).options(
            joinedload(Document.uploader).joinedload(User.role),
            joinedload(Document.department),
            joinedload(Document.team),
        )
    ).unique().all()
    permitted_ids = {
        str(document.id)
        for document in permission_documents
        if can_view_document(current_user, document)
    }

    visible_documents = [
        document
        for document in chroma_documents
        if str(document.get("document_id")) in permitted_ids
    ]

    return {
        "documents": visible_documents
    }
