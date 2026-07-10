"""存储后端工厂。

工厂负责根据 config.yaml 中的 storage.type 创建具体存储实现。
Step 11 开始支持 SQLite 与 MySQL 两种后端切换。
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.storage.base import StorageBackend
from src.storage.mysql_backend import MySQLBackend
from src.storage.sqlite_backend import SQLiteBackend


class StorageFactory:
    """存储后端工厂类。"""

    @staticmethod
    def create(config: dict[str, Any], project_root: Path | None = None) -> StorageBackend:
        """根据配置创建具体存储后端。

        Args:
            config: ConfigManager.get_config() 返回的完整配置字典。
            project_root: 项目根目录，用于解析相对路径和加载 .env。
        """
        root = project_root or Path.cwd()
        storage_config = config.get("storage", {})
        storage_type = storage_config.get("type", "sqlite")

        if storage_type == "sqlite":
            return StorageFactory._create_sqlite(storage_config, root)

        if storage_type == "mysql":
            return StorageFactory._create_mysql(storage_config, root)

        if storage_type == "file":
            raise NotImplementedError("file 存储后端将在后续步骤实现。")

        raise ValueError(f"不支持的存储类型：{storage_type}")

    @staticmethod
    def _create_sqlite(storage_config: dict[str, Any], project_root: Path) -> StorageBackend:
        """创建 SQLite 后端。"""
        sqlite_config = storage_config.get("sqlite", {})
        db_path = Path(sqlite_config.get("path", "data/sqlite/app.db"))

        # config.yaml 中通常写相对路径，这里统一按项目根目录解析。
        if not db_path.is_absolute():
            db_path = project_root / db_path

        return SQLiteBackend(db_path)

    @staticmethod
    def _create_mysql(storage_config: dict[str, Any], project_root: Path) -> StorageBackend:
        """创建 MySQL 后端。

        MySQL 密码属于敏感信息，只从 .env 的 MYSQL_PASSWORD 读取，不写入 config.yaml。
        非敏感字段优先读取环境变量，便于本地临时覆盖；否则使用 config.yaml。
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
            raise ValueError("当前 storage.type=mysql，但缺少环境变量 MYSQL_PASSWORD，请在 .env 中填写。")

        return MySQLBackend(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
        )
