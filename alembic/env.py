from logging.config import fileConfig

from alembic import context

from app.database.database import Base, DATABASE_URL
from app import models  # noqa: F401  Registers every mapped model and association table.


config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    # SQLite reflects SQLAlchemy Enum checks as standalone constraints while
    # the model represents them as type-bound constraints. Ignore only these
    # two known Enum checks to prevent false-positive autogenerate removals.
    if type_ == "check_constraint" and name in {"document_visibility", "chat_message_role"}:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Reuse the application's Engine so APP_DATA_DIR and all future connection
    # options have one source of truth.
    from app.database.database import engine

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
