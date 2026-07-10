"""用户管理业务逻辑。

本模块只处理用户相关业务规则，例如用户名校验、重复检查、当前用户状态维护。
TUI 不直接操作数据库，只通过 UserManager 调用存储层。
"""

from src.models.schemas import User
from src.storage.base import StorageBackend
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserManager:
    """用户管理器。"""

    def __init__(self, storage: StorageBackend) -> None:
        """初始化用户管理器。"""
        self.storage = storage
        self._current_user: User | None = None

    async def create_user(self, username: str) -> User:
        """创建用户。"""
        cleaned_username = username.strip()
        if not cleaned_username:
            raise ValueError("用户名不能为空。")

        existing_user = await self.storage.get_user_by_username(cleaned_username)
        if existing_user is not None:
            raise ValueError(f"用户 {cleaned_username} 已存在。")

        user = await self.storage.create_user(cleaned_username)
        logger.info("用户创建成功：user_id=%s username=%s", user.id, user.username)
        return user

    async def list_users(self) -> list[User]:
        """返回所有用户。"""
        return await self.storage.list_users()

    async def get_user(self, username: str) -> User | None:
        """根据用户名查询用户；找不到时返回 None。"""
        cleaned_username = username.strip()
        if not cleaned_username:
            return None
        return await self.storage.get_user_by_username(cleaned_username)

    async def switch_user(self, username: str) -> User:
        """切换当前用户。"""
        user = await self.get_user(username)
        if user is None:
            raise ValueError(f"用户 {username.strip()} 不存在。")

        self._current_user = user
        logger.info("当前用户切换成功：user_id=%s username=%s", user.id, user.username)
        return user

    async def delete_user(self, username: str) -> None:
        """根据用户名删除用户。"""
        user = await self.get_user(username)
        if user is None:
            raise ValueError(f"用户 {username.strip()} 不存在。")

        if user.id is None:
            raise ValueError("用户 ID 为空，无法删除。")

        await self.storage.delete_user(user.id)
        logger.info("用户删除成功：user_id=%s username=%s", user.id, user.username)

        if self._current_user is not None and self._current_user.id == user.id:
            self._current_user = None

    def get_current_user(self) -> User | None:
        """返回当前用户；尚未选择用户时返回 None。"""
        return self._current_user
