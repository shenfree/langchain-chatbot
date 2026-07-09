"""存储后端抽象接口。

Step 2 只定义存储层应该具备哪些能力，不实现任何真实数据库逻辑。
后续 SQLite、MySQL 或其他存储后端都可以实现这个抽象基类。
"""

from abc import ABC, abstractmethod

from src.models.schemas import Message, Preset, Session, User


class StorageBackend(ABC):
    """存储后端抽象基类。

    所有方法都使用 async/await 形式，保证项目从一开始就是异步架构。
    """

    @abstractmethod
    async def init_storage(self) -> None:
        """初始化存储资源。

        例如后续 SQLite 后端会在这里建立连接、创建表结构等。
        """

    @abstractmethod
    async def close(self) -> None:
        """关闭存储资源。

        例如关闭数据库连接，释放文件句柄等。
        """

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
    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """查询预设列表。

        user_id 为空时，可以返回内置预设；传入 user_id 时，可以返回该用户可用的预设。
        """
