"""统一日志工具。

本模块提供项目级日志初始化能力：
- 优先读取 logging.yaml；
- 配置文件不存在时使用 basicConfig 兜底；
- 自动创建 logs/ 目录；
- 避免重复初始化导致同一条日志输出多次。
"""

import logging
import logging.config
from pathlib import Path
from typing import Any

import yaml

_LOGGING_INITIALIZED = False


def setup_logging(config_path: str | Path = "logging.yaml") -> None:
    """初始化项目日志系统。

    Args:
        config_path: logging.yaml 路径。可以传相对路径或绝对路径。
    """
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    path = Path(config_path)
    project_root = path.parent if path.is_absolute() else Path.cwd()
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            config: dict[str, Any] = yaml.safe_load(file) or {}
        _normalize_file_handler_paths(config, project_root)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s",
        )

    _LOGGING_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger。"""
    return logging.getLogger(name)


def _normalize_file_handler_paths(config: dict[str, Any], project_root: Path) -> None:
    """把 logging.yaml 中的相对日志文件路径转换为项目根目录下的绝对路径。"""
    handlers = config.get("handlers", {})
    if not isinstance(handlers, dict):
        return

    for handler in handlers.values():
        if not isinstance(handler, dict):
            continue
        filename = handler.get("filename")
        if not filename:
            continue
        file_path = Path(str(filename))
        if not file_path.is_absolute():
            file_path = project_root / file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        handler["filename"] = str(file_path)
