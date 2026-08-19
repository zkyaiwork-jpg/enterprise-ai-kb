"""Add server-controlled JWT token version to users."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_0002"
down_revision: Union[str, None] = "20260812_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default=sa.text("1"))
        )
    # Keep the value as an application default after existing rows are backfilled.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("token_version", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")
