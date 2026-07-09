"""基础配置管理器。

本模块负责读取项目根目录下的 config.yaml 和 .env。
Step 2 只提供最小可用能力，后续再扩展多环境配置、配置校验等功能。
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigManager:
    """配置管理器。

    设计成普通类，方便后续在应用启动时创建实例，也方便测试时传入不同项目根目录。
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """初始化配置管理器。

        Args:
            project_root: 项目根目录。为空时，自动从当前文件位置推导到项目根目录。
        """
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.config_path = self.project_root / "config.yaml"
        self.env_path = self.project_root / ".env"
        self._config: dict[str, Any] | None = None

    def get_config(self) -> dict[str, Any]:
        """读取并返回 config.yaml 的配置内容。

        为了避免重复读文件，第一次读取后会缓存在内存中。
        """
        if self._config is None:
            if not self.config_path.exists():
                self._config = {}
                return self._config

            with self.config_path.open("r", encoding="utf-8") as file:
                loaded_config = yaml.safe_load(file) or {}

            # yaml.safe_load 正常会返回 dict；这里做一次保护，避免配置文件内容不是对象时出错。
            self._config = loaded_config if isinstance(loaded_config, dict) else {}

        return self._config

    def get_env(self, name: str, default: str | None = None) -> str | None:
        """读取环境变量。

        先加载项目根目录下的 .env，再从系统环境变量中取值。
        Args:
            name: 环境变量名称。
            default: 环境变量不存在时返回的默认值。
        """
        load_dotenv(self.env_path)
        return os.getenv(name, default)
