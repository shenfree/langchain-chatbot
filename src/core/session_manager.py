"""会话管理业务逻辑。

本模块负责会话创建、消息保存、历史消息组装、自动标题生成，以及 Step 8 的会话
列表、加载、重命名和删除。TUI 不直接操作 sessions/messages 表，只通过 SessionManager
调用存储层。
"""

from src.models.schemas import Message, Session
from src.storage.base import StorageBackend


class SessionManager:
    """会话管理器。

    Step 8 完善会话 CRUD：新建、列表、加载、重命名、删除。
    搜索、导出等功能留到后续步骤。
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
        """查询当前用户的所有会话。

        SQLiteBackend 已按 updated_at 倒序返回；这里保留业务层入口，避免 TUI 直接依赖存储细节。
        """
        return await self.storage.list_sessions(user_id)

    async def get_session(self, session_id: int) -> Session | None:
        """根据 session_id 查询会话；找不到时返回 None。"""
        return await self.storage.get_session(session_id)

    async def get_messages(self, session_id: int) -> list[Message]:
        """查询指定会话的全部消息。"""
        return await self.storage.list_messages(session_id)

    async def rename_session(self, session_id: int, new_title: str) -> Session:
        """重命名会话。

        Args:
            session_id: 会话 ID。
            new_title: 新标题，不能为空。
        """
        cleaned_title = new_title.strip()
        if not cleaned_title:
            raise ValueError("会话标题不能为空。")

        session = await self.storage.update_session_title(session_id, cleaned_title)
        if session is None:
            raise ValueError(f"会话 ID {session_id} 不存在。")
        return session

    async def delete_session(self, session_id: int) -> None:
        """删除会话。

        该会话下的消息由 SQLite 外键 ON DELETE CASCADE 自动删除。
        """
        session = await self.storage.get_session(session_id)
        if session is None:
            raise ValueError(f"会话 ID {session_id} 不存在。")
        await self.storage.delete_session(session_id)

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

    async def search_messages(self, user_id: int, keyword: str) -> list[dict]:
        """搜索当前用户的历史消息。

        业务规则：关键词会自动去除首尾空格；关键词为空时不允许执行全量搜索。
        """
        cleaned_keyword = keyword.strip()
        if not cleaned_keyword:
            raise ValueError("搜索关键词不能为空。")
        return await self.storage.search_messages(user_id, cleaned_keyword)

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
        """根据首条用户消息自动生成会话标题。"""
        session = await self.storage.get_session(session_id)
        if session is None:
            return None

        if session.title and session.title != "新会话":
            return session

        title = first_message.strip().replace("\n", " ")[:30] or "新会话"
        return await self.storage.update_session_title(session_id, title)

