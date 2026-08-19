"""HTTP client for the FastAPI knowledge-base backend."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import requests


DEFAULT_API_URL = "http://127.0.0.1:8000"


class APIClientError(RuntimeError):
    """A user-facing backend communication error."""


class BackendUnavailableError(APIClientError):
    """Raised when the FastAPI service cannot be reached."""


class KnowledgeBaseAPI:
    """Small, typed boundary around the backend API."""

    def __init__(self, base_url: str | None = None, timeout: int = 90) -> None:
        self.base_url = (base_url or os.getenv("KB_API_BASE_URL", DEFAULT_API_URL)).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, f"{self.base_url}{path}", **kwargs)
        except requests.ConnectionError as exc:
            raise BackendUnavailableError("后端服务未连接") from exc
        except requests.Timeout as exc:
            raise APIClientError("请求超时，请稍后重试") from exc
        except requests.RequestException as exc:
            raise APIClientError(f"网络请求失败：{exc}") from exc

        if not response.ok:
            detail = self._extract_error(response)
            raise APIClientError(f"接口请求失败（HTTP {response.status_code}）：{detail}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise APIClientError("后端返回了无法解析的数据") from exc

        if not isinstance(payload, dict):
            raise APIClientError("后端返回的数据格式不符合预期")
        return payload

    @staticmethod
    def _extract_error(response: requests.Response) -> str:
        try:
            payload = response.json()
            detail = payload.get("detail") if isinstance(payload, dict) else None
            if isinstance(detail, list):
                return "；".join(str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail)
            if detail:
                return str(detail)
        except ValueError:
            pass
        return response.text.strip() or "未知错误"

    def check_health(self) -> bool:
        try:
            self._request("GET", "/", timeout=3)
            return True
        except APIClientError:
            return False

    def list_documents(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/documents", timeout=15)
        documents = payload.get("documents", [])
        return documents if isinstance(documents, list) else []

    def upload_document(self, uploaded_file: Any) -> dict[str, Any]:
        uploaded_file.seek(0)
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        return self._request("POST", "/upload", files=files, timeout=180)

    def delete_document(self, filename: str) -> dict[str, Any]:
        safe_filename = quote(filename, safe="")
        return self._request("DELETE", f"/documents/{safe_filename}", timeout=60)

    def search(self, query: str) -> list[dict[str, Any]]:
        payload = self._request("GET", "/search", params={"query": query}, timeout=90)
        results = payload.get("results", [])
        return results if isinstance(results, list) else []

    def chat(self, question: str) -> dict[str, Any]:
        return self._request("POST", "/chat", json={"question": question}, timeout=180)
