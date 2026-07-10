"""存储层基础流程测试。"""

import sqlite3
from pathlib import Path

import pytest

from src.storage.sqlite_backend import SQLiteBackend


@pytest.mark.asyncio
async def test_init_storage_creates_tables(tmp_path: Path) -> None:
    """init_storage 应能创建核心数据表。"""
    db_path = tmp_path / "storage.db"
    storage = SQLiteBackend(db_path)
    await storage.init_storage()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()

    table_names = {row[0] for row in rows}
    assert {"users", "sessions", "messages", "presets", "user_configs"}.issubset(table_names)


@pytest.mark.asyncio
async def test_storage_basic_user_session_message_flow(sqlite_storage: SQLiteBackend) -> None:
    """验证用户、会话、消息的最小闭环。"""
    user = await sqlite_storage.create_user("alice")
    users = await sqlite_storage.list_users()

    assert user.id is not None
    assert [item.username for item in users] == ["alice"]

    session = await sqlite_storage.create_session(
        user_id=user.id,
        title="测试会话",
        model_name="test-model",
    )
    message = await sqlite_storage.add_message(
        session_id=session.id,
        role="human",
        content="你好，LangChain",
    )
    messages = await sqlite_storage.list_messages(session.id)

    assert session.id is not None
    assert message.id is not None
    assert len(messages) == 1
    assert messages[0].role == "human"
    assert messages[0].content == "你好，LangChain"
