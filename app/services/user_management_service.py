from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth.password import hash_password
from app.models.audit_log import AuditLog
from app.models.department import Department
from app.models.document import Document
from app.models.role import Role
from app.models.user import User
from app.utils.datetime import serialize_utc_datetime
from app.models.team import Team


def _get_role(database: Session, role_id: int) -> Role:
    role = database.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=400, detail="角色不存在")
    return role


def _get_department(database: Session, department_id: int | None) -> Department | None:
    if department_id is None:
        return None
    department = database.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=400, detail="部门不存在")
    return department


def _get_team(database: Session, team_id: int | None) -> Team | None:
    if team_id is None:
        return None
    team = database.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=400, detail="小组不存在")
    return team


def _validate_org_assignment(role: Role | None, department: Department | None, team: Team | None) -> None:
    role_name = role.name.strip().lower() if role else None
    if team is not None and (department is None or team.department_id != department.id):
        raise HTTPException(status_code=400, detail="小组必须属于用户所在部门")
    if role_name in {"employee", "leader"} and team is None:
        raise HTTPException(status_code=400, detail="员工和组长必须分配小组")


def get_managed_user(database: Session, user_id: int) -> User:
    user = database.scalar(
        select(User)
        .options(joinedload(User.role), joinedload(User.department), joinedload(User.team))
        .where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _duplicate_name_error() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail="已存在同名用户，请使用可区分的姓名，例如“张伟-市场部”。",
    )


def create_managed_user(database: Session, *, username: str, password: str, real_name: str | None, role_id: int, department_id: int | None, team_id: int | None = None) -> User:
    if database.scalar(select(User.id).where(User.username == username)) is not None:
        raise _duplicate_name_error()
    role = _get_role(database, role_id)
    department = _get_department(database, department_id)
    team = _get_team(database, team_id)
    _validate_org_assignment(role, department, team)
    user = User(
        username=username,
        password_hash=hash_password(password),
        real_name=real_name or username,
        role=role,
        department=department,
        team=team,
        status="active",
    )
    database.add(user)
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise _duplicate_name_error() from exc
    database.refresh(user)
    return get_managed_user(database, user.id)


def list_managed_users(database: Session, *, page: int, page_size: int, status_filter: str | None, department_id: int | None, role_id: int | None) -> tuple[list[User], int]:
    filters = []
    if status_filter:
        filters.append(User.status == status_filter)
    if department_id is not None:
        filters.append(User.department_id == department_id)
    if role_id is not None:
        filters.append(User.role_id == role_id)
    total = int(database.scalar(select(func.count(User.id)).where(*filters)) or 0)
    users = list(database.scalars(
        select(User)
        .options(joinedload(User.role), joinedload(User.department), joinedload(User.team))
        .where(*filters)
        .order_by(User.created_time.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    return users, total


def _active_admin_count(database: Session) -> int:
    return int(database.scalar(
        select(func.count(User.id))
        .join(Role, User.role_id == Role.id)
        .where(User.status == "active", Role.name == "admin")
    ) or 0)


def _admin_count(database: Session) -> int:
    return int(database.scalar(
        select(func.count(User.id))
        .join(Role, User.role_id == Role.id)
        .where(Role.name == "admin")
    ) or 0)


def update_managed_user(database: Session, current_user: User, target: User, *, changes: dict) -> tuple[User, list[str]]:
    changed_fields = []
    new_status = changes.get("status") if "status" in changes else target.status
    new_role = _get_role(database, changes["role_id"]) if "role_id" in changes else target.role
    new_department = _get_department(database, changes["department_id"]) if "department_id" in changes else target.department
    new_team = _get_team(database, changes["team_id"]) if "team_id" in changes else target.team
    if {"role_id", "department_id", "team_id"}.intersection(changes):
        _validate_org_assignment(new_role, new_department, new_team)

    if current_user.id == target.id and new_status == "inactive":
        raise HTTPException(status_code=409, detail="不能停用当前操作账号")
    target_is_active_admin = target.status == "active" and target.role and target.role.name == "admin"
    removes_active_admin = target_is_active_admin and (
        new_status != "active" or new_role is None or new_role.name != "admin"
    )
    if removes_active_admin and _active_admin_count(database) <= 1:
        raise HTTPException(status_code=409, detail="不能停用或降级最后一个有效管理员")

    if "username" in changes:
        username = changes["username"]
        duplicate_id = database.scalar(
            select(User.id).where(User.username == username, User.id != target.id)
        )
        if duplicate_id is not None:
            raise _duplicate_name_error()
        target.username = username
        target.real_name = username
        changed_fields.extend(["username", "real_name"])
    elif "real_name" in changes:
        target.real_name = changes["real_name"]
        changed_fields.append("real_name")
    if "role_id" in changes:
        target.role = new_role
        changed_fields.append("role_id")
    if "department_id" in changes:
        target.department = new_department
        changed_fields.append("department_id")
    if "team_id" in changes:
        target.team = new_team
        changed_fields.append("team_id")
    if "status" in changes:
        target.status = changes["status"]
        changed_fields.append("status")
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise _duplicate_name_error() from exc
    database.refresh(target)
    return get_managed_user(database, target.id), changed_fields


def delete_managed_user(
    database: Session,
    current_user: User,
    target: User,
    *,
    ip_address: str | None = None,
) -> None:
    if current_user.id == target.id:
        raise HTTPException(status_code=409, detail="不能删除当前登录用户")

    target_is_admin = bool(target.role and target.role.name == "admin")
    if target_is_admin and _admin_count(database) <= 1:
        raise HTTPException(status_code=409, detail="不能删除系统最后一个管理员")
    if target_is_admin and target.status == "active" and _active_admin_count(database) <= 1:
        raise HTTPException(status_code=409, detail="不能删除系统最后一个有效管理员")

    if database.scalar(select(Document.id).where(Document.uploader_id == target.id).limit(1)) is not None:
        raise HTTPException(
            status_code=409,
            detail="该用户仍有关联文档，请先处理文档归属后再删除",
        )
    target_id = target.id
    target_username = target.username
    role_name = target.role.name if target.role else "unassigned"
    department_name = target.department.name if target.department else "unassigned"
    audit_log = AuditLog(
        user_id=current_user.id,
        actor_name=current_user.username,
        action="user_delete",
        resource_type="user",
        resource_id=str(target_id),
        resource_name=target_username,
        result="success",
        detail=f"username={target_username};role={role_name};department={department_name}",
        ip_address=ip_address,
    )

    database.delete(target)
    try:
        database.flush()
        database.add(audit_log)
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise HTTPException(
            status_code=409,
            detail="该用户仍有关联企业数据，暂时无法删除",
        ) from exc


def invalidate_user_tokens(target: User) -> None:
    """Invalidate every JWT issued with the user's current server-side version."""
    target.token_version += 1


def reset_managed_user_password(database: Session, target: User, new_password: str) -> None:
    target.password_hash = hash_password(new_password)
    invalidate_user_tokens(target)
    database.commit()


def serialize_managed_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": {"id": user.role.id, "name": user.role.name} if user.role else None,
        "department": {"id": user.department.id, "name": user.department.name} if user.department else None,
        "team": {"id": user.team.id, "name": user.team.name} if user.team else None,
        "status": user.status,
        "created_time": serialize_utc_datetime(user.created_time),
    }
