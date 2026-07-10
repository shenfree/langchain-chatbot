"""聊天接口。"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps import AppServices, get_services, require_current_user
from backend.schemas import ChatRequest, ChatResponse
from src.core.chat_engine import ChatEngine

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, services: AppServices = Depends(get_services)) -> ChatResponse:
    """执行一次完整聊天回复。

    MVP 阶段返回完整 AI 回复。后续如果需要真正的浏览器流式体验，
    可以扩展为 /chat/stream，并使用 SSE 或 WebSocket 推送 chunk。
    """
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

    engine = ChatEngine(
        config_manager=services.config_manager,
        system_prompt=system_prompt,
        model_name=model_name,
    )
    try:
        reply = await engine.chat_once(message, history=history, system_prompt=system_prompt)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    await services.session_manager.add_ai_message(session.id, reply)
    await services.session_manager.auto_title_from_first_message(session.id, message)
    if model_name != session.model_name:
        await services.session_manager.update_session_model(session.id, model_name)

    return ChatResponse(session_id=session.id, reply=reply)
