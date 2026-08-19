"""Add teams and team ownership snapshots."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0005"
down_revision: Union[str, None] = "20260812_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id", "name", name="uq_teams_department_name"),
    )
    op.create_index(op.f("ix_teams_department_id"), "teams", ["department_id"], unique=False)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_team_id"), ["team_id"], unique=False)
        batch_op.create_foreign_key("fk_users_team_id_teams", "teams", ["team_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_documents_team_id"), ["team_id"], unique=False)
        batch_op.create_foreign_key("fk_documents_team_id_teams", "teams", ["team_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("fk_documents_team_id_teams", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_documents_team_id"))
        batch_op.drop_column("team_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_team_id_teams", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_users_team_id"))
        batch_op.drop_column("team_id")

    op.drop_index(op.f("ix_teams_department_id"), table_name="teams")
    op.drop_table("teams")
