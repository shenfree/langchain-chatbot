"""SQLite 存储后端实现。

本模块只负责数据持久化，不负责 TUI 菜单展示，也不负责 LangChain 调用。
Step 5 在 Step 3 基础上补充了预设 Prompt 的 CRUD 能力。
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from src.models.schemas import Message, Preset, Session, User
from src.storage.base import StorageBackend


class SQLiteBackend(StorageBackend):
    """基于 SQLite 的异步存储后端。"""

    def __init__(self, db_path: str | Path) -> None:
        """初始化 SQLite 后端。"""
        self.db_path = Path(db_path)

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """创建 SQLite 连接，并启用外键约束。"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON")
            yield db

    async def init_storage(self) -> None:
        """初始化数据库目录和所有数据表。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with self._connect() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    default_model TEXT,
                    default_preset_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    is_builtin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    preset_id INTEGER,
                    total_prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    total_completion_tokens INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(preset_id) REFERENCES presets(id) ON DELETE SET NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, key),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            await db.commit()

    async def close(self) -> None:
        """关闭存储资源。当前实现采用短连接，无需额外操作。"""

    async def create_user(self, username: str) -> User:
        """创建用户并返回用户对象。"""
        now = self._now()
        async with self._connect() as db:
            cursor = await db.execute(
                "INSERT INTO users (username, created_at, updated_at) VALUES (?, ?, ?)",
                (username, now, now),
            )
            await db.commit()
            return await self._get_user_by_id(db, cursor.lastrowid)

    async def get_user_by_username(self, username: str) -> User | None:
        """根据用户名查询用户。"""
        async with self._connect() as db:
            cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = await cursor.fetchone()
            return self._row_to_user(row) if row else None

    async def list_users(self) -> list[User]:
        """查询所有用户。"""
        async with self._connect() as db:
            cursor = await db.execute("SELECT * FROM users ORDER BY id ASC")
            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def delete_user(self, user_id: int) -> None:
        """删除指定用户，关联数据依赖外键级联删除。"""
        async with self._connect() as db:
            await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await db.commit()

    async def create_session(
        self,
        user_id: int,
        title: str,
        model_name: str,
        preset_id: int | None = None,
    ) -> Session:
        """创建会话并返回会话对象。"""
        now = self._now()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO sessions (
                    user_id, title, model_name, preset_id,
                    total_prompt_tokens, total_completion_tokens,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 0, 0, ?, ?)
                """,
                (user_id, title, model_name, preset_id, now, now),
            )
            await db.commit()
            return await self._get_session_by_id(db, cursor.lastrowid)

    async def list_sessions(self, user_id: int) -> list[Session]:
        """查询指定用户的所有会话。"""
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_session(row) for row in rows]

    async def get_session(self, session_id: int) -> Session | None:
        """根据会话 ID 查询会话。"""
        async with self._connect() as db:
            cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            return self._row_to_session(row) if row else None

    async def update_session_title(self, session_id: int, title: str) -> Session | None:
        """更新会话标题。"""
        now = self._now()
        async with self._connect() as db:
            await db.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            return self._row_to_session(row) if row else None

    async def delete_session(self, session_id: int) -> None:
        """删除指定会话。"""
        async with self._connect() as db:
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()

    async def update_session_model(self, session_id: int, model_name: str) -> Session | None:
        """更新会话使用的模型名。"""
        now = self._now()
        async with self._connect() as db:
            await db.execute(
                "UPDATE sessions SET model_name = ?, updated_at = ? WHERE id = ?",
                (model_name, now, session_id),
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            return self._row_to_session(row) if row else None

    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Message:
        """向会话中追加一条消息。"""
        now = self._now()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO messages (
                    session_id, role, content,
                    prompt_tokens, completion_tokens, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, prompt_tokens, completion_tokens, now),
            )
            # 每次新增消息时顺手更新会话更新时间和 token 统计，方便 /sessions 展示最新状态。
            await db.execute(
                """
                UPDATE sessions
                SET updated_at = ?,
                    total_prompt_tokens = total_prompt_tokens + ?,
                    total_completion_tokens = total_completion_tokens + ?
                WHERE id = ?
                """,
                (now, prompt_tokens, completion_tokens, session_id),
            )
            await db.commit()
            return await self._get_message_by_id(db, cursor.lastrowid)

    async def list_messages(self, session_id: int) -> list[Message]:
        """查询指定会话的全部消息。"""
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_message(row) for row in rows]

    async def search_messages(self, user_id: int, keyword: str) -> list[dict]:
        """在指定用户的所有历史消息中搜索关键词。

        通过 JOIN sessions 并限制 sessions.user_id，确保不会搜索到其他用户的数据。
        """
        cleaned_keyword = keyword.strip()
        if not cleaned_keyword:
            return []

        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT
                    messages.id AS message_id,
                    messages.session_id,
                    sessions.title AS session_title,
                    messages.role,
                    messages.content,
                    messages.created_at
                FROM messages
                JOIN sessions ON messages.session_id = sessions.id
                WHERE sessions.user_id = ?
                  AND messages.content LIKE ?
                ORDER BY messages.created_at DESC
                """,
                (user_id, f"%{cleaned_keyword}%"),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_preset(
        self,
        user_id: int | None,
        name: str,
        description: str,
        system_prompt: str,
        is_builtin: bool = False,
    ) -> Preset:
        """创建预设 Prompt。"""
        now = self._now()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO presets (
                    user_id, name, description, system_prompt,
                    is_builtin, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, name, description, system_prompt, int(is_builtin), now, now),
            )
            await db.commit()
            return await self._get_preset_by_id(db, cursor.lastrowid)

    async def get_preset(self, preset_id: int) -> Preset | None:
        """根据 ID 查询预设。"""
        async with self._connect() as db:
            cursor = await db.execute("SELECT * FROM presets WHERE id = ?", (preset_id,))
            row = await cursor.fetchone()
            return self._row_to_preset(row) if row else None

    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """查询预设列表。

        user_id 为空时只返回系统内置预设；传入用户 ID 时返回系统内置预设和该用户预设。
        """
        async with self._connect() as db:
            if user_id is None:
                cursor = await db.execute(
                    "SELECT * FROM presets WHERE is_builtin = 1 ORDER BY id ASC"
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM presets
                    WHERE is_builtin = 1 OR user_id = ?
                    ORDER BY is_builtin DESC, id ASC
                    """,
                    (user_id,),
                )
            rows = await cursor.fetchall()
            return [self._row_to_preset(row) for row in rows]

    async def update_preset(
        self,
        preset_id: int,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Preset:
        """更新非内置预设。"""
        preset = await self.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"预设 ID {preset_id} 不存在。")
        if preset.is_builtin:
            raise ValueError("系统内置预设不允许修改。")

        now = self._now()
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE presets
                SET name = ?, description = ?, system_prompt = ?, updated_at = ?
                WHERE id = ? AND is_builtin = 0
                """,
                (name, description, system_prompt, now, preset_id),
            )
            await db.commit()
            return await self._get_preset_by_id(db, preset_id)

    async def delete_preset(self, preset_id: int) -> None:
        """删除非内置预设。"""
        preset = await self.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"预设 ID {preset_id} 不存在。")
        if preset.is_builtin:
            raise ValueError("系统内置预设不允许删除。")

        async with self._connect() as db:
            await db.execute("DELETE FROM presets WHERE id = ? AND is_builtin = 0", (preset_id,))
            await db.commit()

    async def _get_user_by_id(self, db: aiosqlite.Connection, user_id: int | None) -> User:
        """在当前连接中按 ID 查询用户。"""
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("用户创建后未能读取到记录")
        return self._row_to_user(row)

    async def _get_session_by_id(self, db: aiosqlite.Connection, session_id: int | None) -> Session:
        """在当前连接中按 ID 查询会话。"""
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("会话创建后未能读取到记录")
        return self._row_to_session(row)

    async def _get_message_by_id(self, db: aiosqlite.Connection, message_id: int | None) -> Message:
        """在当前连接中按 ID 查询消息。"""
        cursor = await db.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("消息创建后未能读取到记录")
        return self._row_to_message(row)

    async def _get_preset_by_id(self, db: aiosqlite.Connection, preset_id: int | None) -> Preset:
        """在当前连接中按 ID 查询预设。"""
        cursor = await db.execute("SELECT * FROM presets WHERE id = ?", (preset_id,))
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("预设写入后未能读取到记录")
        return self._row_to_preset(row)

    @staticmethod
    def _now() -> str:
        """生成当前时间字符串，统一使用 ISO 格式保存到 SQLite。"""
        return datetime.now().isoformat()

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        """把 aiosqlite.Row 转成普通字典，方便传给 Pydantic 模型。"""
        return dict(row)

    @classmethod
    def _row_to_user(cls, row: aiosqlite.Row) -> User:
        """把 users 表记录转换为 User 模型。"""
        return User(**cls._row_to_dict(row))

    @classmethod
    def _row_to_session(cls, row: aiosqlite.Row) -> Session:
        """把 sessions 表记录转换为 Session 模型。"""
        return Session(**cls._row_to_dict(row))

    @classmethod
    def _row_to_message(cls, row: aiosqlite.Row) -> Message:
        """把 messages 表记录转换为 Message 模型。"""
        return Message(**cls._row_to_dict(row))

    @classmethod
    def _row_to_preset(cls, row: aiosqlite.Row) -> Preset:
        """把 presets 表记录转换为 Preset 模型。"""
        data = cls._row_to_dict(row)
        data["is_builtin"] = bool(data["is_builtin"])
        return Preset(**data)



