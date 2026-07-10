"""JSON 文件存储后端实现。

FileBackend 是 Step 12 新增的轻量存储实现，主要用于演示项目可以在
SQLite / MySQL / File 三种后端之间切换。

注意：文件存储没有数据库外键能力，因此用户、会话、预设之间的级联清理
需要在本类中手动维护。
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models.schemas import Message, Preset, Session, User
from src.storage.base import StorageBackend


class FileBackend(StorageBackend):
    """基于 JSON 文件的异步存储后端。"""

    FILES = {
        "users": "users.json",
        "sessions": "sessions.json",
        "messages": "messages.json",
        "presets": "presets.json",
    }

    def __init__(self, base_dir: str | Path) -> None:
        """保存文件存储根目录。"""
        self.base_dir = Path(base_dir)
        self._lock = asyncio.Lock()

    async def init_storage(self) -> None:
        """初始化目录和空 JSON 文件。"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for filename in self.FILES.values():
            path = self.base_dir / filename
            if not path.exists():
                self._write_json(path, [])

    async def close(self) -> None:
        """关闭存储资源。文件后端没有长连接，因此无需额外处理。"""

    async def create_user(self, username: str) -> User:
        """创建用户并返回用户对象。"""
        async with self._lock:
            users = self._load_table("users")
            if any(user["username"] == username for user in users):
                raise ValueError(f"用户名 {username} 已存在。")

            now = self._now()
            user = {
                "id": self._next_id(users),
                "username": username,
                "default_model": None,
                "default_preset_id": None,
                "created_at": now,
                "updated_at": now,
            }
            users.append(user)
            self._save_table("users", users)
            return self._row_to_user(user)

    async def get_user_by_username(self, username: str) -> User | None:
        """根据用户名查询用户。"""
        async with self._lock:
            for user in self._load_table("users"):
                if user["username"] == username:
                    return self._row_to_user(user)
            return None

    async def list_users(self) -> list[User]:
        """查询所有用户。"""
        async with self._lock:
            users = sorted(self._load_table("users"), key=lambda item: item["id"])
            return [self._row_to_user(user) for user in users]

    async def delete_user(self, user_id: int) -> None:
        """删除用户，并手动级联删除该用户的会话、消息和个人预设。"""
        async with self._lock:
            users = [user for user in self._load_table("users") if user["id"] != user_id]
            sessions = self._load_table("sessions")
            messages = self._load_table("messages")
            presets = self._load_table("presets")

            deleted_session_ids = {
                session["id"] for session in sessions if session["user_id"] == user_id
            }
            sessions = [session for session in sessions if session["user_id"] != user_id]
            messages = [
                message for message in messages if message["session_id"] not in deleted_session_ids
            ]
            presets = [
                preset
                for preset in presets
                if preset.get("is_builtin") or preset.get("user_id") != user_id
            ]

            self._save_table("users", users)
            self._save_table("sessions", sessions)
            self._save_table("messages", messages)
            self._save_table("presets", presets)

    async def create_session(
        self,
        user_id: int,
        title: str,
        model_name: str,
        preset_id: int | None = None,
    ) -> Session:
        """创建会话并返回会话对象。"""
        async with self._lock:
            sessions = self._load_table("sessions")
            now = self._now()
            session = {
                "id": self._next_id(sessions),
                "user_id": user_id,
                "title": title,
                "model_name": model_name,
                "preset_id": preset_id,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "created_at": now,
                "updated_at": now,
            }
            sessions.append(session)
            self._save_table("sessions", sessions)
            return self._row_to_session(session)

    async def list_sessions(self, user_id: int) -> list[Session]:
        """查询指定用户的会话，按更新时间倒序排列。"""
        async with self._lock:
            sessions = [
                session for session in self._load_table("sessions") if session["user_id"] == user_id
            ]
            sessions.sort(key=lambda item: (item["updated_at"], item["id"]), reverse=True)
            return [self._row_to_session(session) for session in sessions]

    async def get_session(self, session_id: int) -> Session | None:
        """根据会话 ID 查询会话。"""
        async with self._lock:
            session = self._find_by_id("sessions", session_id)
            return self._row_to_session(session) if session else None

    async def update_session_title(self, session_id: int, title: str) -> Session | None:
        """更新会话标题。"""
        async with self._lock:
            sessions = self._load_table("sessions")
            for session in sessions:
                if session["id"] == session_id:
                    session["title"] = title
                    session["updated_at"] = self._now()
                    self._save_table("sessions", sessions)
                    return self._row_to_session(session)
            return None

    async def delete_session(self, session_id: int) -> None:
        """删除会话，并手动级联删除该会话下的消息。"""
        async with self._lock:
            sessions = [
                session for session in self._load_table("sessions") if session["id"] != session_id
            ]
            messages = [
                message
                for message in self._load_table("messages")
                if message["session_id"] != session_id
            ]
            self._save_table("sessions", sessions)
            self._save_table("messages", messages)

    async def update_session_model(self, session_id: int, model_name: str) -> Session | None:
        """更新会话使用的模型名。"""
        async with self._lock:
            sessions = self._load_table("sessions")
            for session in sessions:
                if session["id"] == session_id:
                    session["model_name"] = model_name
                    session["updated_at"] = self._now()
                    self._save_table("sessions", sessions)
                    return self._row_to_session(session)
            return None

    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Message:
        """向会话追加消息，并同步更新会话时间和 token 统计。"""
        async with self._lock:
            messages = self._load_table("messages")
            sessions = self._load_table("sessions")
            now = self._now()
            message = {
                "id": self._next_id(messages),
                "session_id": session_id,
                "role": role,
                "content": content,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "created_at": now,
            }
            messages.append(message)

            for session in sessions:
                if session["id"] == session_id:
                    session["updated_at"] = now
                    session["total_prompt_tokens"] += prompt_tokens
                    session["total_completion_tokens"] += completion_tokens
                    break

            self._save_table("messages", messages)
            self._save_table("sessions", sessions)
            return self._row_to_message(message)

    async def list_messages(self, session_id: int) -> list[Message]:
        """查询指定会话的全部消息。"""
        async with self._lock:
            messages = [
                message
                for message in self._load_table("messages")
                if message["session_id"] == session_id
            ]
            messages.sort(key=lambda item: item["id"])
            return [self._row_to_message(message) for message in messages]

    async def search_messages(self, user_id: int, keyword: str) -> list[dict]:
        """在指定用户的所有历史消息中搜索关键词。"""
        cleaned_keyword = keyword.strip()
        if not cleaned_keyword:
            return []

        async with self._lock:
            sessions = self._load_table("sessions")
            session_map = {
                session["id"]: session for session in sessions if session["user_id"] == user_id
            }
            results = []
            for message in self._load_table("messages"):
                session = session_map.get(message["session_id"])
                if session is None:
                    continue
                if cleaned_keyword not in message["content"]:
                    continue
                results.append(
                    {
                        "message_id": message["id"],
                        "session_id": message["session_id"],
                        "session_title": session["title"],
                        "role": message["role"],
                        "content": message["content"],
                        "created_at": message["created_at"],
                    }
                )
            results.sort(key=lambda item: item["created_at"], reverse=True)
            return results

    async def create_preset(
        self,
        user_id: int | None,
        name: str,
        description: str,
        system_prompt: str,
        is_builtin: bool = False,
    ) -> Preset:
        """创建预设 Prompt。"""
        async with self._lock:
            presets = self._load_table("presets")
            now = self._now()
            preset = {
                "id": self._next_id(presets),
                "user_id": user_id,
                "name": name,
                "description": description,
                "system_prompt": system_prompt,
                "is_builtin": is_builtin,
                "created_at": now,
                "updated_at": now,
            }
            presets.append(preset)
            self._save_table("presets", presets)
            return self._row_to_preset(preset)

    async def get_preset(self, preset_id: int) -> Preset | None:
        """根据 ID 查询预设。"""
        async with self._lock:
            preset = self._find_by_id("presets", preset_id)
            return self._row_to_preset(preset) if preset else None

    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """查询系统内置预设，或系统内置预设加指定用户的个人预设。"""
        async with self._lock:
            if user_id is None:
                presets = [preset for preset in self._load_table("presets") if preset["is_builtin"]]
            else:
                presets = [
                    preset
                    for preset in self._load_table("presets")
                    if preset["is_builtin"] or preset.get("user_id") == user_id
                ]
            presets.sort(key=lambda item: (not item["is_builtin"], item["id"]))
            return [self._row_to_preset(preset) for preset in presets]

    async def update_preset(
        self,
        preset_id: int,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Preset:
        """更新非内置预设。"""
        async with self._lock:
            presets = self._load_table("presets")
            for preset in presets:
                if preset["id"] != preset_id:
                    continue
                if preset["is_builtin"]:
                    raise ValueError("系统内置预设不允许修改。")
                preset["name"] = name
                preset["description"] = description
                preset["system_prompt"] = system_prompt
                preset["updated_at"] = self._now()
                self._save_table("presets", presets)
                return self._row_to_preset(preset)
            raise ValueError(f"预设 ID {preset_id} 不存在。")

    async def delete_preset(self, preset_id: int) -> None:
        """删除非内置预设，并把引用该预设的会话 preset_id 置空。"""
        async with self._lock:
            presets = self._load_table("presets")
            preset = next((item for item in presets if item["id"] == preset_id), None)
            if preset is None:
                raise ValueError(f"预设 ID {preset_id} 不存在。")
            if preset["is_builtin"]:
                raise ValueError("系统内置预设不允许删除。")

            presets = [item for item in presets if item["id"] != preset_id]
            sessions = self._load_table("sessions")
            now = self._now()
            for session in sessions:
                if session.get("preset_id") == preset_id:
                    session["preset_id"] = None
                    session["updated_at"] = now

            self._save_table("presets", presets)
            self._save_table("sessions", sessions)

    def _load_table(self, table: str) -> list[dict[str, Any]]:
        """读取指定 JSON 文件。"""
        path = self.base_dir / self.FILES[table]
        if not path.exists():
            self._write_json(path, [])
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError(f"文件 {path} 的数据结构不是列表。")
        return data

    def _save_table(self, table: str, rows: list[dict[str, Any]]) -> None:
        """写入指定 JSON 文件。"""
        path = self.base_dir / self.FILES[table]
        self._write_json(path, rows)

    def _write_json(self, path: Path, data: list[dict[str, Any]]) -> None:
        """按项目要求使用 UTF-8、ensure_ascii=False 和 indent=2 写入 JSON。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def _find_by_id(self, table: str, item_id: int) -> dict[str, Any] | None:
        """在指定表中按 ID 查找记录。"""
        for item in self._load_table(table):
            if item["id"] == item_id:
                return item
        return None

    @staticmethod
    def _next_id(rows: list[dict[str, Any]]) -> int:
        """生成下一个自增 ID，避免删除记录后重复使用旧 ID。"""
        if not rows:
            return 1
        return max(int(row["id"]) for row in rows) + 1

    @staticmethod
    def _now() -> str:
        """生成 ISO 格式时间字符串。"""
        return datetime.now().isoformat()

    @staticmethod
    def _row_to_user(row: dict[str, Any]) -> User:
        return User(**dict(row))

    @staticmethod
    def _row_to_session(row: dict[str, Any]) -> Session:
        return Session(**dict(row))

    @staticmethod
    def _row_to_message(row: dict[str, Any]) -> Message:
        return Message(**dict(row))

    @staticmethod
    def _row_to_preset(row: dict[str, Any]) -> Preset:
        data = dict(row)
        data["is_builtin"] = bool(data["is_builtin"])
        return Preset(**data)
