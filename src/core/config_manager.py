"""基础配置管理器。

本模块负责读取项目根目录下的 config.yaml、可选环境配置和 .env。
Step 15 增加 APP_ENV 多环境配置能力，支持 development / testing / production。
"""

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigManager:
    """配置管理器。

    设计成普通类，方便应用启动时创建实例，也方便测试时传入不同项目根目录。
    """

    VALID_ENVS = {"development", "testing", "production"}

    def __init__(self, project_root: Path | None = None) -> None:
        """初始化配置管理器。

        Args:
            project_root: 项目根目录。为空时，自动从当前文件位置推导到项目根目录。
        """
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.config_path = self.project_root / "config.yaml"
        self.env_path = self.project_root / ".env"
        self.envs_dir = self.project_root / "config" / "envs"
        self._config: dict[str, Any] | None = None

    def get_config(self) -> dict[str, Any]:
        """读取并返回合并后的配置内容。

        默认只读取 config.yaml，保持历史兼容。
        如果设置 APP_ENV，则读取 config/envs/{APP_ENV}.yaml，并递归覆盖基础配置。
        """
        if self._config is None:
            base_config = self._load_yaml_file(self.config_path, missing_ok=True)
            app_env = self.get_env("APP_ENV")

            if app_env:
                env_name = app_env.strip().lower()
                if env_name not in self.VALID_ENVS:
                    valid_text = ", ".join(sorted(self.VALID_ENVS))
                    raise ValueError(f"不支持的 APP_ENV：{app_env}，可选值：{valid_text}")

                env_config_path = self.envs_dir / f"{env_name}.yaml"
                if not env_config_path.exists():
                    raise FileNotFoundError(f"APP_ENV={env_name}，但环境配置文件不存在：{env_config_path}")

                env_config = self._load_yaml_file(env_config_path)
                self._config = self._deep_merge(base_config, env_config)
            else:
                self._config = base_config

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

    def _load_yaml_file(self, path: Path, missing_ok: bool = False) -> dict[str, Any]:
        """读取 YAML 文件并确保顶层结构是字典。"""
        if not path.exists():
            if missing_ok:
                return {}
            raise FileNotFoundError(f"配置文件不存在：{path}")

        with path.open("r", encoding="utf-8") as file:
            loaded_config = yaml.safe_load(file) or {}

        if not isinstance(loaded_config, dict):
            raise ValueError(f"配置文件顶层结构必须是字典：{path}")
        return loaded_config

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """递归合并配置，override 覆盖 base 中的同名叶子节点。"""
        merged = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = cls._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
