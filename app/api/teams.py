from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.department import Department
from app.models.team import Team
from app.models.user import User
from app.schemas.user_management import TeamCreate
from app.services.audit_service import write_audit_log
from app.utils.datetime import serialize_utc_datetime


router = APIRouter(tags=["teams"])


def _serialize(team: Team) -> dict:
    return {
        "id": team.id,
        "name": team.name,
        "department_id": team.department_id,
        "department": {"id": team.department.id, "name": team.department.name},
        "description": team.description,
        "created_time": serialize_utc_datetime(team.created_time),
    }


@router.get("/teams")
def list_teams(
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
    department_id: int | None = Query(default=None),
):
    statement = select(Team).options(joinedload(Team.department)).order_by(Team.department_id, Team.name)
    if department_id is not None:
        statement = statement.where(Team.department_id == department_id)
    return {"items": [_serialize(team) for team in database.scalars(statement).all()]}


@router.get("/teams/available-for-upload")
def available_upload_teams(
    current_user: Annotated[User, Depends(require_permission("file_upload"))],
    database: Annotated[Session, Depends(get_db)],
):
    """Return only safe Team choices needed by the document upload form."""
    role_name = current_user.role.name.strip().lower() if current_user.role else ""
    statement = select(Team).options(joinedload(Team.department)).order_by(Team.department_id, Team.name)
    if role_name in {"employee", "leader"}:
        statement = statement.where(Team.id == current_user.team_id)
    elif role_name == "manager":
        statement = statement.where(Team.department_id == current_user.department_id)
    elif role_name != "admin":
        return {"items": []}
    return {"items": [_serialize(team) for team in database.scalars(statement).all()]}


@router.get("/teams/{team_id}")
def get_team(
    team_id: int,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    team = database.scalar(select(Team).options(joinedload(Team.department)).where(Team.id == team_id))
    if team is None:
        raise HTTPException(status_code=404, detail="小组不存在")
    return _serialize(team)


@router.post("/teams", status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("user_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    if database.get(Department, payload.department_id) is None:
        raise HTTPException(status_code=400, detail="部门不存在")
    team = Team(name=payload.name, department_id=payload.department_id, description=payload.description)
    database.add(team)
    try:
        database.commit()
        database.refresh(team)
    except IntegrityError as exc:
        database.rollback()
        raise HTTPException(status_code=409, detail="该部门已存在同名小组") from exc
    write_audit_log(
        database, action="team_create", resource_type="team", result="success",
        user_id=current_user.id, resource_id=team.id, resource_name=team.name,
        detail=f"department_id={team.department_id}",
        ip_address=request.client.host if request.client else None,
    )
    return _serialize(database.scalar(select(Team).options(joinedload(Team.department)).where(Team.id == team.id)))
