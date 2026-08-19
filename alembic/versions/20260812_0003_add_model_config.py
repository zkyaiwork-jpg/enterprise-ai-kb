"""Add encrypted enterprise model configuration."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260812_0003"
down_revision: Union[str, None] = "20260812_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_configs_provider"), "model_configs", ["provider"], unique=False)
    op.create_index(op.f("ix_model_configs_is_active"), "model_configs", ["is_active"], unique=False)
    op.create_index("ix_model_configs_one_active", "model_configs", ["is_active"], unique=True, sqlite_where=sa.text("is_active = 1"))


def downgrade() -> None:
    op.drop_index("ix_model_configs_one_active", table_name="model_configs")
    op.drop_index(op.f("ix_model_configs_is_active"), table_name="model_configs")
    op.drop_index(op.f("ix_model_configs_provider"), table_name="model_configs")
    op.drop_table("model_configs")
