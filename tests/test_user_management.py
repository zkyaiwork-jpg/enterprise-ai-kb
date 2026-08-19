import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def user_management_context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "user-management-test-secret-over-32-bytes")
    from app.auth.jwt import create_access_token
    from app.auth.password import hash_password
    from app.database.database import Base, get_db
    from app.database.seed_permissions import seed_default_permissions
    from app.main import app
    from app.models import Department, Role, Team, User

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as database:
        seed_default_permissions(database)
        roles = {role.name: role for role in database.scalars(select(Role)).all()}
        departments = {"a": Department(name="Engineering"), "b": Department(name="Finance")}
        database.add_all(departments.values())
        database.flush()
        teams = {name: Team(name=f"Team {name.upper()}", department=department) for name, department in departments.items()}
        database.add_all(teams.values())
        admin = User(username="manage_admin", password_hash=hash_password("AdminPass123"), real_name="Admin", role=roles["admin"], department=departments["a"], status="active")
        employee = User(username="manage_employee", password_hash=hash_password("EmployeePass123"), real_name="Employee", role=roles["employee"], department=departments["a"], team=teams["a"], status="active")
        database.add_all([admin, employee])
        database.commit()
        ids = {"admin": admin.id, "employee": employee.id}
        tokens = {"admin": create_access_token(admin.id, admin.token_version), "employee": create_access_token(employee.id, employee.token_version)}
        role_ids = {name: role.id for name, role in roles.items()}
        department_ids = {name: department.id for name, department in departments.items()}

    def override_get_db():
        with testing_session() as database:
            yield database
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, tokens, ids, role_ids, department_ids, testing_session
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create(client, token, username, role_id, department_id=None, password="StrongPass123", team_id=None):
    if team_id is None:
        roles = client.get("/roles", headers=_headers(token)).json()["items"]
        role_name = next((item["name"] for item in roles if item["id"] == role_id), None)
        if role_name in {"employee", "leader"} and department_id is None:
            departments = client.get("/departments", headers=_headers(token)).json()["items"]
            department_id = departments[0]["id"] if departments else None
        if role_name in {"employee", "leader"} and department_id is not None:
            teams = client.get("/teams", headers=_headers(token), params={"department_id": department_id}).json()["items"]
            team_id = teams[0]["id"] if teams else None
    return client.post("/users", headers=_headers(token), json={
        "username": username, "password": password, "real_name": username,
        "role_id": role_id, "department_id": department_id, "team_id": team_id,
    })


def test_admin_creates_employee_and_leader_with_safe_responses(user_management_context):
    client, tokens, _, roles, departments, testing_session = user_management_context
    from app.models.audit_log import AuditLog
    from app.models.user import User

    employee = _create(client, tokens["admin"], "new_employee", roles["employee"], departments["a"])
    leader = _create(client, tokens["admin"], "new_leader", roles["leader"], departments["a"])
    assert employee.status_code == leader.status_code == 201
    assert employee.json()["role"]["name"] == "employee"
    assert leader.json()["role"]["name"] == "leader"
    assert employee.json()["created_time"].endswith("Z")
    assert leader.json()["created_time"].endswith("Z")
    assert "password" not in str(employee.json()).lower()
    with testing_session() as database:
        stored = database.scalar(select(User).where(User.username == "new_employee"))
        assert stored.token_version == 1
        assert stored.password_hash.startswith("$2") and stored.password_hash != "StrongPass123"
        audits = database.scalars(select(AuditLog).where(AuditLog.action == "user_create")).all()
        assert len(audits) == 2
        assert "StrongPass123" not in str([(item.detail, item.resource_name) for item in audits])


def test_create_user_requires_auth_and_user_manage_and_unique_username(user_management_context):
    client, tokens, _, roles, _, _ = user_management_context
    payload = {"username": "blocked_user", "password": "StrongPass123", "real_name": "Blocked", "role_id": roles["employee"]}
    assert client.post("/users", json=payload).status_code == 401
    assert client.post("/users", headers=_headers(tokens["employee"]), json=payload).status_code == 403
    assert _create(client, tokens["admin"], "unique_user", roles["employee"]).status_code == 201
    assert _create(client, tokens["admin"], "unique_user", roles["leader"]).status_code == 409


def test_user_list_detail_and_filters_never_return_password_hash(user_management_context):
    client, tokens, ids, roles, departments, _ = user_management_context
    assert client.get("/users", headers=_headers(tokens["employee"])).status_code == 403
    response = client.get("/users", headers=_headers(tokens["admin"]), params={"page": 1, "page_size": 10, "role_id": roles["employee"]})
    assert response.status_code == 200 and response.json()["total"] == 1
    detail = client.get(f"/users/{ids['employee']}", headers=_headers(tokens["admin"]))
    assert detail.status_code == 200
    assert detail.json()["department"]["id"] == departments["a"]
    assert response.json()["items"][0]["created_time"].endswith("Z")
    assert detail.json()["created_time"].endswith("Z")
    assert "password" not in str(response.json()).lower()
    assert "password" not in str(detail.json()).lower()


def test_admin_updates_role_department_and_status_with_audit(user_management_context):
    client, tokens, ids, roles, departments, testing_session = user_management_context
    from app.models.audit_log import AuditLog
    response = client.patch(f"/users/{ids['employee']}", headers=_headers(tokens["admin"]), json={
        "role_id": roles["leader"], "department_id": departments["b"],
        "team_id": client.get("/teams", headers=_headers(tokens["admin"]), params={"department_id": departments["b"]}).json()["items"][0]["id"],
        "status": "inactive",
    })
    assert response.status_code == 200
    assert response.json()["role"]["name"] == "leader"
    assert response.json()["department"]["id"] == departments["b"]
    assert response.json()["status"] == "inactive"
    with testing_session() as database:
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "user_status_change"))
        assert audit and "role_id" in audit.detail and "department_id" in audit.detail


def test_inactive_user_cannot_login_or_use_old_jwt(user_management_context):
    client, tokens, ids, _, _, _ = user_management_context
    response = client.patch(f"/users/{ids['employee']}", headers=_headers(tokens["admin"]), json={"status": "inactive"})
    assert response.status_code == 200
    login = client.post("/auth/login", json={"username": "manage_employee", "password": "EmployeePass123"})
    assert login.status_code == 401
    assert client.get("/documents", headers=_headers(tokens["employee"])).status_code == 401
    assert client.get("/search", headers=_headers(tokens["employee"]), params={"query": "policy"}).status_code == 401
    assert client.post("/chat", headers=_headers(tokens["employee"]), json={"question": "policy"}).status_code == 401


def test_password_reset_invalidates_old_password_and_audits_without_secret(user_management_context):
    client, tokens, ids, _, _, testing_session = user_management_context
    from app.models.audit_log import AuditLog
    reset = client.post(f"/users/{ids['employee']}/reset-password", headers=_headers(tokens["admin"]), json={"new_password": "NewEmployeePass123"})
    assert reset.status_code == 200 and "password_hash" not in str(reset.json())
    assert client.get("/documents", headers=_headers(tokens["employee"])).status_code == 401
    assert client.post("/auth/login", json={"username": "manage_employee", "password": "EmployeePass123"}).status_code == 401
    new_login = client.post("/auth/login", json={"username": "manage_employee", "password": "NewEmployeePass123"})
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]
    assert client.get("/documents", headers=_headers(new_token)).status_code == 200
    with testing_session() as database:
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "user_password_reset"))
        assert audit.detail == "password_reset;tokens_invalidated=true"
        assert "NewEmployeePass123" not in str(audit.__dict__)


def test_admin_cannot_disable_self_or_remove_last_active_admin(user_management_context):
    client, tokens, ids, roles, _, _ = user_management_context
    self_disable = client.patch(f"/users/{ids['admin']}", headers=_headers(tokens["admin"]), json={"status": "inactive"})
    downgrade = client.patch(f"/users/{ids['admin']}", headers=_headers(tokens["admin"]), json={"role_id": roles["manager"]})
    assert self_disable.status_code == 409
    assert downgrade.status_code == 409


def test_department_create_list_and_audit(user_management_context):
    client, tokens, _, _, _, testing_session = user_management_context
    from app.models.audit_log import AuditLog
    assert client.post("/departments", json={"name": "HR"}).status_code == 401
    assert client.post("/departments", headers=_headers(tokens["employee"]), json={"name": "HR"}).status_code == 403
    created = client.post("/departments", headers=_headers(tokens["admin"]), json={"name": "HR", "description": "People"})
    assert created.status_code == 201
    assert created.json()["created_time"].endswith("Z")
    listed = client.get("/departments", headers=_headers(tokens["admin"]))
    assert listed.status_code == 200 and "HR" in [item["name"] for item in listed.json()["items"]]
    assert all(item["created_time"].endswith("Z") for item in listed.json()["items"])
    with testing_session() as database:
        audit = database.scalar(select(AuditLog).where(AuditLog.action == "department_create"))
        assert audit and audit.resource_name == "HR"


def test_team_create_list_and_auth_register_use_utc_api_contract(user_management_context):
    client, tokens, _, roles, departments, _ = user_management_context
    team = client.post(
        "/teams",
        headers=_headers(tokens["admin"]),
        json={"name": "Time Contract Team", "department_id": departments["a"]},
    )
    assert team.status_code == 201
    assert team.json()["created_time"].endswith("Z")

    listed = client.get("/teams", headers=_headers(tokens["admin"]))
    assert listed.status_code == 200
    assert all(item["created_time"].endswith("Z") for item in listed.json()["items"])

    registered = client.post(
        "/auth/register",
        headers=_headers(tokens["admin"]),
        json={
            "username": "utc_registered_user",
            "password": "StrongPass123",
            "real_name": "UTC Registered User",
            "role_id": roles["manager"],
            "department_id": departments["a"],
        },
    )
    assert registered.status_code == 201
    assert registered.json()["created_time"].endswith("Z")


def test_name_is_username_create_and_edit_contract(user_management_context):
    client, tokens, _, roles, departments, testing_session = user_management_context
    from app.models.user import User

    created = client.post("/users", headers=_headers(tokens["admin"]), json={
        "username": "张三",
        "password": "StrongPass123",
        "role_id": roles["manager"],
        "department_id": departments["a"],
    })
    assert created.status_code == 201
    assert created.json()["username"] == created.json()["real_name"] == "张三"

    duplicate = client.post("/users", headers=_headers(tokens["admin"]), json={
        "username": "张三",
        "password": "StrongPass123",
        "role_id": roles["manager"],
    })
    assert duplicate.status_code == 409
    assert "已存在同名用户" in duplicate.json()["detail"]

    updated = client.patch(
        f"/users/{created.json()['id']}",
        headers=_headers(tokens["admin"]),
        json={"username": "张三-市场部"},
    )
    assert updated.status_code == 200
    assert updated.json()["username"] == updated.json()["real_name"] == "张三-市场部"
    assert client.post("/auth/login", json={"username": "张三", "password": "StrongPass123"}).status_code == 401
    assert client.post("/auth/login", json={"username": "张三-市场部", "password": "StrongPass123"}).status_code == 200
    with testing_session() as database:
        stored = database.get(User, created.json()["id"])
        assert stored and stored.username == stored.real_name == "张三-市场部"


def test_admin_deletes_unassociated_user_and_writes_atomic_audit(user_management_context):
    client, tokens, ids, roles, departments, testing_session = user_management_context
    from app.models.audit_log import AuditLog
    from app.models.user import User

    created = _create(client, tokens["admin"], "待删除成员", roles["manager"], departments["a"])
    target_id = created.json()["id"]
    deleted = client.delete(f"/users/{target_id}", headers=_headers(tokens["admin"]))
    assert deleted.status_code == 204
    assert client.post("/auth/login", json={"username": "待删除成员", "password": "StrongPass123"}).status_code == 401
    listed_ids = {
        item["id"]
        for item in client.get("/users", headers=_headers(tokens["admin"])).json()["items"]
    }
    assert target_id not in listed_ids
    assert ids["employee"] in listed_ids

    with testing_session() as database:
        assert database.get(User, target_id) is None
        audit = database.scalar(select(AuditLog).where(
            AuditLog.action == "user_delete",
            AuditLog.resource_id == str(target_id),
        ))
        assert audit and audit.user_id == ids["admin"]
        assert audit.resource_name == "待删除成员"
        assert "password" not in (audit.detail or "").lower()
        assert database.execute(text("PRAGMA foreign_key_check")).all() == []


def test_delete_requires_auth_and_user_manage(user_management_context):
    client, tokens, _, roles, departments, _ = user_management_context
    target = _create(client, tokens["admin"], "delete_permission_target", roles["manager"], departments["a"])
    target_id = target.json()["id"]
    assert client.delete(f"/users/{target_id}").status_code == 401
    assert client.delete(f"/users/{target_id}", headers=_headers(tokens["employee"])).status_code == 403
    assert client.get(f"/users/{target_id}", headers=_headers(tokens["admin"])).status_code == 200


def test_delete_protects_current_user_last_admin_and_missing_user(user_management_context):
    client, tokens, ids, roles, departments, _ = user_management_context
    self_delete = client.delete(f"/users/{ids['admin']}", headers=_headers(tokens["admin"]))
    assert self_delete.status_code == 409
    assert self_delete.json()["detail"] == "不能删除当前登录用户"

    manager = _create(client, tokens["admin"], "delete_manager", roles["manager"], departments["a"])
    assert manager.status_code == 201
    login = client.post("/auth/login", json={"username": "delete_manager", "password": "StrongPass123"})
    manager_token = login.json()["access_token"]
    last_admin = client.delete(f"/users/{ids['admin']}", headers=_headers(manager_token))
    assert last_admin.status_code == 409
    assert "最后一个管理员" in last_admin.json()["detail"]
    assert client.delete("/users/999999", headers=_headers(tokens["admin"])).status_code == 404


def test_delete_blocks_user_with_enterprise_document(user_management_context):
    client, tokens, _, roles, departments, testing_session = user_management_context
    from app.models.document import Document
    from app.models.user import User

    target = _create(client, tokens["admin"], "document_owner_delete", roles["manager"], departments["a"])
    target_id = target.json()["id"]
    with testing_session() as database:
        database.add(Document(
            filename="retained-enterprise-document.txt",
            original_name="retained-enterprise-document.txt",
            uploader_id=target_id,
        ))
        database.commit()

    response = client.delete(f"/users/{target_id}", headers=_headers(tokens["admin"]))
    assert response.status_code == 409
    assert "关联文档" in response.json()["detail"]
    with testing_session() as database:
        assert database.get(User, target_id) is not None
        assert database.scalar(select(Document).where(Document.uploader_id == target_id)) is not None
        assert database.execute(text("PRAGMA foreign_key_check")).all() == []


def test_delete_preserves_actor_audit_history_with_name_snapshot(user_management_context):
    client, tokens, _, roles, departments, testing_session = user_management_context
    from app.models.audit_log import AuditLog
    from app.models.user import User

    target = _create(client, tokens["admin"], "audited_delete_target", roles["manager"], departments["a"])
    target_id = target.json()["id"]
    with testing_session() as database:
        audit = AuditLog(
            user_id=target_id,
            actor_name="audited_delete_target",
            action="document_view",
            resource_type="document",
            resource_id="42",
            resource_name="retained-policy.txt",
            result="success",
        )
        database.add(audit)
        database.commit()
        audit_id = audit.id

    response = client.delete(f"/users/{target_id}", headers=_headers(tokens["admin"]))
    assert response.status_code == 204
    with testing_session() as database:
        assert database.get(User, target_id) is None
        retained_audit = database.get(AuditLog, audit_id)
        assert retained_audit and retained_audit.user_id is None
        assert retained_audit.actor_name == "audited_delete_target"


def test_delete_cascades_personal_conversation_and_messages(user_management_context):
    client, tokens, _, roles, departments, testing_session = user_management_context
    from app.models.chat_message import ChatMessage, ChatRole
    from app.models.conversation import Conversation

    target = _create(client, tokens["admin"], "conversation_delete_target", roles["manager"], departments["a"])
    target_id = target.json()["id"]
    with testing_session() as database:
        conversation = Conversation(user_id=target_id, title="Private conversation")
        conversation.messages.append(ChatMessage(role=ChatRole.USER, content="question", sources=[]))
        database.add(conversation)
        database.commit()
        conversation_id = conversation.id
        message_id = conversation.messages[0].id

    response = client.delete(f"/users/{target_id}", headers=_headers(tokens["admin"]))
    assert response.status_code == 204
    with testing_session() as database:
        assert database.get(Conversation, conversation_id) is None
        assert database.get(ChatMessage, message_id) is None
        assert database.execute(text("PRAGMA foreign_key_check")).all() == []


def test_managed_user_complete_lifecycle_in_isolated_database(user_management_context):
    client, tokens, _, roles, departments, _ = user_management_context

    created = client.post("/users", headers=_headers(tokens["admin"]), json={
        "username": "生命周期测试用户",
        "password": "LifecyclePass123",
        "role_id": roles["manager"],
        "department_id": departments["a"],
    })
    assert created.status_code == 201
    user_id = created.json()["id"]

    edited = client.patch(f"/users/{user_id}", headers=_headers(tokens["admin"]), json={
        "username": "生命周期测试用户-财务部",
        "department_id": departments["b"],
    })
    assert edited.status_code == 200
    assert edited.json()["username"] == "生命周期测试用户-财务部"
    assert edited.json()["department"]["id"] == departments["b"]

    disabled = client.patch(
        f"/users/{user_id}",
        headers=_headers(tokens["admin"]),
        json={"status": "inactive"},
    )
    assert disabled.status_code == 200 and disabled.json()["status"] == "inactive"
    enabled = client.patch(
        f"/users/{user_id}",
        headers=_headers(tokens["admin"]),
        json={"status": "active"},
    )
    assert enabled.status_code == 200 and enabled.json()["status"] == "active"

    reset = client.post(
        f"/users/{user_id}/reset-password",
        headers=_headers(tokens["admin"]),
        json={"new_password": "LifecycleNewPass123"},
    )
    assert reset.status_code == 200
    assert client.post("/auth/login", json={
        "username": "生命周期测试用户-财务部",
        "password": "LifecycleNewPass123",
    }).status_code == 200

    deleted = client.delete(f"/users/{user_id}", headers=_headers(tokens["admin"]))
    assert deleted.status_code == 204
    assert client.post("/auth/login", json={
        "username": "生命周期测试用户-财务部",
        "password": "LifecycleNewPass123",
    }).status_code == 401
