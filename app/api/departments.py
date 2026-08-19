from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas.user_management import DepartmentCreate
from app.services.audit_service import write_audit_log
from app.utils.datetime import serialize_utc_datetime


router = APIRouter(tags=["departments"])


@router.get("/departments")
def list_departments(
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    return {"items": [
        {"id": item.id, "name": item.name, "description": item.description, "created_time": serialize_utc_datetime(item.created_time)}
        for item in database.scalars(select(Department).order_by(Department.name)).all()
    ]}


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    department = Department(name=payload.name, description=payload.description)
    database.add(department)
    try:
        database.commit()
        database.refresh(department)
    except IntegrityError as exc:
        database.rollback()
        raise HTTPException(status_code=409, detail="部门名称已存在") from exc
    write_audit_log(
        database, action="department_create", resource_type="department", result="success",
        user_id=current_user.id, resource_id=department.id, resource_name=department.name,
        detail="department_created", ip_address=request.client.host if request.client else None,
    )
    return {"id": department.id, "name": department.name, "description": department.description, "created_time": serialize_utc_datetime(department.created_time)}
