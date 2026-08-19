from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session


def test_document_table_columns_foreign_keys_and_visibility_enum(tmp_path):
    from app.database.database import Base
    from app.models import DocumentVisibility

    engine = create_engine(f"sqlite:///{(tmp_path / 'documents.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    assert "documents" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("documents")} == {
        "id", "filename", "original_name", "uploader_id", "department_id",
        "team_id", "visibility", "created_time", "updated_time",
    }
    foreign_keys = {
        foreign_key["constrained_columns"][0]: foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys("documents")
    }
    assert foreign_keys == {"uploader_id": "users", "department_id": "departments", "team_id": "teams"}
    assert {visibility.value for visibility in DocumentVisibility} == {
        "private", "team", "department", "company",
    }
    check_constraints = inspector.get_check_constraints("documents")
    assert any(
        all(value in constraint["sqltext"] for value in ("private", "team", "department", "company"))
        for constraint in check_constraints
    )

    engine.dispose()


def test_document_orm_relationships_and_default_visibility(tmp_path):
    from app.database.database import Base
    from app.models import Department, Document, DocumentVisibility, User

    engine = create_engine(f"sqlite:///{(tmp_path / 'relationships.db').as_posix()}")
    Base.metadata.create_all(bind=engine)

    with Session(engine, expire_on_commit=False) as database:
        department = Department(name="研发部")
        uploader = User(
            username="document_owner",
            password_hash="test-hash",
            real_name="文档负责人",
            department=department,
            status="active",
        )
        document = Document(
            filename="stored-document.docx",
            original_name="企业制度.docx",
            uploader=uploader,
            department=department,
        )
        database.add(document)
        database.commit()
        database.refresh(document)

        assert document.visibility is DocumentVisibility.PRIVATE
        assert document.uploader is uploader
        assert document in uploader.documents
        assert document.department is department
        assert document in department.documents
        assert document.created_time is not None
        assert document.updated_time is not None

    assert Document.uploader.property.back_populates == "documents"
    assert User.documents.property.back_populates == "uploader"
    assert Department.documents.property.back_populates == "department"
    engine.dispose()
