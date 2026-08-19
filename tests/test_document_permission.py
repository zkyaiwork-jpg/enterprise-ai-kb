import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def document_permission_context():
    from app.database.database import Base
    from app.models import Department, Document, DocumentVisibility, Role, Team, User

    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    with Session(engine, expire_on_commit=False) as database:
        department_a = Department(name="研发部")
        department_b = Department(name="市场部")
        roles = {
            name: Role(name=name)
            for name in ("admin", "manager", "leader", "employee")
        }
        team_a = Team(name="Team A", department=department_a)
        team_b = Team(name="Team B", department=department_a)
        users = {
            "admin": User(username="admin_user", password_hash="hash", real_name="管理员", role=roles["admin"], department=department_b),
            "manager": User(username="manager_user", password_hash="hash", real_name="主管", role=roles["manager"], department=department_a),
            "leader": User(username="leader_user", password_hash="hash", real_name="组长", role=roles["leader"], department=department_a, team=team_a),
            "employee": User(username="employee_user", password_hash="hash", real_name="员工", role=roles["employee"], department=department_a, team=team_a),
            "other_employee": User(username="other_employee", password_hash="hash", real_name="其他员工", role=roles["employee"], department=department_a, team=team_b),
            "outside_employee": User(username="outside_employee", password_hash="hash", real_name="外部员工", role=roles["employee"], department=department_b),
        }
        database.add_all([department_a, department_b, *roles.values(), *users.values()])
        database.flush()

        documents = {
            "employee": Document(filename="employee.docx", original_name="员工文件.docx", uploader=users["employee"], department=department_a, team=team_a, visibility=DocumentVisibility.PRIVATE),
            "leader": Document(filename="leader.docx", original_name="组长文件.docx", uploader=users["leader"], department=department_a, visibility=DocumentVisibility.DEPARTMENT),
            "manager": Document(filename="manager.docx", original_name="主管文件.docx", uploader=users["manager"], department=department_a, visibility=DocumentVisibility.PRIVATE),
            "outside": Document(filename="outside.docx", original_name="外部文件.docx", uploader=users["outside_employee"], department=department_b, visibility=DocumentVisibility.PRIVATE),
            "company": Document(filename="company.docx", original_name="公司文件.docx", uploader=users["outside_employee"], department=department_b, visibility=DocumentVisibility.COMPANY),
        }
        database.add_all(documents.values())
        database.commit()
        yield users, documents
    engine.dispose()


def test_employee_can_access_own_document(document_permission_context):
    from app.services.document_permission import can_view_document

    users, documents = document_permission_context
    assert can_view_document(users["employee"], documents["employee"])


def test_employee_cannot_access_other_non_company_document(document_permission_context):
    from app.services.document_permission import can_view_document

    users, documents = document_permission_context
    assert not can_view_document(users["other_employee"], documents["employee"])


def test_leader_can_access_employee_document(document_permission_context):
    from app.services.document_permission import can_delete_document, can_edit_document, can_view_document

    users, documents = document_permission_context
    assert can_view_document(users["leader"], documents["employee"])
    assert can_edit_document(users["leader"], documents["employee"])
    assert can_delete_document(users["leader"], documents["employee"])


def test_leader_cannot_access_manager_document(document_permission_context):
    from app.services.document_permission import can_delete_document, can_edit_document, can_view_document

    users, documents = document_permission_context
    assert not can_view_document(users["leader"], documents["manager"])
    assert not can_edit_document(users["leader"], documents["manager"])
    assert not can_delete_document(users["leader"], documents["manager"])


def test_manager_can_manage_department_document(document_permission_context):
    from app.services.document_permission import can_delete_document, can_edit_document, can_view_document

    users, documents = document_permission_context
    assert can_view_document(users["manager"], documents["employee"])
    assert can_edit_document(users["manager"], documents["employee"])
    assert can_delete_document(users["manager"], documents["employee"])


def test_admin_can_access_all_documents(document_permission_context):
    from app.services.document_permission import can_delete_document, can_edit_document, can_view_document

    users, documents = document_permission_context
    assert all(can_view_document(users["admin"], document) for document in documents.values())
    assert all(can_edit_document(users["admin"], document) for document in documents.values())
    assert all(can_delete_document(users["admin"], document) for document in documents.values())


def test_company_visibility_expands_view_but_not_employee_mutation(document_permission_context):
    from app.services.document_permission import can_delete_document, can_edit_document, can_view_document

    users, documents = document_permission_context
    assert can_view_document(users["employee"], documents["company"])
    assert not can_edit_document(users["employee"], documents["company"])
    assert not can_delete_document(users["employee"], documents["company"])
