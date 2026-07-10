"""FastAPI 后端请求/响应模型。"""

from pydantic import BaseModel, Field

from src.models.schemas import Message, Preset, Session, User


class UserCreateRequest(BaseModel):
    """创建用户请求。"""

    username: str = Field(min_length=1)


class UserSwitchRequest(BaseModel):
    """切换当前用户请求。"""

    username: str | None = None
    user_id: int | None = None


class CurrentUserResponse(BaseModel):
    """当前用户响应。"""

    user: User | None


class SessionCreateRequest(BaseModel):
    """创建会话请求。"""

    title: str = "新会话"
    model_name: str | None = None
    preset_id: int | None = None


class SessionUpdateRequest(BaseModel):
    """更新会话请求。"""

    title: str


class SessionDetailResponse(BaseModel):
    """会话详情响应。"""

    session: Session
    messages: list[Message]


class ChatRequest(BaseModel):
    """聊天请求。"""

    session_id: int
    message: str = Field(min_length=1)
    preset_id: int | None = None
    model_name: str | None = None


class ChatResponse(BaseModel):
    """聊天响应。"""

    session_id: int
    reply: str


class PresetsResponse(BaseModel):
    """预设列表响应。"""

    presets: list[Preset]


class ModelsResponse(BaseModel):
    """模型列表响应。"""

    default_model: str
    current_model: str
    models: list[dict]


class SearchResponse(BaseModel):
    """搜索结果响应。"""

    results: list[dict]


class ExportResponse(BaseModel):
    """导出响应。"""

    path: str
