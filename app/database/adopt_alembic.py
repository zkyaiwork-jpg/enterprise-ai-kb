"""Safely adopt Alembic for a database previously managed by create_all()."""
import argparse
from datetime import datetime
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config

from app.database.baseline import BASELINE_REVISION, validate_baseline_schema
from app.database.database import DATABASE_PATH, engine
from app.database.init_db import init_db


def _backup_sqlite(source: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = source.with_name(f"{source.name}.pre-alembic-{timestamp}.bak")
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as backup_connection:
        source_connection.backup(backup_connection)
    return destination


def adopt_existing_database(*, apply: bool = False) -> dict:
    before_valid, before_issues = validate_baseline_schema(engine)
    if not apply:
        return {"valid": before_valid, "issues": before_issues, "changed": False}

    backup_path = _backup_sqlite(DATABASE_PATH)
    try:
        # Compatibility-only create_all fills tables introduced after the old
        # database was created. It does not drop or rewrite existing data.
        init_db()
        valid, issues = validate_baseline_schema(engine)
        if not valid:
            raise RuntimeError("schema validation failed: " + "; ".join(issues))
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.stamp(config, BASELINE_REVISION)
    except Exception:
        # The backup is intentionally retained for explicit operator recovery;
        # never replace a live database automatically after a partial failure.
        raise
    return {
        "valid": True,
        "issues": [],
        "changed": True,
        "backup": str(backup_path),
        "revision": BASELINE_REVISION,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="backup, complete, validate and stamp the database")
    arguments = parser.parse_args()
    result = adopt_existing_database(apply=arguments.apply)
    print(result)


if __name__ == "__main__":
    main()
