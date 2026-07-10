"""用户接口。"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps import AppServices, get_services
from backend.schemas import CurrentUserResponse, UserCreateRequest, UserSwitchRequest
from src.models.schemas import User

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=User)
async def create_user(payload: UserCreateRequest, services: AppServices = Depends(get_services)) -> User:
    """创建用户。"""
    try:
        return await services.user_manager.create_user(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[User])
async def list_users(services: AppServices = Depends(get_services)) -> list[User]:
    """获取用户列表。"""
    return await services.user_manager.list_users()


@router.get("/current", response_model=CurrentUserResponse)
async def get_current_user(services: AppServices = Depends(get_services)) -> CurrentUserResponse:
    """获取当前用户。"""
    return CurrentUserResponse(user=services.current_user)


@router.post("/current", response_model=User)
async def switch_current_user(
    payload: UserSwitchRequest,
    services: AppServices = Depends(get_services),
) -> User:
    """切换当前用户，支持按 username 或 user_id。"""
    username = payload.username
    if username is None and payload.user_id is not None:
        users = await services.user_manager.list_users()
        user = next((item for item in users if item.id == payload.user_id), None)
        if user is not None:
            username = user.username

    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 username 或 user_id")

    try:
        user = await services.user_manager.switch_user(username)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    services.current_user = user
    return user


@router.delete("/{user_id}")
async def delete_user(user_id: int, services: AppServices = Depends(get_services)) -> dict[str, str]:
    """删除用户。"""
    users = await services.user_manager.list_users()
    user = next((item for item in users if item.id == user_id), None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    await services.user_manager.delete_user(user.username)
    if services.current_user is not None and services.current_user.id == user_id:
        services.current_user = None
    return {"message": "用户已删除"}
