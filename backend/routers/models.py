"""模型接口。"""

from fastapi import APIRouter, Depends

from backend.deps import AppServices, get_services
from backend.schemas import ModelsResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelsResponse)
async def list_models(services: AppServices = Depends(get_services)) -> ModelsResponse:
    """获取可用模型列表、默认模型和当前模型。"""
    return ModelsResponse(
        default_model=services.model_manager.get_default_model(),
        current_model=services.model_manager.get_current_model(),
        models=services.model_manager.list_models(),
    )
