"""Prepare multi-role acceptance accounts through the protected HTTP APIs.

Run the FastAPI service first, then execute this script interactively. Passwords
and JWTs are held in process memory only and are never printed or persisted.
"""

from __future__ import annotations

import argparse
from getpass import getpass
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ACCOUNTS = (
    ("tech_manager", "技术部经理", "manager", "技术部"),
    ("tech_leader", "技术部组长", "leader", "技术部"),
    ("tech_employee_a", "技术部员工A", "employee", "技术部"),
    ("tech_employee_b", "技术部员工B", "employee", "技术部"),
    ("ops_manager", "运营部经理", "manager", "运营部"),
    ("ops_employee", "运营部员工", "employee", "运营部"),
)


class ApiFailure(RuntimeError):
    pass


def request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Any:
    headers = {"Accept": "application/json"}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            response = json.loads(exc.read().decode("utf-8"))
            detail = response.get("detail", "请求失败")
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = "请求失败"
        raise ApiFailure(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise ApiFailure("无法连接后端，请先启动FastAPI服务") from exc


def prompt_password(username: str) -> str:
    while True:
        password = getpass(f"为 {username} 输入初始密码（至少8位，输入隐藏）：")
        confirmation = getpass("确认密码：")
        if password != confirmation:
            print("两次密码不一致，请重新输入。")
            continue
        if len(password) < 8 or len(password.encode("utf-8")) > 72:
            print("密码必须至少8个字符且不超过72字节。")
            continue
        return password


def main() -> int:
    parser = argparse.ArgumentParser(description="通过正式业务API准备多角色验收账号")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-username")
    arguments = parser.parse_args()

    admin_username = arguments.admin_username or input("管理员用户名：").strip()
    admin_password = getpass("管理员密码（输入隐藏）：")
    try:
        login = request_json(
            arguments.api_base,
            "POST",
            "/auth/login",
            payload={"username": admin_username, "password": admin_password},
        )
        admin_password = ""
        token = login["access_token"]

        roles_payload = request_json(arguments.api_base, "GET", "/roles", token=token)
        role_ids = {item["name"]: item["id"] for item in roles_payload["items"]}

        departments_payload = request_json(arguments.api_base, "GET", "/departments", token=token)
        department_ids = {item["name"]: item["id"] for item in departments_payload["items"]}
        for department_name in ("技术部", "运营部"):
            if department_name not in department_ids:
                created = request_json(
                    arguments.api_base,
                    "POST",
                    "/departments",
                    token=token,
                    payload={"name": department_name, "description": "多角色权限验收部门"},
                )
                department_ids[department_name] = created["id"]
                print(f"已创建部门：{department_name}")
            else:
                print(f"部门已存在：{department_name}")

        users_payload = request_json(
            arguments.api_base, "GET", "/users?page=1&page_size=100", token=token
        )
        existing_usernames = {item["username"] for item in users_payload["items"]}
        for username, real_name, role_name, department_name in ACCOUNTS:
            if username in existing_usernames:
                print(f"账号已存在，跳过：{username}")
                continue
            password = prompt_password(username)
            request_json(
                arguments.api_base,
                "POST",
                "/users",
                token=token,
                payload={
                    "username": username,
                    "password": password,
                    "real_name": real_name,
                    "role_id": role_ids[role_name],
                    "department_id": department_ids[department_name],
                },
            )
            password = ""
            print(f"已创建账号：{username}（{department_name}/{role_name}）")

        token = ""
        print("验收账号准备完成。脚本未打印或保存任何密码、JWT。")
        return 0
    except (ApiFailure, KeyError) as exc:
        admin_password = ""
        print(f"准备失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
