"""会话管理业务逻辑。

本模块负责会话创建、消息保存、历史消息组装、搜索、模型名更新，以及 Markdown 导出。
TUI 不直接操作 sessions/messages 表，只通过 SessionManager 调用存储层。
"""

import re
from datetime import datetime
from pathlib import Path

from src.models.schemas import Message, Session
from src.storage.base import StorageBackend
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """会话管理器。"""

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
        session = await self.storage.create_session(user_id, title, model_name, preset_id)
        logger.info(
            "会话创建成功：user_id=%s session_id=%s model_name=%s preset_id=%s",
            user_id,
            session.id,
            model_name,
            preset_id,
        )
        return session

    async def list_sessions(self, user_id: int) -> list[Session]:
        """查询当前用户的所有会话。"""
        return await self.storage.list_sessions(user_id)

    async def get_session(self, session_id: int) -> Session | None:
        """根据 session_id 查询会话；找不到时返回 None。"""
        return await self.storage.get_session(session_id)

    async def get_messages(self, session_id: int) -> list[Message]:
        """查询指定会话的全部消息。"""
        return await self.storage.list_messages(session_id)

    async def rename_session(self, session_id: int, new_title: str) -> Session:
        """重命名会话。"""
        cleaned_title = new_title.strip()
        if not cleaned_title:
            raise ValueError("会话标题不能为空。")
        session = await self.storage.update_session_title(session_id, cleaned_title)
        if session is None:
            raise ValueError(f"会话 ID {session_id} 不存在。")
        logger.info("会话重命名成功：session_id=%s title_length=%s", session_id, len(cleaned_title))
        return session

    async def update_session_model(self, session_id: int, model_name: str) -> Session:
        """更新会话使用的模型名。"""
        cleaned_model = model_name.strip()
        if not cleaned_model:
            raise ValueError("模型名称不能为空。")
        session = await self.storage.update_session_model(session_id, cleaned_model)
        if session is None:
            raise ValueError(f"会话 ID {session_id} 不存在。")
        logger.info("会话模型更新成功：session_id=%s model_name=%s", session_id, cleaned_model)
        return session

    async def delete_session(self, session_id: int) -> None:
        """删除会话，消息由存储后端级联删除。"""
        session = await self.storage.get_session(session_id)
        if session is None:
            raise ValueError(f"会话 ID {session_id} 不存在。")
        await self.storage.delete_session(session_id)
        logger.info("会话删除成功：session_id=%s user_id=%s", session_id, session.user_id)

    async def add_user_message(self, session_id: int, content: str) -> Message:
        """保存 human 消息。"""
        cleaned_content = content.strip()
        if not cleaned_content:
            raise ValueError("消息内容不能为空。")
        message = await self.storage.add_message(session_id, "human", cleaned_content)
        logger.debug("用户消息已保存：session_id=%s message_length=%s", session_id, len(cleaned_content))
        return message

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
        message = await self.storage.add_message(
            session_id,
            "ai",
            cleaned_content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        logger.debug(
            "AI 消息已保存：session_id=%s message_length=%s prompt_tokens=%s completion_tokens=%s",
            session_id,
            len(cleaned_content),
            prompt_tokens,
            completion_tokens,
        )
        return message

    async def search_messages(self, user_id: int, keyword: str) -> list[dict]:
        """搜索当前用户的历史消息。"""
        cleaned_keyword = keyword.strip()
        if not cleaned_keyword:
            raise ValueError("搜索关键词不能为空。")
        results = await self.storage.search_messages(user_id, cleaned_keyword)
        logger.info("历史消息搜索完成：user_id=%s keyword_length=%s result_count=%s", user_id, len(cleaned_keyword), len(results))
        return results

    async def build_history(self, session_id: int) -> list[dict[str, str]]:
        """把数据库消息转换成 ChatEngine 接收的历史格式。"""
        messages = await self.get_messages(session_id)
        history: list[dict[str, str]] = []
        for message in messages:
            if message.role in {"human", "ai", "system"}:
                history.append({"role": message.role, "content": message.content})
        logger.debug("会话历史已构建：session_id=%s history_count=%s", session_id, len(history))
        return history

    async def auto_title_from_first_message(self, session_id: int, first_message: str) -> Session | None:
        """根据首条用户消息自动生成会话标题。"""
        session = await self.storage.get_session(session_id)
        if session is None:
            return None
        if session.title and session.title != "新会话":
            return session
        title = first_message.strip().replace("\n", " ")[:30] or "新会话"
        updated = await self.storage.update_session_title(session_id, title)
        logger.info("会话标题自动生成：session_id=%s title_length=%s", session_id, len(title))
        return updated

    async def export_session_to_markdown(
        self,
        session_id: int,
        username: str,
        export_dir_template: str = "data/users/{username}/exports",
    ) -> Path:
        """将指定会话导出为 Markdown 文件。"""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"会话 ID {session_id} 不存在。")

        messages = await self.get_messages(session_id)
        export_dir = Path(export_dir_template.format(username=self._safe_filename(username)))
        export_dir.mkdir(parents=True, exist_ok=True)

        title = session.title or "未命名会话"
        date_text = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_name = f"{self._safe_filename(title)}-{date_text}.md"
        export_path = export_dir / file_name

        content = self._build_markdown_content(session, username, messages)
        export_path.write_text(content, encoding="utf-8")
        logger.info("会话导出完成：session_id=%s message_count=%s export_path=%s", session_id, len(messages), export_path)
        return export_path

    def _build_markdown_content(self, session: Session, username: str, messages: list[Message]) -> str:
        """生成 Markdown 文本内容。"""
        lines = [
            f"# {session.title}",
            "",
            f"- 会话 ID：{session.id}",
            f"- 用户：{username}",
            f"- 模型：{session.model_name}",
            f"- 预设 ID：{session.preset_id or '-'}",
            f"- 创建时间：{session.created_at}",
            f"- 更新时间：{session.updated_at}",
            "",
            "---",
            "",
            "## 对话记录",
            "",
        ]

        role_titles = {"human": "Human", "ai": "AI", "system": "System"}
        for message in messages:
            role_title = role_titles.get(message.role, message.role)
            lines.extend([f"### {role_title}", message.content, ""])
        return "\n".join(lines)

    @staticmethod
    def _safe_filename(value: str) -> str:
        """清洗 Windows 文件名非法字符。"""
        cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value.strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        return cleaned[:80] or "untitled"
