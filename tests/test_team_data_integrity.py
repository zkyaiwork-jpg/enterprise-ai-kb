import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _sqlite_engine():
    from app.database.database import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine


def test_sqlite_foreign_keys_are_enabled_on_real_connection():
    engine = _sqlite_engine()
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    engine.dispose()


def test_team_foreign_key_delete_actions_and_invalid_reference():
    from app.models import Department, Document, Team, User

    engine = _sqlite_engine()
    with Session(engine) as database:
        department = Department(name="Integrity Department")
        team = Team(name="Integrity Team", department=department)
        user = User(username="integrity_user", password_hash="x", real_name="Integrity User", department=department, team=team)
        document = Document(filename="integrity.txt", original_name="integrity.txt", uploader=user, department=department, team=team)
        database.add_all([department, team, user, document])
        database.commit()
        department_id, team_id, user_id, document_id = department.id, team.id, user.id, document.id

    with Session(engine) as database:
        database.delete(database.get(Department, department_id))
        with pytest.raises(IntegrityError):
            database.commit()
        database.rollback()

    with Session(engine) as database:
        database.delete(database.get(Team, team_id))
        database.commit()

    with Session(engine) as database:
        assert database.get(User, user_id).team_id is None
        assert database.get(Document, document_id).team_id is None
        database.add(User(username="invalid_team_user", password_hash="x", real_name="Invalid", team_id=999999))
        with pytest.raises(IntegrityError):
            database.commit()
        database.rollback()
    engine.dispose()
