from pathlib import Path
import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


EXPECTED_TABLES = {
    "users", "roles", "permissions", "role_permissions", "departments",
    "documents", "conversations", "chat_messages", "audit_logs", "model_configs", "teams", "alembic_version",
}


def _run_alembic(project_root: Path, app_data: Path, *arguments: str) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["APP_DATA_DIR"] = str(app_data)
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(project_root / "alembic.ini"), *arguments],
        cwd=project_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_empty_sqlite_database_upgrades_to_head_and_is_idempotent(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    app_data = tmp_path / "migration-data"
    _run_alembic(project_root, app_data, "upgrade", "head")
    _run_alembic(project_root, app_data, "upgrade", "head")

    engine = create_engine(f"sqlite:///{(app_data / 'app.db').as_posix()}")
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == EXPECTED_TABLES
    assert "token_version" in {column["name"] for column in inspector.get_columns("users")}
    with engine.connect() as connection:
        revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
    assert revision == "20260817_0006"


def test_existing_user_is_backfilled_and_downgrade_upgrade_is_safe(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    app_data = tmp_path / "migration-existing-user"
    _run_alembic(project_root, app_data, "upgrade", "20260812_0001")
    engine = create_engine(f"sqlite:///{(app_data / 'app.db').as_posix()}")
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users(username,password_hash,real_name,status,created_time) "
            "VALUES ('legacy-user','hash','Legacy User','active','2026-08-12')"
        ))

    _run_alembic(project_root, app_data, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT token_version FROM users WHERE username='legacy-user'")).scalar_one() == 1

    _run_alembic(project_root, app_data, "downgrade", "20260812_0001")
    assert "token_version" not in {column["name"] for column in inspect(engine).get_columns("users")}
    _run_alembic(project_root, app_data, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT token_version FROM users WHERE username='legacy-user'")).scalar_one() == 1


def test_model_config_migration_downgrade_and_upgrade(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    app_data = tmp_path / "migration-model-config"
    _run_alembic(project_root, app_data, "upgrade", "head")
    engine = create_engine(f"sqlite:///{(app_data / 'app.db').as_posix()}")
    assert "model_configs" in inspect(engine).get_table_names()
    _run_alembic(project_root, app_data, "downgrade", "20260812_0002")
    assert "model_configs" not in inspect(engine).get_table_names()
    _run_alembic(project_root, app_data, "upgrade", "head")
    assert "model_configs" in inspect(engine).get_table_names()


def test_document_publish_permission_data_migration(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    app_data = tmp_path / "migration-publish-permissions"
    _run_alembic(project_root, app_data, "upgrade", "20260812_0003")
    engine = create_engine(f"sqlite:///{(app_data / 'app.db').as_posix()}")
    with engine.begin() as connection:
        for role in ("admin", "manager", "leader", "employee"):
            connection.execute(
                text("INSERT INTO roles(name, description) VALUES (:name, :description)"),
                {"name": role, "description": role},
            )
    _run_alembic(project_root, app_data, "upgrade", "head")
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT r.name, p.code FROM roles r "
            "JOIN role_permissions rp ON rp.role_id=r.id "
            "JOIN permissions p ON p.id=rp.permission_id "
            "WHERE p.code LIKE 'file_publish_%'"
        )).all()
    grants = {}
    for role, code in rows:
        grants.setdefault(role, set()).add(code)
    assert grants["leader"] == {"file_publish_team"}
    assert grants["manager"] == {"file_publish_team", "file_publish_department", "file_publish_company"}
    assert grants["admin"] == {"file_publish_team", "file_publish_department", "file_publish_company"}
    assert "employee" not in grants
    _run_alembic(project_root, app_data, "downgrade", "20260812_0003")
    _run_alembic(project_root, app_data, "upgrade", "head")


def test_workspace_database_is_only_validated_never_modified():
    from app.database.baseline import validate_baseline_schema
    from app.database.database import engine

    before_tables = set(inspect(engine).get_table_names())
    valid, issues = validate_baseline_schema(engine)
    after_tables = set(inspect(engine).get_table_names())
    assert before_tables == after_tables
    if not valid:
        assert issues


def test_audit_actor_snapshot_migration_preserves_history_and_is_reversible(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    app_data = tmp_path / "migration-audit-actor"
    _run_alembic(project_root, app_data, "upgrade", "20260813_0005")
    engine = create_engine(f"sqlite:///{(app_data / 'app.db').as_posix()}")
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users(username,password_hash,real_name,status,token_version,created_time) "
            "VALUES ('audit-actor','hash','Audit Actor','active',1,'2026-08-17')"
        ))
        user_id = connection.execute(text(
            "SELECT id FROM users WHERE username='audit-actor'"
        )).scalar_one()
        connection.execute(text(
            "INSERT INTO audit_logs(user_id,action,resource_type,result,created_time) "
            "VALUES (:user_id,'login','auth','success','2026-08-17')"
        ), {"user_id": user_id})

    _run_alembic(project_root, app_data, "upgrade", "head")
    actor_column = next(
        column for column in inspect(engine).get_columns("audit_logs")
        if column["name"] == "actor_name"
    )
    assert actor_column["nullable"] is True
    with engine.begin() as connection:
        historical_log = connection.execute(text(
            "SELECT action, resource_type, result, actor_name "
            "FROM audit_logs WHERE user_id=:user_id"
        ), {"user_id": user_id}).one()
        assert historical_log == ("login", "auth", "success", None)
        connection.execute(text(
            "INSERT INTO audit_logs(user_id,actor_name,action,resource_type,resource_id,"
            "resource_name,result,created_time) "
            "VALUES (:user_id,'audit-actor','user_delete','user','42','temporary-user',"
            "'success','2026-08-17')"
        ), {"user_id": user_id})
        inserted_log = connection.execute(text(
            "SELECT actor_name, action, resource_name FROM audit_logs "
            "WHERE action='user_delete'"
        )).one()
        assert inserted_log == ("audit-actor", "user_delete", "temporary-user")

    _run_alembic(project_root, app_data, "downgrade", "20260813_0005")
    assert "actor_name" not in {column["name"] for column in inspect(engine).get_columns("audit_logs")}
    _run_alembic(project_root, app_data, "upgrade", "head")
    assert "actor_name" in {column["name"] for column in inspect(engine).get_columns("audit_logs")}
