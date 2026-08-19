"""Secure, one-time CLI bootstrap for the first enterprise administrator."""
import argparse
from getpass import getpass
import os
from typing import Callable

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.database.database import SessionLocal, engine
from app.database.seed_permissions import seed_default_permissions
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.schemas.user_management import ManagedUserCreate
from app.services.audit_service import write_audit_log


InputFunction = Callable[[str], str]
PasswordFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


class BootstrapError(RuntimeError):
    """Safe operator-facing bootstrap failure."""


def database_is_at_alembic_head() -> bool:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())
    with engine.connect() as connection:
        current_heads = set(MigrationContext.configure(connection).get_current_heads())
    return bool(expected_heads) and current_heads == expected_heads


def _active_admin(database: Session) -> User | None:
    return database.scalar(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(User.status == "active", Role.name == "admin")
        .limit(1)
    )


def _resolve_department(database: Session, department_name: str | None) -> Department | None:
    normalized = (department_name or "").strip()
    if not normalized:
        return None
    department = database.scalar(select(Department).where(Department.name == normalized))
    if department is None:
        department = Department(name=normalized)
        database.add(department)
        database.flush()
    return department


def bootstrap_system(
    *,
    username: str | None = None,
    real_name: str | None = None,
    department: str | None = None,
    password: str | None = None,
    input_function: InputFunction = input,
    password_function: PasswordFunction = getpass,
    output_function: OutputFunction = print,
) -> User | None:
    if not database_is_at_alembic_head():
        raise BootstrapError("数据库未升级到最新版本，请先执行：python -m alembic upgrade head")

    with SessionLocal() as database:
        # Always repair missing default permissions first. The seed is
        # idempotent and remains the single source of the RBAC matrix.
        seed_default_permissions(database)
        if _active_admin(database) is not None:
            output_function("系统已经初始化。后续管理员请由已有管理员通过 POST /users 创建。")
            return None

        resolved_username = (username or input_function("管理员用户名：")).strip()
        resolved_real_name = (real_name or input_function("管理员姓名：")).strip()
        resolved_department = department
        if resolved_department is None:
            resolved_department = input_function("初始部门（可选，直接回车跳过）：").strip() or None

        resolved_password = password
        if resolved_password is None:
            resolved_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
        if resolved_password is None:
            first_password = password_function("管理员密码：")
            confirmation = password_function("确认管理员密码：")
            if first_password != confirmation:
                raise BootstrapError("两次输入的密码不一致")
            resolved_password = first_password

        admin_role = database.scalar(select(Role).where(Role.name == "admin"))
        if admin_role is None:
            raise BootstrapError("默认admin角色初始化失败")
        try:
            validated = ManagedUserCreate(
                username=resolved_username,
                password=resolved_password,
                real_name=resolved_real_name,
                role_id=admin_role.id,
                department_id=None,
            )
        except ValidationError as exc:
            # Do not include validation input values, which could contain the password.
            raise BootstrapError("管理员账号输入不符合安全规则") from exc

        if database.scalar(select(User.id).where(User.username == validated.username)) is not None:
            raise BootstrapError("用户名已存在，请选择其他管理员用户名")

        try:
            admin = User(
                username=validated.username,
                real_name=validated.real_name,
                password_hash=hash_password(resolved_password),
                role=admin_role,
                department=_resolve_department(database, resolved_department),
                status="active",
            )
            database.add(admin)
            database.commit()
            database.refresh(admin)
        except (IntegrityError, ValueError) as exc:
            database.rollback()
            write_audit_log(
                database,
                action="system_bootstrap_admin",
                resource_type="user",
                resource_name=resolved_username,
                result="failed",
                detail=f"bootstrap_failed:{type(exc).__name__}",
            )
            raise BootstrapError("首个管理员创建失败") from exc

        write_audit_log(
            database,
            action="system_bootstrap_admin",
            resource_type="user",
            resource_id=admin.id,
            resource_name=admin.username,
            result="success",
            detail="initial_admin_created",
            user_id=None,
        )
        output_function(f"系统初始化成功，管理员账号：{admin.username}")
        return admin


def main() -> int:
    parser = argparse.ArgumentParser(description="安全初始化企业知识库首个管理员")
    parser.add_argument("--username")
    parser.add_argument("--real-name")
    parser.add_argument("--department")
    arguments = parser.parse_args()
    try:
        bootstrap_system(
            username=arguments.username,
            real_name=arguments.real_name,
            department=arguments.department,
        )
    except BootstrapError as exc:
        print(f"初始化失败：{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
