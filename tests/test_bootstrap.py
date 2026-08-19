import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def bootstrap_context(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    app_data = tmp_path / "bootstrap-data"
    environment = os.environ.copy()
    environment["APP_DATA_DIR"] = str(app_data)
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(project_root / "alembic.ini"), "upgrade", "head"],
        cwd=project_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    from app.database import bootstrap

    engine = create_engine(f"sqlite:///{(app_data / 'app.db').as_posix()}")
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(bootstrap, "engine", engine)
    monkeypatch.setattr(bootstrap, "SessionLocal", testing_session)
    yield bootstrap, testing_session
    engine.dispose()


def test_bootstrap_creates_first_admin_permissions_department_and_audit(bootstrap_context):
    bootstrap, testing_session = bootstrap_context
    from app.auth.password import verify_password
    from app.models.audit_log import AuditLog
    from app.models.department import Department
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.user import User

    output = []
    password = "InitialAdminPass123"
    admin = bootstrap.bootstrap_system(
        username="first_admin",
        real_name="First Administrator",
        department="Technology",
        password=password,
        output_function=output.append,
    )

    assert admin.status == "active"
    with testing_session() as database:
        stored = database.scalar(select(User).where(User.username == "first_admin"))
        assert stored.role.name == "admin"
        assert stored.department.name == "Technology"
        assert verify_password(password, stored.password_hash)
        assert {role.name for role in database.scalars(select(Role)).all()} == {"admin", "manager", "leader", "employee"}
        assert {permission.code for permission in database.scalars(select(Permission)).all()} >= {"user_manage", "file_view", "model_manage", "audit_view"}
        assert database.scalar(select(Department).where(Department.name == "Technology")) is not None
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "system_bootstrap_admin"))
        assert audit.user_id is None
        assert audit.resource_id == str(stored.id)
        assert audit.resource_name == "first_admin"
        assert audit.result == "success"
        assert password not in str(audit.__dict__)
    assert password not in "\n".join(output)


def test_bootstrap_is_idempotent_and_existing_admin_blocks_second(bootstrap_context):
    bootstrap, testing_session = bootstrap_context
    bootstrap.bootstrap_system(username="only_admin", real_name="Admin", department="", password="InitialAdminPass123", output_function=lambda value: None)
    output = []
    second = bootstrap.bootstrap_system(
        username="second_admin",
        real_name="Second",
        department="",
        password="SecondAdminPass123",
        output_function=output.append,
    )
    assert second is None
    assert "系统已经初始化" in output[0]
    from app.models.user import User
    with testing_session() as database:
        assert len(database.scalars(select(User)).all()) == 1


def test_roles_without_active_admin_still_allow_bootstrap(bootstrap_context):
    bootstrap, testing_session = bootstrap_context
    from app.database.seed_permissions import seed_default_permissions
    from app.models.user import User

    with testing_session() as database:
        seed_default_permissions(database)
        assert database.scalar(select(User)) is None
    assert bootstrap.bootstrap_system(
        username="recovery_admin", real_name="Recovery", department="", password="RecoveryAdminPass123", output_function=lambda value: None,
    ) is not None


def test_bootstrap_rejects_database_not_at_head(monkeypatch):
    from app.database import bootstrap

    monkeypatch.setattr(bootstrap, "database_is_at_alembic_head", lambda: False)
    with pytest.raises(bootstrap.BootstrapError, match="alembic upgrade head"):
        bootstrap.bootstrap_system(username="admin", real_name="Admin", password="InitialAdminPass123")


def test_environment_password_mode_does_not_echo_secret(bootstrap_context, monkeypatch):
    bootstrap, testing_session = bootstrap_context
    secret = "EnvironmentAdminPass123"
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", secret)
    output = []

    def forbidden_getpass(prompt):
        pytest.fail("getpass should not be called in environment mode")

    bootstrap.bootstrap_system(
        username="env_admin",
        real_name="Environment Admin",
        department="",
        password_function=forbidden_getpass,
        output_function=output.append,
    )
    assert secret not in "\n".join(output)
    from app.models.audit_log import AuditLog
    with testing_session() as database:
        assert secret not in str(database.scalar(select(AuditLog)).__dict__)
