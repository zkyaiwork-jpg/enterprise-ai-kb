import sqlite3
import importlib

from sqlalchemy import inspect


def test_database_initialization_creates_sqlite_file(tmp_path, monkeypatch):
    from app.database import database

    init_db_module = importlib.import_module("app.database.init_db")

    database_path = tmp_path / "app.db"
    test_engine = database.create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(init_db_module, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(init_db_module, "engine", test_engine)

    init_db_module.init_db()

    assert database_path.is_file()
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA schema_version").fetchone() is not None


def test_database_session_dependency_closes_session():
    from app.database.database import get_db

    dependency = get_db()
    session = next(dependency)
    assert session.is_active
    dependency.close()


def test_enterprise_models_create_expected_tables_and_relationships(tmp_path):
    from app.database.database import Base, create_engine
    from app.models import Department, Permission, Role, User, role_permissions

    database_path = tmp_path / "enterprise-models.db"
    test_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(bind=test_engine)
    inspector = inspect(test_engine)

    assert {"departments", "roles", "permissions", "users", "role_permissions"}.issubset(
        set(inspector.get_table_names())
    )
    assert {column["name"] for column in inspector.get_columns("users")} == {
        "id", "username", "password_hash", "real_name", "role_id",
        "department_id", "team_id", "status", "token_version", "created_time",
    }
    assert {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("users")} == {
        "roles", "departments", "teams",
    }
    assert set(role_permissions.primary_key.columns.keys()) == {"role_id", "permission_id"}
    assert User.role.property.back_populates == "users"
    assert User.department.property.back_populates == "users"
    assert Role.permissions.property.back_populates == "roles"
    assert Permission.roles.property.back_populates == "permissions"
    assert Department.__tablename__ == "departments"
