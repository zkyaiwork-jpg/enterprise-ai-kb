from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.permission import Permission
from app.models.role import Role


DEFAULT_PERMISSIONS = {
    "file_publish_team": ("小组发布", "将文档发布到小组可见范围"),
    "file_publish_department": ("部门发布", "将文档发布到部门可见范围"),
    "file_publish_company": ("全公司发布", "将文档发布到全公司可见范围"),
    "user_manage": ("用户管理", "创建、修改和管理企业用户"),
    "file_upload": ("文件上传", "上传知识库文档"),
    "file_view": ("文件查看", "查看知识库文档"),
    "file_edit": ("文件编辑", "编辑知识库文档信息"),
    "file_delete": ("文件删除", "删除知识库文档"),
    "model_manage": ("模型管理", "管理AI模型配置"),
    "audit_view": ("审计日志查看", "查看企业安全审计日志"),
}

DEFAULT_ROLES = {
    "admin": {
        "description": "系统管理员",
        "permissions": set(DEFAULT_PERMISSIONS),
    },
    "manager": {
        "description": "企业管理员",
        "permissions": {
            "user_manage", "file_upload", "file_view", "file_edit", "file_delete",
            "file_publish_team", "file_publish_department", "file_publish_company",
        },
    },
    "leader": {
        "description": "团队负责人",
        "permissions": {"file_upload", "file_view", "file_edit", "file_delete", "file_publish_team"},
    },
    "employee": {
        "description": "普通员工",
        "permissions": {"file_upload", "file_view"},
    },
}


def seed_default_permissions(database: Session) -> None:
    """Idempotently create default RBAC roles, permissions and associations."""
    permissions_by_code = {
        permission.code: permission
        for permission in database.scalars(select(Permission)).all()
    }
    for code, (name, description) in DEFAULT_PERMISSIONS.items():
        permission = permissions_by_code.get(code)
        if permission is None:
            permission = Permission(code=code, name=name, description=description)
            database.add(permission)
            permissions_by_code[code] = permission

    roles_by_name = {
        role.name: role
        for role in database.scalars(select(Role)).all()
    }
    for role_name, role_config in DEFAULT_ROLES.items():
        role = roles_by_name.get(role_name)
        if role is None:
            role = Role(name=role_name, description=str(role_config["description"]))
            database.add(role)
            roles_by_name[role_name] = role

        assigned_codes = {permission.code for permission in role.permissions}
        for code in role_config["permissions"]:
            if code not in assigned_codes:
                role.permissions.append(permissions_by_code[code])

    database.commit()


def main() -> None:
    with SessionLocal() as database:
        seed_default_permissions(database)


if __name__ == "__main__":
    main()
