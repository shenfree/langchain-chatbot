"""会话导出接口。"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps import AppServices, get_services, require_current_user
from backend.schemas import ExportResponse

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/{session_id}", response_model=ExportResponse)
async def export_session(session_id: int, services: AppServices = Depends(get_services)) -> ExportResponse:
    """导出当前用户的指定会话为 Markdown。"""
    current_user = require_current_user(services)
    session = await services.session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能导出其他用户的会话")

    path = await services.session_manager.export_session_to_markdown(session_id, current_user.username)
    return ExportResponse(path=str(path))
