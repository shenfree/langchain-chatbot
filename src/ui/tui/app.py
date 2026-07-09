"""TUI 应用主程序。

本模块负责组织命令行界面的主循环：显示菜单、读取输入、分发到对应功能。
Step 4 只接入用户管理菜单，其余功能仍保持占位。
"""

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession

from src.core.config_manager import ConfigManager
from src.core.user_manager import UserManager
from src.interface.ui_protocol import AbstractUI
from src.storage.base import StorageBackend
from src.storage.factory import StorageFactory
from src.ui.tui.chat_view import show_chat_placeholder
from src.ui.tui.menu_view import MENU_OPTIONS, USER_MENU_OPTIONS, render_main_menu, render_user_menu
from src.ui.tui.widgets import console, print_error, print_info, print_warning


class TUIApp(AbstractUI):
    """LangChain Chat 的 TUI 应用。"""

    def __init__(self, project_root: Path | None = None) -> None:
        """初始化 TUI 应用。

        Args:
            project_root: 项目根目录。为空时使用当前工作目录，适合从项目根目录运行。
        """
        self.project_root = project_root or Path.cwd()
        self.prompt_session: PromptSession | None = None
        self.is_running = True
        self.storage: StorageBackend | None = None
        self.user_manager: UserManager | None = None

    async def run(self) -> None:
        """启动 TUI 主循环。

        启动时初始化存储和用户管理器；退出时关闭存储资源。
        """
        self.prompt_session = self._create_prompt_session()
        await self._setup_services()
        print_info("LangChain Chat 项目已启动。")

        try:
            while self.is_running:
                render_main_menu()
                choice = (await self._prompt_text("请选择功能编号：")).strip()
                await self.handle_choice(choice)
        finally:
            await self._close_services()

    async def _setup_services(self) -> None:
        """初始化配置、存储和业务管理器。"""
        config_manager = ConfigManager(project_root=self.project_root)
        config = config_manager.get_config()
        self.storage = StorageFactory.create(config, project_root=self.project_root)
        await self.storage.init_storage()
        self.user_manager = UserManager(self.storage)

    async def _close_services(self) -> None:
        """关闭应用持有的外部资源。"""
        if self.storage is not None:
            await self.storage.close()

    def _create_prompt_session(self) -> PromptSession | None:
        """创建 prompt_toolkit 输入会话。

        在真实终端中会返回 PromptSession；如果当前环境没有标准控制台，返回 None，
        后续输入会自动退回到 Python 内置 input，方便自动化验证。
        """
        try:
            return PromptSession()
        except Exception:
            return None

    async def _prompt_text(self, message: str) -> str:
        """异步读取用户输入。"""
        if self.prompt_session is not None:
            return await self.prompt_session.prompt_async(message)

        # fallback 只用于没有完整控制台的环境；真实 TUI 仍优先使用 prompt_toolkit。
        return await asyncio.to_thread(input, message)

    async def handle_choice(self, choice: str) -> None:
        """根据主菜单输入分发动作。"""
        if choice == "0":
            await self.exit_app()
        elif choice == "1":
            await self.show_user_menu()
        elif choice == "2":
            await self.show_stub("会话管理")
        elif choice == "3":
            await self.show_stub("预设管理")
        elif choice == "4":
            await show_chat_placeholder()
        elif choice == "5":
            await self.show_stub("设置")
        else:
            valid_options = "、".join(MENU_OPTIONS.keys())
            print_error(f"无效输入：{choice or '空输入'}。请输入以下编号之一：{valid_options}")

    async def show_user_menu(self) -> None:
        """显示并处理用户管理子菜单。"""
        while self.is_running:
            render_user_menu()
            choice = (await self._prompt_text("请选择用户管理功能编号：")).strip()

            if choice == "0":
                return
            if choice == "1":
                await self.create_user_flow()
            elif choice == "2":
                await self.list_users_flow()
            elif choice == "3":
                await self.switch_user_flow()
            elif choice == "4":
                await self.delete_user_flow()
            elif choice == "5":
                await self.show_current_user_flow()
            else:
                valid_options = "、".join(USER_MENU_OPTIONS.keys())
                print_error(f"无效输入：{choice or '空输入'}。请输入以下编号之一：{valid_options}")

    def _require_user_manager(self) -> UserManager:
        """获取用户管理器；如果未初始化则抛出错误。"""
        if self.user_manager is None:
            raise RuntimeError("用户管理器尚未初始化。")
        return self.user_manager

    async def create_user_flow(self) -> None:
        """创建用户的 TUI 流程。"""
        username = await self._prompt_text("请输入用户名：")
        try:
            user = await self._require_user_manager().create_user(username)
            print_info(f"用户创建成功：{user.username}")
        except ValueError as exc:
            print_error(str(exc))

    async def list_users_flow(self) -> None:
        """查看用户列表的 TUI 流程。"""
        users = await self._require_user_manager().list_users()
        if not users:
            print_warning("暂无用户。")
            return

        console.print("[bold]用户列表：[/bold]")
        for user in users:
            console.print(f"- {user.username}")

    async def switch_user_flow(self) -> None:
        """切换当前用户的 TUI 流程。"""
        username = await self._prompt_text("请输入要切换的用户名：")
        try:
            user = await self._require_user_manager().switch_user(username)
            print_info(f"当前用户已切换为：{user.username}")
        except ValueError as exc:
            print_error(str(exc))

    async def delete_user_flow(self) -> None:
        """删除用户的 TUI 流程。"""
        username = await self._prompt_text("请输入要删除的用户名：")
        confirm = await self._prompt_text("确认删除该用户及其关联数据？输入 yes 确认：")
        if confirm.strip().lower() != "yes":
            print_warning("已取消删除。")
            return

        try:
            await self._require_user_manager().delete_user(username)
            print_info(f"用户已删除：{username.strip()}")
        except ValueError as exc:
            print_error(str(exc))

    async def show_current_user_flow(self) -> None:
        """查看当前用户的 TUI 流程。"""
        user = self._require_user_manager().get_current_user()
        if user is None:
            print_warning("尚未选择用户。")
            return

        print_info(f"当前用户：{user.username}")

    async def show_stub(self, feature_name: str) -> None:
        """显示功能占位提示。"""
        print_warning(f"{feature_name} 功能将在后续步骤实现。")

    async def exit_app(self) -> None:
        """退出 TUI 应用。"""
        self.is_running = False
        print_info("程序已退出。")
