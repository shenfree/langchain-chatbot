"""UserManager 单元测试。"""

import pytest

from src.core.user_manager import UserManager
from src.storage.sqlite_backend import SQLiteBackend


@pytest.mark.asyncio
async def test_create_user_and_reject_duplicate(sqlite_storage: SQLiteBackend) -> None:
    """创建用户成功，重复用户名应报错。"""
    manager = UserManager(sqlite_storage)

    user = await manager.create_user(" alice ")

    assert user.id is not None
    assert user.username == "alice"

    with pytest.raises(ValueError, match="已存在"):
        await manager.create_user("alice")


@pytest.mark.asyncio
async def test_switch_user(sqlite_storage: SQLiteBackend) -> None:
    """切换用户后应能读取当前用户。"""
    manager = UserManager(sqlite_storage)
    await manager.create_user("alice")

    current = await manager.switch_user("alice")

    assert current.username == "alice"
    assert manager.get_current_user() is not None
    assert manager.get_current_user().username == "alice"


@pytest.mark.asyncio
async def test_delete_user_clears_current_user(sqlite_storage: SQLiteBackend) -> None:
    """删除当前用户后，应同步清空当前用户状态。"""
    manager = UserManager(sqlite_storage)
    await manager.create_user("alice")
    await manager.switch_user("alice")

    await manager.delete_user("alice")

    assert manager.get_current_user() is None
    assert await manager.get_user("alice") is None
