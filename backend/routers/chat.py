"""聊天接口。"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.deps import AppServices, get_services, require_current_user
from backend.schemas import ChatRequest, ChatResponse
from src.core.chat_engine import ChatEngine
from src.models.schemas import Session

router = APIRouter(prefix="/chat", tags=["chat"])


@dataclass
class ChatContext:
    """一次聊天请求需要的上下文。"""

    session: Session
    message: str
    history: list[dict[str, str]]
    system_prompt: str | None
    model_name: str


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, services: AppServices = Depends(get_services)) -> ChatResponse:
    """执行一次完整聊天回复。"""
    context = await prepare_chat_context(payload, services)
    engine = ChatEngine(
        config_manager=services.config_manager,
        system_prompt=context.system_prompt,
        model_name=context.model_name,
    )
    try:
        reply = await engine.chat_once(
            context.message,
            history=context.history,
            system_prompt=context.system_prompt,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    await finalize_chat_response(services, context, reply)
    return ChatResponse(session_id=context.session.id, reply=reply)


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    services: AppServices = Depends(get_services),
) -> StreamingResponse:
    """执行流式聊天回复。

    该接口使用 text/plain 流式返回 chunk。前端逐段读取并更新页面。
    如果后续需要标准 SSE，可在保持本接口逻辑的基础上扩展为 text/event-stream。
    """
    context = await prepare_chat_context(payload, services)

    async def chunk_generator() -> AsyncIterator[str]:
        full_answer = ""
        engine = ChatEngine(
            config_manager=services.config_manager,
            system_prompt=context.system_prompt,
            model_name=context.model_name,
        )
        try:
            async for chunk in engine.stream_chat(
                context.message,
                history=context.history,
                system_prompt=context.system_prompt,
            ):
                full_answer += chunk
                yield chunk
        except Exception as exc:
            yield f"\n[流式接口调用失败：{exc}]"
            return

        if full_answer.strip():
            await finalize_chat_response(services, context, full_answer)

    return StreamingResponse(chunk_generator(), media_type="text/plain; charset=utf-8")


async def prepare_chat_context(payload: ChatRequest, services: AppServices) -> ChatContext:
    """校验聊天请求、构建历史并保存本轮 human 消息。"""
    current_user = require_current_user(services)
    session = await services.session_manager.get_session(payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能操作其他用户的会话")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消息不能为空")

    preset_id = payload.preset_id or session.preset_id
    system_prompt = None
    if preset_id is not None:
        preset = await services.preset_manager.get_preset(preset_id)
        if preset is not None:
            system_prompt = preset.system_prompt

    model_name = payload.model_name or session.model_name or services.model_manager.get_current_model()

    # 先构建历史，再保存本轮 human 消息，避免当前输入在 history 和 user_input 中重复出现。
    history = await services.session_manager.build_history(session.id)
    await services.session_manager.add_user_message(session.id, message)

    return ChatContext(
        session=session,
        message=message,
        history=history,
        system_prompt=system_prompt,
        model_name=model_name,
    )


async def finalize_chat_response(services: AppServices, context: ChatContext, reply: str) -> None:
    """保存 AI 回复，并更新会话标题和模型。"""
    await services.session_manager.add_ai_message(context.session.id, reply)
    await services.session_manager.auto_title_from_first_message(context.session.id, context.message)
    if context.model_name != context.session.model_name:
        await services.session_manager.update_session_model(context.session.id, context.model_name)
