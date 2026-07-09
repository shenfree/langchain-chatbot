"""会话管理业务逻辑。

本模块负责会话创建、消息保存、历史消息组装和自动标题生成。
TUI 不直接操作 messages/sessions 表，只通过 SessionManager 调用存储层。
"""

from src.models.schemas import Message, Session
from src.storage.base import StorageBackend


class SessionManager:
    """会话管理器。

    Step 7 只实现新建会话、保存消息、查看会话列表和构建上下文历史。
    会话加载、重命名、删除、搜索、导出都留到后续步骤。
    """

    def __init__(self, storage: StorageBackend) -> None:
        """初始化会话管理器。"""
        self.storage = storage

    async def create_session(
        self,
        user_id: int,
        title: str,
        model_name: str,
        preset_id: int | None = None,
    ) -> Session:
        """创建新会话并返回会话对象。"""
        return await self.storage.create_session(
            user_id=user_id,
            title=title,
            model_name=model_name,
            preset_id=preset_id,
        )

    async def list_sessions(self, user_id: int) -> list[Session]:
        """查询当前用户的会话列表。"""
        return await self.storage.list_sessions(user_id)

    async def get_session(self, session_id: int) -> Session | None:
        """查询指定会话；找不到时返回 None。"""
        return await self.storage.get_session(session_id)

    async def get_messages(self, session_id: int) -> list[Message]:
        """查询指定会话的全部消息。"""
        return await self.storage.list_messages(session_id)

    async def add_user_message(self, session_id: int, content: str) -> Message:
        """保存 human 消息。"""
        cleaned_content = content.strip()
        if not cleaned_content:
            raise ValueError("消息内容不能为空。")
        return await self.storage.add_message(
            session_id=session_id,
            role="human",
            content=cleaned_content,
        )

    async def add_ai_message(
        self,
        session_id: int,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Message:
        """保存 ai 消息。"""
        cleaned_content = content.strip()
        if not cleaned_content:
            raise ValueError("AI 回复内容不能为空。")
        return await self.storage.add_message(
            session_id=session_id,
            role="ai",
            content=cleaned_content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    async def build_history(self, session_id: int) -> list[dict[str, str]]:
        """把数据库消息转换成 ChatEngine 接收的历史格式。

        预设 system_prompt 会在调用 ChatEngine 时单独传入，因此这里不额外插入系统提示词，
        避免同一个 system_prompt 在上下文中重复出现。
        """
        messages = await self.get_messages(session_id)
        history: list[dict[str, str]] = []

        for message in messages:
            if message.role not in {"human", "ai", "system"}:
                continue
            history.append({"role": message.role, "content": message.content})

        return history

    async def auto_title_from_first_message(self, session_id: int, first_message: str) -> Session | None:
        """根据首条用户消息自动生成会话标题。

        只有当前标题为空或为“新会话”时才会更新，避免覆盖后续步骤可能提供的自定义标题。
        """
        session = await self.storage.get_session(session_id)
        if session is None:
            return None

        if session.title and session.title != "新会话":
            return session

        title = first_message.strip().replace("\n", " ")[:30] or "新会话"
        return await self.storage.update_session_title(session_id, title)
