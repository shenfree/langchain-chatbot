"""pytest 共享测试夹具。

测试统一使用临时 SQLite 数据库，避免污染项目真实运行数据。
"""

import sys
from pathlib import Path

import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.sqlite_backend import SQLiteBackend


@pytest_asyncio.fixture
async def sqlite_storage(tmp_path: Path) -> SQLiteBackend:
    """创建并初始化临时 SQLite 存储后端。"""
    db_path = tmp_path / "test.db"
    storage = SQLiteBackend(db_path)
    await storage.init_storage()
    try:
        yield storage
    finally:
        await storage.close()
