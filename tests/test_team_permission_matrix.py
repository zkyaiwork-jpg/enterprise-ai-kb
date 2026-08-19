from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_same_department_two_team_permission_matrix():
    from app.database.database import Base
    from app.models import Department, Document, DocumentVisibility, Role, Team, User
    from app.services.document_permission import can_delete_document, can_edit_document, can_view_document

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database:
        technology = Department(name="Technology")
        operations = Department(name="Operations")
        team_a = Team(name="Team A", department=technology)
        team_b = Team(name="Team B", department=technology)
        team_c = Team(name="Team C", department=operations)
        roles = {name: Role(name=name) for name in ("admin", "manager", "leader", "employee")}
        users = {
            "leader_a": User(username="leader_a_matrix", password_hash="x", real_name="Leader A", role=roles["leader"], department=technology, team=team_a),
            "employee_a": User(username="employee_a_matrix", password_hash="x", real_name="Employee A", role=roles["employee"], department=technology, team=team_a),
            "employee_b": User(username="employee_b_matrix", password_hash="x", real_name="Employee B", role=roles["employee"], department=technology, team=team_b),
            "employee_c": User(username="employee_c_matrix", password_hash="x", real_name="Employee C", role=roles["employee"], department=operations, team=team_c),
            "manager": User(username="manager_matrix", password_hash="x", real_name="Manager", role=roles["manager"], department=technology),
            "admin": User(username="admin_matrix", password_hash="x", real_name="Admin", role=roles["admin"]),
        }
        database.add_all([technology, operations, *roles.values(), *users.values()])
        database.flush()
        documents = {
            "a_private": Document(filename="a-private.txt", original_name="a-private.txt", uploader=users["employee_a"], department=technology, team=team_a, visibility=DocumentVisibility.PRIVATE),
            "b_private": Document(filename="b-private.txt", original_name="b-private.txt", uploader=users["employee_b"], department=technology, team=team_b, visibility=DocumentVisibility.PRIVATE),
            "a_team": Document(filename="a-team.txt", original_name="a-team.txt", uploader=users["employee_a"], department=technology, team=team_a, visibility=DocumentVisibility.TEAM),
            "department": Document(filename="department.txt", original_name="department.txt", uploader=users["employee_b"], department=technology, team=team_b, visibility=DocumentVisibility.DEPARTMENT),
            "company": Document(filename="company.txt", original_name="company.txt", uploader=users["employee_c"], department=operations, team=team_c, visibility=DocumentVisibility.COMPANY),
            "legacy_team": Document(filename="legacy-team.txt", original_name="legacy-team.txt", uploader=users["employee_b"], department=technology, team=None, visibility=DocumentVisibility.TEAM),
        }
        database.add_all(documents.values())
        database.commit()

        assert can_view_document(users["leader_a"], documents["a_private"])
        assert not can_view_document(users["leader_a"], documents["b_private"])
        assert can_edit_document(users["leader_a"], documents["a_private"])
        assert can_delete_document(users["leader_a"], documents["a_private"])
        assert not can_edit_document(users["leader_a"], documents["b_private"])
        assert can_view_document(users["employee_a"], documents["a_team"])
        assert not can_view_document(users["employee_b"], documents["a_team"])
        assert can_view_document(users["employee_a"], documents["department"])
        assert not can_view_document(users["employee_c"], documents["department"])
        assert can_view_document(users["employee_a"], documents["company"])
        assert not can_view_document(users["leader_a"], documents["legacy_team"])
        assert can_view_document(users["manager"], documents["legacy_team"])
        assert can_view_document(users["admin"], documents["legacy_team"])
    engine.dispose()
