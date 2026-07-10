"""项目配置轻量检查脚本。

运行方式：
    uv run python scripts/check_project_config.py

本脚本只检查配置文件和目录是否齐全，不连接真实模型，也不连接 MySQL。
"""

import os
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config_manager import ConfigManager

VALID_STORAGE_TYPES = {"sqlite", "mysql", "file"}
VALID_APP_ENVS = {"development", "testing", "production"}


def main() -> None:
    """执行项目配置检查。"""
    config_path = PROJECT_ROOT / "config.yaml"
    env_example_path = PROJECT_ROOT / ".env.example"
    logging_path = PROJECT_ROOT / "logging.yaml"
    logs_dir = PROJECT_ROOT / "logs"
    configuration_doc = PROJECT_ROOT / "docs" / "configuration.md"
    readme_path = PROJECT_ROOT / "README.md"
    env_paths = {
        "development": PROJECT_ROOT / "config" / "envs" / "development.yaml",
        "testing": PROJECT_ROOT / "config" / "envs" / "testing.yaml",
        "production": PROJECT_ROOT / "config" / "envs" / "production.yaml",
    }

    _require_file(config_path, "config.yaml")
    _require_file(env_example_path, ".env.example")
    _require_file(logging_path, "logging.yaml")
    _require_dir(logs_dir, "logs")
    _require_file(configuration_doc, "docs/configuration.md")
    _require_file(readme_path, "README.md")
    for label, path in env_paths.items():
        _require_file(path, f"config/envs/{label}.yaml")

    app_env = os.getenv("APP_ENV")
    if app_env and app_env not in VALID_APP_ENVS:
        raise RuntimeError("APP_ENV 必须是 development / testing / production 之一。")

    config = ConfigManager(project_root=PROJECT_ROOT).get_config()
    storage = config.get("storage")
    if not isinstance(storage, dict):
        raise RuntimeError("config.yaml 缺少 storage 配置块。")

    storage_type = storage.get("type")
    if storage_type not in VALID_STORAGE_TYPES:
        raise RuntimeError("storage.type 必须是 sqlite / mysql / file 之一。")

    for section in ("sqlite", "mysql", "file"):
        if section not in storage:
            raise RuntimeError(f"环境覆盖后缺少 storage.{section} 配置块。")

    models = config.get("models")
    if not isinstance(models, dict) or not models.get("available"):
        raise RuntimeError("环境覆盖后缺少 models.available 模型配置。")

    app_config = config.get("app", {}) if isinstance(config.get("app"), dict) else {}
    sqlite_path = storage.get("sqlite", {}).get("path", "")

    print(f"当前加载环境：{app_config.get('env', '未设置')}")
    print(f"当前 storage.type：{storage_type}")
    print(f"当前 SQLite 路径：{sqlite_path}")

    if storage_type == "mysql":
        print("提示：当前 storage.type=mysql，请确认 .env 中已填写 MYSQL_PASSWORD。")

    print("项目配置检查通过")


def _load_yaml(path: Path) -> dict[str, Any]:
    """读取 YAML 文件。"""
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"{path.name} 顶层结构必须是字典。")
    return data


def _require_file(path: Path, label: str) -> None:
    """确认文件存在。"""
    if not path.is_file():
        raise RuntimeError(f"缺少必要文件：{label}")


def _require_dir(path: Path, label: str) -> None:
    """确认目录存在。"""
    if not path.is_dir():
        raise RuntimeError(f"缺少必要目录：{label}")


if __name__ == "__main__":
    main()
