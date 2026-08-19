"""Add document visibility publishing permissions and default grants."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260812_0004"
down_revision: Union[str, None] = "20260812_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = {
    "file_publish_team": ("小组发布", "将文档发布到小组可见范围"),
    "file_publish_department": ("部门发布", "将文档发布到部门可见范围"),
    "file_publish_company": ("全公司发布", "将文档发布到全公司可见范围"),
}
ROLE_GRANTS = {
    "leader": {"file_publish_team"},
    "manager": set(PERMISSIONS),
    "admin": set(PERMISSIONS),
}


def upgrade() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()
    permissions = sa.Table("permissions", metadata, autoload_with=connection)
    roles = sa.Table("roles", metadata, autoload_with=connection)
    links = sa.Table("role_permissions", metadata, autoload_with=connection)
    permission_ids = {}
    for code, (name, description) in PERMISSIONS.items():
        permission_id = connection.scalar(sa.select(permissions.c.id).where(permissions.c.code == code))
        if permission_id is None:
            connection.execute(permissions.insert().values(code=code, name=name, description=description))
            permission_id = connection.scalar(sa.select(permissions.c.id).where(permissions.c.code == code))
        permission_ids[code] = permission_id
    for role_name, codes in ROLE_GRANTS.items():
        role_id = connection.scalar(sa.select(roles.c.id).where(roles.c.name == role_name))
        if role_id is None:
            continue
        for code in codes:
            exists = connection.scalar(sa.select(links.c.role_id).where(links.c.role_id == role_id, links.c.permission_id == permission_ids[code]))
            if exists is None:
                connection.execute(links.insert().values(role_id=role_id, permission_id=permission_ids[code]))


def downgrade() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()
    permissions = sa.Table("permissions", metadata, autoload_with=connection)
    roles = sa.Table("roles", metadata, autoload_with=connection)
    links = sa.Table("role_permissions", metadata, autoload_with=connection)
    for role_name, codes in ROLE_GRANTS.items():
        role_id = connection.scalar(sa.select(roles.c.id).where(roles.c.name == role_name))
        if role_id is None:
            continue
        permission_ids = connection.scalars(sa.select(permissions.c.id).where(permissions.c.code.in_(codes))).all()
        if permission_ids:
            connection.execute(links.delete().where(links.c.role_id == role_id, links.c.permission_id.in_(permission_ids)))
    # Preserve permission rows because custom roles may still reference them.
