"""历史消息搜索接口。"""

from fastapi import APIRouter, Depends, Query

from backend.deps import AppServices, get_services, require_current_user
from backend.schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search_messages(
    keyword: str = Query(min_length=1),
    services: AppServices = Depends(get_services),
) -> SearchResponse:
    """搜索当前用户历史消息。"""
    current_user = require_current_user(services)
    results = await services.session_manager.search_messages(current_user.id, keyword)
    return SearchResponse(results=results)
