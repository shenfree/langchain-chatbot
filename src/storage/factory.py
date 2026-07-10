"""存储后端工厂。

工厂负责根据 config.yaml 中的 storage.type 创建具体存储实现。
当前支持 SQLite / MySQL / File 三种后端切换。
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.storage.base import StorageBackend
from src.storage.file_backend import FileBackend
from src.storage.mysql_backend import MySQLBackend
from src.storage.sqlite_backend import SQLiteBackend
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StorageFactory:
    """存储后端工厂类。"""

    @staticmethod
    def create(config: dict[str, Any], project_root: Path | None = None) -> StorageBackend:
        """根据配置创建具体存储后端。"""
        root = project_root or Path.cwd()
        storage_config = config.get("storage", {})
        storage_type = storage_config.get("type", "sqlite")
        logger.info("创建存储后端：storage_type=%s", storage_type)

        if storage_type == "sqlite":
            return StorageFactory._create_sqlite(storage_config, root)

        if storage_type == "mysql":
            return StorageFactory._create_mysql(storage_config, root)

        if storage_type == "file":
            return StorageFactory._create_file(storage_config, root)

        logger.error("不支持的存储类型：storage_type=%s", storage_type)
        raise ValueError(f"不支持的存储类型：{storage_type}")

    @staticmethod
    def _create_sqlite(storage_config: dict[str, Any], project_root: Path) -> StorageBackend:
        """创建 SQLite 后端。"""
        sqlite_config = storage_config.get("sqlite", {})
        db_path = Path(sqlite_config.get("path", "data/sqlite/app.db"))

        if not db_path.is_absolute():
            db_path = project_root / db_path

        logger.debug("SQLite 后端路径已解析：db_path=%s", db_path)
        return SQLiteBackend(db_path)

    @staticmethod
    def _create_mysql(storage_config: dict[str, Any], project_root: Path) -> StorageBackend:
        """创建 MySQL 后端。

        MySQL 密码属于敏感信息，只从 .env 的 MYSQL_PASSWORD 读取，不写入日志。
        """
        load_dotenv(project_root / ".env")

        mysql_config = storage_config.get("mysql", {})
        host = os.getenv("MYSQL_HOST", str(mysql_config.get("host", "localhost")))
        port = int(os.getenv("MYSQL_PORT", str(mysql_config.get("port", 3306))))
        user = os.getenv("MYSQL_USER", str(mysql_config.get("user", "root")))
        database = os.getenv("MYSQL_DATABASE", str(mysql_config.get("database", "langchain_chat")))
        charset = str(mysql_config.get("charset", "utf8mb4"))
        password = os.getenv("MYSQL_PASSWORD")

        if not password:
            logger.error("MySQL 后端缺少 MYSQL_PASSWORD：host=%s port=%s database=%s", host, port, database)
            raise ValueError("当前 storage.type=mysql，但缺少环境变量 MYSQL_PASSWORD，请在 .env 中填写。")

        logger.info("MySQL 后端配置完成：host=%s port=%s database=%s user=%s", host, port, database, user)
        return MySQLBackend(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
        )

    @staticmethod
    def _create_file(storage_config: dict[str, Any], project_root: Path) -> StorageBackend:
        """创建 JSON 文件存储后端。"""
        file_config = storage_config.get("file", {})
        base_dir = Path(file_config.get("base_dir", "data/file_storage"))

        if not base_dir.is_absolute():
            base_dir = project_root / base_dir

        logger.debug("File 后端目录已解析：base_dir=%s", base_dir)
        return FileBackend(base_dir)
