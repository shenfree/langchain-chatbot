"""FastAPI 依赖和服务容器。"""

import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request, status

from src.core.config_manager import ConfigManager
from src.core.model_manager import ModelManager
from src.core.preset_manager import PresetManager
from src.core.session_manager import SessionManager
from src.core.user_manager import UserManager
from src.models.schemas import User
from src.storage.base import StorageBackend
from src.storage.factory import StorageFactory


@dataclass
class AppServices:
    """后端复用现有核心模块的服务容器。"""

    project_root: Path
    config_manager: ConfigManager
    storage: StorageBackend
    user_manager: UserManager
    preset_manager: PresetManager
    session_manager: SessionManager
    model_manager: ModelManager
    current_user: User | None = None


async def create_services(project_root: Path | None = None) -> AppServices:
    """创建并初始化后端服务。"""
    root = project_root or Path(os.getenv("LANGCHAIN_CHAT_PROJECT_ROOT", Path.cwd()))
    config_manager = ConfigManager(project_root=root)
    config = config_manager.get_config()
    storage = StorageFactory.create(config, project_root=root)
    await storage.init_storage()

    user_manager = UserManager(storage)
    preset_manager = PresetManager(storage, project_root=root)
    session_manager = SessionManager(storage)
    model_manager = ModelManager(config_manager)
    await preset_manager.load_builtin_presets()

    return AppServices(
        project_root=root,
        config_manager=config_manager,
        storage=storage,
        user_manager=user_manager,
        preset_manager=preset_manager,
        session_manager=session_manager,
        model_manager=model_manager,
    )


async def close_services(services: AppServices) -> None:
    """关闭后端服务资源。"""
    await services.storage.close()


def get_services(request: Request) -> AppServices:
    """从 FastAPI app.state 中获取服务容器。"""
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="服务尚未初始化")
    return services


def require_current_user(services: AppServices) -> User:
    """获取当前用户；未选择时返回 400。"""
    if services.current_user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先创建并切换当前用户")
    return services.current_user
