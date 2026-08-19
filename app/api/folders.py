from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.folder_service import create_folder, list_folders


router = APIRouter()


class FolderCreate(BaseModel):
    name: str


@router.get("/folders")
def get_folders():
    return list_folders()


@router.post("/folders", status_code=201)
def post_folder(payload: FolderCreate):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="文件夹名称不能超过100个字符")
    try:
        return create_folder(name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
