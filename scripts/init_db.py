"""数据库/文件存储初始化脚本。

运行方式：
    uv run python scripts/init_db.py

本脚本只负责根据 config.yaml 初始化当前选择的存储后端，不插入业务数据，也不启动 TUI。
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config_manager import ConfigManager
from src.storage.factory import StorageFactory
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
    """读取配置并初始化当前存储后端。"""
    setup_logging(PROJECT_ROOT / "logging.yaml")
    config_manager = ConfigManager(project_root=PROJECT_ROOT)
    config = config_manager.get_config()
    storage_config = config.get("storage", {})
    storage_type = storage_config.get("type", "sqlite")
    logger.info("开始初始化存储：storage_type=%s", storage_type)

    storage = StorageFactory.create(config, project_root=PROJECT_ROOT)
    try:
        await storage.init_storage()
    except Exception:
        logger.exception("存储初始化失败：storage_type=%s", storage_type)
        raise
    finally:
        await storage.close()

    if storage_type == "sqlite":
        sqlite_path = storage_config.get("sqlite", {}).get("path", "data/sqlite/app.db")
        logger.info("SQLite 数据库初始化完成：path=%s", sqlite_path)
        print(f"SQLite 数据库初始化完成：{sqlite_path}")
        return

    if storage_type == "mysql":
        database = storage_config.get("mysql", {}).get("database", "langchain_chat")
        logger.info("MySQL 数据库初始化完成：database=%s", database)
        print(f"MySQL 数据库初始化完成：{database}")
        return

    if storage_type == "file":
        base_dir = storage_config.get("file", {}).get("base_dir", "data/file_storage")
        logger.info("File 存储初始化完成：base_dir=%s", base_dir)
        print(f"File 存储初始化完成：{base_dir}")
        return

    logger.info("存储初始化完成：storage_type=%s", storage_type)
    print(f"{storage_type} 存储初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
