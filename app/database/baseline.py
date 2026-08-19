from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database.database import Base
from app import models  # noqa: F401


BASELINE_REVISION = "20260812_0001"


def validate_baseline_schema(engine: Engine) -> tuple[bool, list[str]]:
    """Check table/column compatibility before stamping an existing database."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names()) - {"alembic_version"}
    expected_tables = set(Base.metadata.tables)
    issues = []
    missing_tables = expected_tables - existing_tables
    if missing_tables:
        issues.append(f"missing tables: {', '.join(sorted(missing_tables))}")
    for table_name in sorted(expected_tables & existing_tables):
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        expected_columns = set(Base.metadata.tables[table_name].columns.keys())
        missing_columns = expected_columns - existing_columns
        if missing_columns:
            issues.append(f"{table_name} missing columns: {', '.join(sorted(missing_columns))}")
    return not issues, issues
