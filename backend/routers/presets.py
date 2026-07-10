"""预设 Prompt 接口。"""

from fastapi import APIRouter, Depends

from backend.deps import AppServices, get_services
from backend.schemas import PresetsResponse

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=PresetsResponse)
async def list_presets(services: AppServices = Depends(get_services)) -> PresetsResponse:
    """获取系统内置预设和当前用户个人预设。"""
    user_id = services.current_user.id if services.current_user is not None else None
    presets = await services.preset_manager.list_presets(user_id=user_id)
    return PresetsResponse(presets=presets)
