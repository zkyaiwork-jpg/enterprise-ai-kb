import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


TEST_SECRET = "test-secret-key-for-rbac-permission-tests"


@pytest.fixture
def rbac_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    from app.auth.jwt import create_access_token
    from app.auth.password import hash_password
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models.role import Role
    from app.models.user import User

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with testing_session() as database:
        seed_default_permissions(database)
        admin_role = database.scalar(select(Role).where(Role.name == "admin"))
        employee_role = database.scalar(select(Role).where(Role.name == "employee"))
        admin = User(
            username="rbac_admin",
            password_hash=hash_password("StrongPass123"),
            real_name="管理员",
            role_id=admin_role.id,
            status="active",
        )
        employee = User(
            username="rbac_employee",
            password_hash=hash_password("StrongPass123"),
            real_name="普通员工",
            role_id=employee_role.id,
            status="active",
        )
        database.add_all([admin, employee])
        database.commit()
        database.refresh(admin)
        database.refresh(employee)
        user_ids = {"admin": admin.id, "employee": employee.id}

    def override_get_db():
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, {
                role: create_access_token(user_id, 1)
                for role, user_id in user_ids.items()
            }, testing_session
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_admin_can_access_file_delete_permission(rbac_context):
    client, tokens, _ = rbac_context

    response = client.get(
        "/auth/test-permission",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "file_delete权限验证通过"
    assert response.json()["username"] == "rbac_admin"


def test_employee_cannot_access_file_delete_permission(rbac_context):
    client, tokens, _ = rbac_context

    response = client.get(
        "/auth/test-permission",
        headers={"Authorization": f"Bearer {tokens['employee']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "当前用户没有所需权限"


def test_permission_seed_is_idempotent_and_builds_default_matrix(rbac_context):
    _, _, testing_session = rbac_context
    from app.database.seed_permissions import seed_default_permissions
    from app.models.permission import Permission
    from app.models.role import Role

    with testing_session() as database:
        seed_default_permissions(database)
        seed_default_permissions(database)
        roles = {role.name: {permission.code for permission in role.permissions} for role in database.scalars(select(Role)).all()}
        permission_codes = set(database.scalars(select(Permission.code)).all())

    assert set(roles) == {"admin", "manager", "leader", "employee"}
    assert permission_codes == {
        "user_manage", "file_upload", "file_view", "file_edit", "file_delete", "model_manage", "audit_view",
        "file_publish_team", "file_publish_department", "file_publish_company",
    }
    assert "audit_view" in roles["admin"]
    assert all("audit_view" not in roles[role] for role in ("manager", "leader", "employee"))
    assert "file_delete" in roles["admin"]
    assert "file_delete" not in roles["employee"]
    assert roles["employee"] == {"file_upload", "file_view"}
    assert {"file_publish_team", "file_publish_department", "file_publish_company"} <= roles["manager"]
    assert {"file_publish_team", "file_publish_department", "file_publish_company"} <= roles["admin"]
    assert "file_publish_team" in roles["leader"]
    assert "file_publish_department" not in roles["leader"]
    assert "file_publish_company" not in roles["leader"]
