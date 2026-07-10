"""会话接口。"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps import AppServices, get_services, require_current_user
from backend.schemas import SessionCreateRequest, SessionDetailResponse, SessionUpdateRequest
from src.models.schemas import Session

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _get_owned_session(session_id: int, services: AppServices) -> Session:
    """获取当前用户拥有的会话。"""
    current_user = require_current_user(services)
    session = await services.session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能操作其他用户的会话")
    return session


@router.post("", response_model=Session)
async def create_session(
    payload: SessionCreateRequest,
    services: AppServices = Depends(get_services),
) -> Session:
    """新建会话。"""
    current_user = require_current_user(services)
    model_name = payload.model_name or services.model_manager.get_current_model()
    return await services.session_manager.create_session(
        user_id=current_user.id,
        title=payload.title or "新会话",
        model_name=model_name,
        preset_id=payload.preset_id,
    )


@router.get("", response_model=list[Session])
async def list_sessions(services: AppServices = Depends(get_services)) -> list[Session]:
    """获取当前用户会话列表。"""
    current_user = require_current_user(services)
    return await services.session_manager.list_sessions(current_user.id)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: int,
    services: AppServices = Depends(get_services),
) -> SessionDetailResponse:
    """获取会话详情和消息列表。"""
    session = await _get_owned_session(session_id, services)
    messages = await services.session_manager.get_messages(session_id)
    return SessionDetailResponse(session=session, messages=messages)


@router.patch("/{session_id}", response_model=Session)
async def rename_session(
    session_id: int,
    payload: SessionUpdateRequest,
    services: AppServices = Depends(get_services),
) -> Session:
    """重命名会话。"""
    await _get_owned_session(session_id, services)
    try:
        return await services.session_manager.rename_session(session_id, payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{session_id}")
async def delete_session(session_id: int, services: AppServices = Depends(get_services)) -> dict[str, str]:
    """删除会话。"""
    await _get_owned_session(session_id, services)
    await services.session_manager.delete_session(session_id)
    return {"message": "会话已删除"}
