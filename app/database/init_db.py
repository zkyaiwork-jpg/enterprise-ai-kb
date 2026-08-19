from app.core.paths import APP_DATA_DIR
from app.database.database import Base, engine


def init_db() -> None:
    """Development/test compatibility bootstrap; not a migration mechanism.

    Production and packaged deployments must run ``alembic upgrade head``.
    Keeping create_all temporarily avoids breaking existing test fixtures and
    desktop installs while migration rollout is completed. It only creates
    missing objects and cannot evolve existing columns or constraints.
    """
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Import the model package so every mapped class is registered before
    # metadata creation.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
