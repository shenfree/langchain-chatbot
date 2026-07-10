"""Streamlit 前端 HTTP 客户端。

本模块只通过 requests 调用 FastAPI 后端，不直接访问后端内部业务模块。
"""

from typing import Any

import requests


class ApiClient:
    """FastAPI 后端 API 封装。"""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_users(self) -> list[dict[str, Any]]:
        return self._request("GET", "/users")

    def create_user(self, username: str) -> dict[str, Any]:
        return self._request("POST", "/users", json={"username": username})

    def get_current_user(self) -> dict[str, Any]:
        return self._request("GET", "/users/current")

    def switch_user(self, username: str | None = None, user_id: int | None = None) -> dict[str, Any]:
        return self._request("POST", "/users/current", json={"username": username, "user_id": user_id})

    def delete_user(self, user_id: int) -> dict[str, Any]:
        return self._request("DELETE", f"/users/{user_id}")

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._request("GET", "/sessions")

    def create_session(
        self,
        title: str = "新会话",
        model_name: str | None = None,
        preset_id: int | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/sessions",
            json={"title": title, "model_name": model_name, "preset_id": preset_id},
        )

    def get_session(self, session_id: int) -> dict[str, Any]:
        return self._request("GET", f"/sessions/{session_id}")

    def rename_session(self, session_id: int, title: str) -> dict[str, Any]:
        return self._request("PATCH", f"/sessions/{session_id}", json={"title": title})

    def delete_session(self, session_id: int) -> dict[str, Any]:
        return self._request("DELETE", f"/sessions/{session_id}")

    def list_presets(self) -> list[dict[str, Any]]:
        return self._request("GET", "/presets").get("presets", [])

    def list_models(self) -> dict[str, Any]:
        return self._request("GET", "/models")

    def chat(
        self,
        session_id: int,
        message: str,
        preset_id: int | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/chat",
            json={
                "session_id": session_id,
                "message": message,
                "preset_id": preset_id,
                "model_name": model_name,
            },
        )

    def search(self, keyword: str) -> list[dict[str, Any]]:
        return self._request("GET", "/search", params={"keyword": keyword}).get("results", [])

    def export_session(self, session_id: int) -> dict[str, Any]:
        return self._request("POST", f"/export/{session_id}")

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """发送 HTTP 请求并处理错误。"""
        response = requests.request(method, f"{self.base_url}{path}", timeout=120, **kwargs)
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except ValueError:
                pass
            raise RuntimeError(str(detail))
        if not response.content:
            return {}
        return response.json()
