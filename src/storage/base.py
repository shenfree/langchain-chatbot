"""存储后端抽象接口。

本模块只定义存储层能力，不绑定具体数据库实现。
SQLite、MySQL 或其他存储后端都应该实现这个抽象基类。
"""

from abc import ABC, abstractmethod

from src.models.schemas import Message, Preset, Session, User


class StorageBackend(ABC):
    """存储后端抽象基类。

    所有方法都使用 async/await 形式，保证项目从一开始就是异步架构。
    """

    @abstractmethod
    async def init_storage(self) -> None:
        """初始化存储资源。"""

    @abstractmethod
    async def close(self) -> None:
        """关闭存储资源。"""

    @abstractmethod
    async def create_user(self, username: str) -> User:
        """创建用户并返回用户对象。"""

    @abstractmethod
    async def get_user_by_username(self, username: str) -> User | None:
        """根据用户名查询用户；不存在时返回 None。"""

    @abstractmethod
    async def list_users(self) -> list[User]:
        """查询所有用户。"""

    @abstractmethod
    async def delete_user(self, user_id: int) -> None:
        """删除指定用户。"""

    @abstractmethod
    async def create_session(
        self,
        user_id: int,
        title: str,
        model_name: str,
        preset_id: int | None = None,
    ) -> Session:
        """创建会话并返回会话对象。"""

    @abstractmethod
    async def list_sessions(self, user_id: int) -> list[Session]:
        """查询指定用户的所有会话。"""

    @abstractmethod
    async def get_session(self, session_id: int) -> Session | None:
        """根据会话 ID 查询会话；不存在时返回 None。"""

    @abstractmethod
    async def update_session_title(self, session_id: int, title: str) -> Session | None:
        """更新会话标题，并返回更新后的会话；不存在时返回 None。"""

    @abstractmethod
    async def delete_session(self, session_id: int) -> None:
        """删除指定会话。"""

    @abstractmethod
    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Message:
        """向会话中追加一条消息。"""

    @abstractmethod
    async def list_messages(self, session_id: int) -> list[Message]:
        """查询指定会话的全部消息。"""

    @abstractmethod
    async def search_messages(self, user_id: int, keyword: str) -> list[dict]:
        """在指定用户的所有历史消息中搜索关键词。"""

    @abstractmethod
    async def create_preset(
        self,
        user_id: int | None,
        name: str,
        description: str,
        system_prompt: str,
        is_builtin: bool = False,
    ) -> Preset:
        """创建预设 Prompt。"""

    @abstractmethod
    async def get_preset(self, preset_id: int) -> Preset | None:
        """根据 ID 查询预设；不存在时返回 None。"""

    @abstractmethod
    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """查询预设列表。"""

    @abstractmethod
    async def update_preset(
        self,
        preset_id: int,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Preset:
        """更新非内置预设。"""

    @abstractmethod
    async def delete_preset(self, preset_id: int) -> None:
        """删除非内置预设。"""

