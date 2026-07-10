"""数据库初始化脚本。

运行方式：
    uv run python scripts/init_db.py

本脚本只负责根据 config.yaml 初始化当前选择的存储后端，不插入业务数据，也不启动 TUI。
"""

import asyncio
import sys
from pathlib import Path

# 使用 `python scripts/init_db.py` 运行时，Python 默认只把 scripts 目录加入导入路径。
# 这里补充项目根目录，确保可以正常导入 src 包。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config_manager import ConfigManager
from src.storage.factory import StorageFactory


async def main() -> None:
    """读取配置并初始化当前存储后端。"""
    config_manager = ConfigManager(project_root=PROJECT_ROOT)
    config = config_manager.get_config()
    storage_config = config.get("storage", {})
    storage_type = storage_config.get("type", "sqlite")

    storage = StorageFactory.create(config, project_root=PROJECT_ROOT)
    try:
        await storage.init_storage()
    finally:
        await storage.close()

    if storage_type == "sqlite":
        sqlite_path = storage_config.get("sqlite", {}).get("path", "data/sqlite/app.db")
        print(f"SQLite 数据库初始化完成：{sqlite_path}")
        return

    if storage_type == "mysql":
        database = storage_config.get("mysql", {}).get("database", "langchain_chat")
        print(f"MySQL 数据库初始化完成：{database}")
        return

    print(f"{storage_type} 存储初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
