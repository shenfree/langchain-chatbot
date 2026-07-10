"""SessionManager 单元测试。"""

import pytest

from src.core.session_manager import SessionManager
from src.storage.sqlite_backend import SQLiteBackend


@pytest.mark.asyncio
async def test_session_manager_message_history_and_search(sqlite_storage: SQLiteBackend) -> None:
    """验证会话创建、消息保存、history 构建和搜索。"""
    user = await sqlite_storage.create_user("alice")
    manager = SessionManager(sqlite_storage)

    session = await manager.create_session(
        user_id=user.id,
        title="新会话",
        model_name="test-model",
    )
    await manager.add_user_message(session.id, "我正在学习 LangChain 多轮会话")
    await manager.add_ai_message(session.id, "很好，我们继续。")

    history = await manager.build_history(session.id)
    results = await manager.search_messages(user.id, "LangChain")

    assert history == [
        {"role": "human", "content": "我正在学习 LangChain 多轮会话"},
        {"role": "ai", "content": "很好，我们继续。"},
    ]
    assert len(results) == 1
    assert results[0]["session_id"] == session.id
    assert results[0]["role"] == "human"


@pytest.mark.asyncio
async def test_rename_and_delete_session(sqlite_storage: SQLiteBackend) -> None:
    """验证会话重命名和删除。"""
    user = await sqlite_storage.create_user("alice")
    manager = SessionManager(sqlite_storage)
    session = await manager.create_session(user.id, "新会话", "test-model")

    renamed = await manager.rename_session(session.id, "课程答疑")
    assert renamed.title == "课程答疑"

    await manager.delete_session(session.id)
    assert await manager.get_session(session.id) is None


@pytest.mark.asyncio
async def test_rename_session_rejects_empty_title(sqlite_storage: SQLiteBackend) -> None:
    """空标题不允许用于重命名。"""
    user = await sqlite_storage.create_user("alice")
    manager = SessionManager(sqlite_storage)
    session = await manager.create_session(user.id, "新会话", "test-model")

    with pytest.raises(ValueError, match="不能为空"):
        await manager.rename_session(session.id, "   ")
