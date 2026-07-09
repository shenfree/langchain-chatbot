"""用户管理业务逻辑。

本模块只处理用户相关业务规则，例如用户名校验、重复检查、当前用户状态维护。
TUI 不直接操作数据库，只通过 UserManager 调用存储层。
"""

from src.models.schemas import User
from src.storage.base import StorageBackend


class UserManager:
    """用户管理器。

    UserManager 位于 core 层，负责连接界面层和存储层：
    - 界面层只负责输入输出。
    - 存储层只负责数据读写。
    - 业务规则统一放在这里，避免散落在 TUI 代码中。
    """

    def __init__(self, storage: StorageBackend) -> None:
        """初始化用户管理器。

        Args:
            storage: 具体存储后端，例如 Step 3 实现的 SQLiteBackend。
        """
        self.storage = storage
        self._current_user: User | None = None

    async def create_user(self, username: str) -> User:
        """创建用户。

        业务规则：
        1. 自动去除用户名首尾空格。
        2. 用户名不能为空。
        3. 用户名不能重复。
        4. 通过存储层创建用户并返回 User 模型。
        """
        cleaned_username = username.strip()
        if not cleaned_username:
            raise ValueError("用户名不能为空。")

        existing_user = await self.storage.get_user_by_username(cleaned_username)
        if existing_user is not None:
            raise ValueError(f"用户 {cleaned_username} 已存在。")

        return await self.storage.create_user(cleaned_username)

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
        """切换当前用户。

        如果用户不存在，抛出 ValueError，让 TUI 层负责展示错误提示。
        """
        user = await self.get_user(username)
        if user is None:
            raise ValueError(f"用户 {username.strip()} 不存在。")

        self._current_user = user
        return user

    async def delete_user(self, username: str) -> None:
        """根据用户名删除用户。

        删除用户时，数据库外键会级联删除该用户关联的会话、消息和配置。
        如果删除的是当前用户，需要同步清空当前用户状态。
        """
        user = await self.get_user(username)
        if user is None:
            raise ValueError(f"用户 {username.strip()} 不存在。")

        if user.id is None:
            raise ValueError("用户 ID 为空，无法删除。")

        await self.storage.delete_user(user.id)

        if self._current_user is not None and self._current_user.id == user.id:
            self._current_user = None

    def get_current_user(self) -> User | None:
        """返回当前用户；尚未选择用户时返回 None。"""
        return self._current_user
