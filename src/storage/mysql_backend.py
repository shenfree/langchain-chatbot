"""MySQL 存储后端实现。

本模块只负责 MySQL 数据持久化，不包含任何 TUI 或业务规则。
Step 11 的目标是让项目可以通过 config.yaml 的 storage.type 在 SQLite 与 MySQL 之间切换。
"""

from datetime import datetime
from typing import Any

import aiomysql

from src.models.schemas import Message, Preset, Session, User
from src.storage.base import StorageBackend


class MySQLBackend(StorageBackend):
    """基于 aiomysql 连接池的异步 MySQL 存储后端。"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str = "utf8mb4",
    ) -> None:
        """保存 MySQL 连接参数。"""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.pool: aiomysql.Pool | None = None

    async def init_storage(self) -> None:
        """创建连接池并初始化全部数据表。

        注意：本方法默认数据库已经存在。可以先在 MySQL 中执行：
        CREATE DATABASE langchain_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """
        self.pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            charset=self.charset,
            autocommit=False,
        )

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        username VARCHAR(255) NOT NULL UNIQUE,
                        default_model VARCHAR(255),
                        default_preset_id BIGINT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS presets (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        user_id BIGINT NULL,
                        name VARCHAR(255) NOT NULL,
                        description TEXT NOT NULL,
                        system_prompt TEXT NOT NULL,
                        is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        user_id BIGINT NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        model_name VARCHAR(255) NOT NULL,
                        preset_id BIGINT NULL,
                        total_prompt_tokens INT NOT NULL DEFAULT 0,
                        total_completion_tokens INT NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY(preset_id) REFERENCES presets(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        session_id BIGINT NOT NULL,
                        role VARCHAR(32) NOT NULL,
                        content TEXT NOT NULL,
                        prompt_tokens INT NOT NULL DEFAULT 0,
                        completion_tokens INT NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_configs (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        user_id BIGINT NOT NULL,
                        `key` VARCHAR(255) NOT NULL,
                        value TEXT NOT NULL,
                        updated_at DATETIME NOT NULL,
                        UNIQUE KEY uniq_user_config(user_id, `key`),
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
            await conn.commit()

    async def close(self) -> None:
        """关闭 MySQL 连接池。"""
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

    async def create_user(self, username: str) -> User:
        """创建用户并返回用户对象。"""
        now = self._now()
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    "INSERT INTO users (username, created_at, updated_at) VALUES (%s, %s, %s)",
                    (username, now, now),
                )
                user_id = cursor.lastrowid
            await conn.commit()
            return await self._get_user_by_id(conn, user_id)

    async def get_user_by_username(self, username: str) -> User | None:
        """根据用户名查询用户。"""
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = await cursor.fetchone()
                return self._row_to_user(row) if row else None

    async def list_users(self) -> list[User]:
        """查询所有用户。"""
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM users ORDER BY id ASC")
                rows = await cursor.fetchall()
                return [self._row_to_user(row) for row in rows]

    async def delete_user(self, user_id: int) -> None:
        """删除用户，相关会话、消息和配置由外键级联删除。"""
        async with self._conn() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            await conn.commit()

    async def create_session(
        self,
        user_id: int,
        title: str,
        model_name: str,
        preset_id: int | None = None,
    ) -> Session:
        """创建会话并返回会话对象。"""
        now = self._now()
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    INSERT INTO sessions (
                        user_id, title, model_name, preset_id,
                        total_prompt_tokens, total_completion_tokens, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, 0, 0, %s, %s)
                    """,
                    (user_id, title, model_name, preset_id, now, now),
                )
                session_id = cursor.lastrowid
            await conn.commit()
            return await self._get_session_by_id(conn, session_id)

    async def list_sessions(self, user_id: int) -> list[Session]:
        """按更新时间倒序查询指定用户会话。"""
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    "SELECT * FROM sessions WHERE user_id = %s ORDER BY updated_at DESC, id DESC",
                    (user_id,),
                )
                rows = await cursor.fetchall()
                return [self._row_to_session(row) for row in rows]

    async def get_session(self, session_id: int) -> Session | None:
        """根据 ID 查询会话。"""
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
                row = await cursor.fetchone()
                return self._row_to_session(row) if row else None

    async def update_session_title(self, session_id: int, title: str) -> Session | None:
        """更新会话标题。"""
        now = self._now()
        async with self._conn() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE sessions SET title = %s, updated_at = %s WHERE id = %s",
                    (title, now, session_id),
                )
            await conn.commit()
            return await self._get_optional_session_by_id(conn, session_id)

    async def update_session_model(self, session_id: int, model_name: str) -> Session | None:
        """更新会话模型名。"""
        now = self._now()
        async with self._conn() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE sessions SET model_name = %s, updated_at = %s WHERE id = %s",
                    (model_name, now, session_id),
                )
            await conn.commit()
            return await self._get_optional_session_by_id(conn, session_id)

    async def delete_session(self, session_id: int) -> None:
        """删除会话，消息由外键级联删除。"""
        async with self._conn() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
            await conn.commit()

    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Message:
        """向会话追加消息，并更新会话更新时间和 token 统计。"""
        now = self._now()
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    INSERT INTO messages (
                        session_id, role, content, prompt_tokens, completion_tokens, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (session_id, role, content, prompt_tokens, completion_tokens, now),
                )
                message_id = cursor.lastrowid
                await cursor.execute(
                    """
                    UPDATE sessions
                    SET updated_at = %s,
                        total_prompt_tokens = total_prompt_tokens + %s,
                        total_completion_tokens = total_completion_tokens + %s
                    WHERE id = %s
                    """,
                    (now, prompt_tokens, completion_tokens, session_id),
                )
            await conn.commit()
            return await self._get_message_by_id(conn, message_id)

    async def list_messages(self, session_id: int) -> list[Message]:
        """按 ID 正序查询会话消息。"""
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM messages WHERE session_id = %s ORDER BY id ASC", (session_id,))
                rows = await cursor.fetchall()
                return [self._row_to_message(row) for row in rows]

    async def search_messages(self, user_id: int, keyword: str) -> list[dict]:
        """在指定用户自己的历史消息中搜索关键词。"""
        cleaned_keyword = keyword.strip()
        if not cleaned_keyword:
            return []
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
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
                    WHERE sessions.user_id = %s
                      AND messages.content LIKE %s
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
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    INSERT INTO presets (
                        user_id, name, description, system_prompt, is_builtin, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, name, description, system_prompt, int(is_builtin), now, now),
                )
                preset_id = cursor.lastrowid
            await conn.commit()
            return await self._get_preset_by_id(conn, preset_id)

    async def get_preset(self, preset_id: int) -> Preset | None:
        """根据 ID 查询预设。"""
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM presets WHERE id = %s", (preset_id,))
                row = await cursor.fetchone()
                return self._row_to_preset(row) if row else None

    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """查询系统内置预设和用户个人预设。"""
        async with self._conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if user_id is None:
                    await cursor.execute("SELECT * FROM presets WHERE is_builtin = TRUE ORDER BY id ASC")
                else:
                    await cursor.execute(
                        """
                        SELECT * FROM presets
                        WHERE is_builtin = TRUE OR user_id = %s
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
        """更新非内置预设，内置预设禁止修改。"""
        preset = await self.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"预设 ID {preset_id} 不存在。")
        if preset.is_builtin:
            raise ValueError("系统内置预设不允许修改。")

        now = self._now()
        async with self._conn() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE presets
                    SET name = %s, description = %s, system_prompt = %s, updated_at = %s
                    WHERE id = %s AND is_builtin = FALSE
                    """,
                    (name, description, system_prompt, now, preset_id),
                )
            await conn.commit()
            return await self._get_preset_by_id(conn, preset_id)

    async def delete_preset(self, preset_id: int) -> None:
        """删除非内置预设，内置预设禁止删除。"""
        preset = await self.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"预设 ID {preset_id} 不存在。")
        if preset.is_builtin:
            raise ValueError("系统内置预设不允许删除。")
        async with self._conn() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM presets WHERE id = %s AND is_builtin = FALSE", (preset_id,))
            await conn.commit()

    def _conn(self):
        """获取连接池连接；未初始化时给出清晰错误。"""
        if self.pool is None:
            raise RuntimeError("MySQL 连接池尚未初始化，请先调用 init_storage()。")
        return self.pool.acquire()

    async def _get_user_by_id(self, conn: aiomysql.Connection, user_id: int | None) -> User:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("用户创建后未能读取到记录")
            return self._row_to_user(row)

    async def _get_session_by_id(self, conn: aiomysql.Connection, session_id: int | None) -> Session:
        session = await self._get_optional_session_by_id(conn, session_id)
        if session is None:
            raise RuntimeError("会话创建后未能读取到记录")
        return session

    async def _get_optional_session_by_id(self, conn: aiomysql.Connection, session_id: int | None) -> Session | None:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
            row = await cursor.fetchone()
            return self._row_to_session(row) if row else None

    async def _get_message_by_id(self, conn: aiomysql.Connection, message_id: int | None) -> Message:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("消息创建后未能读取到记录")
            return self._row_to_message(row)

    async def _get_preset_by_id(self, conn: aiomysql.Connection, preset_id: int | None) -> Preset:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM presets WHERE id = %s", (preset_id,))
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("预设写入后未能读取到记录")
            return self._row_to_preset(row)

    @staticmethod
    def _now() -> datetime:
        """生成当前时间，写入 MySQL DATETIME。"""
        return datetime.now()

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
