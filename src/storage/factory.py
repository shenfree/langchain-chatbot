"""存储后端工厂。

工厂负责根据配置创建具体的存储后端实例。
当前 Step 3 只真正支持 SQLite，其他类型先预留扩展入口。
"""

from pathlib import Path
from typing import Any

from src.storage.base import StorageBackend
from src.storage.sqlite_backend import SQLiteBackend


class StorageFactory:
    """存储后端工厂类。"""

    @staticmethod
    def create(config: dict[str, Any], project_root: Path | None = None) -> StorageBackend:
        """根据 config.yaml 配置创建存储后端。

        Args:
            config: ConfigManager.get_config() 返回的完整配置字典。
            project_root: 项目根目录，用于把相对数据库路径转换为绝对路径。
        """
        storage_config = config.get("storage", {})
        storage_type = storage_config.get("type", "sqlite")

        if storage_type == "sqlite":
            sqlite_config = storage_config.get("sqlite", {})
            db_path = Path(sqlite_config.get("path", "data/sqlite/app.db"))

            # config.yaml 中通常写相对路径，这里统一按项目根目录解析。
            if not db_path.is_absolute():
                root = project_root or Path.cwd()
                db_path = root / db_path

            return SQLiteBackend(db_path)

        if storage_type in {"mysql", "file"}:
            raise NotImplementedError(f"{storage_type} 存储后端将在后续步骤实现。")

        raise ValueError(f"不支持的存储类型：{storage_type}")
