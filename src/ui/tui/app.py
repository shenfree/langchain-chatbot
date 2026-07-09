"""TUI 应用主程序。

本模块负责组织命令行界面的主循环：显示菜单、读取输入、分发到对应功能。
Step 5 接入预设 Prompt 管理；会话、LangChain 调用和真实聊天仍保持占位。
"""

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession

from src.core.config_manager import ConfigManager
from src.core.preset_manager import PresetManager
from src.core.user_manager import UserManager
from src.interface.ui_protocol import AbstractUI
from src.storage.base import StorageBackend
from src.storage.factory import StorageFactory
from src.ui.tui.chat_view import show_chat_placeholder
from src.ui.tui.menu_view import (
    MENU_OPTIONS,
    PRESET_MENU_OPTIONS,
    USER_MENU_OPTIONS,
    render_main_menu,
    render_preset_menu,
    render_user_menu,
)
from src.ui.tui.widgets import console, print_error, print_info, print_warning


class TUIApp(AbstractUI):
    """LangChain Chat 的 TUI 应用。"""

    def __init__(self, project_root: Path | None = None) -> None:
        """初始化 TUI 应用。"""
        self.project_root = project_root or Path.cwd()
        self.prompt_session: PromptSession | None = None
        self.is_running = True
        self.storage: StorageBackend | None = None
        self.user_manager: UserManager | None = None
        self.preset_manager: PresetManager | None = None

    async def run(self) -> None:
        """启动 TUI 主循环。"""
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
        self.preset_manager = PresetManager(self.storage, project_root=self.project_root)
        await self.preset_manager.load_builtin_presets()

    async def _close_services(self) -> None:
        """关闭应用持有的外部资源。"""
        if self.storage is not None:
            await self.storage.close()

    def _create_prompt_session(self) -> PromptSession | None:
        """创建 prompt_toolkit 输入会话。"""
        try:
            return PromptSession()
        except Exception:
            return None

    async def _prompt_text(self, message: str) -> str:
        """异步读取用户输入。"""
        if self.prompt_session is not None:
            return await self.prompt_session.prompt_async(message)
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
            await self.show_preset_menu()
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

    async def show_preset_menu(self) -> None:
        """显示并处理预设管理子菜单。"""
        while self.is_running:
            render_preset_menu()
            choice = (await self._prompt_text("请选择预设管理功能编号：")).strip()

            if choice == "0":
                return
            if choice == "1":
                await self.list_presets_flow()
            elif choice == "2":
                await self.create_preset_flow()
            elif choice == "3":
                await self.update_preset_flow()
            elif choice == "4":
                await self.delete_preset_flow()
            else:
                valid_options = "、".join(PRESET_MENU_OPTIONS.keys())
                print_error(f"无效输入：{choice or '空输入'}。请输入以下编号之一：{valid_options}")

    def _require_user_manager(self) -> UserManager:
        """获取用户管理器；如果未初始化则抛出错误。"""
        if self.user_manager is None:
            raise RuntimeError("用户管理器尚未初始化。")
        return self.user_manager

    def _require_preset_manager(self) -> PresetManager:
        """获取预设管理器；如果未初始化则抛出错误。"""
        if self.preset_manager is None:
            raise RuntimeError("预设管理器尚未初始化。")
        return self.preset_manager

    def _get_current_user_id(self) -> int | None:
        """获取当前用户 ID；尚未选择用户时返回 None。"""
        user = self._require_user_manager().get_current_user()
        return user.id if user is not None else None

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

    async def list_presets_flow(self) -> None:
        """查看预设列表的 TUI 流程。"""
        user_id = self._get_current_user_id()
        presets = await self._require_preset_manager().list_presets(user_id=user_id)
        if not presets:
            print_warning("暂无预设。")
            return

        console.print("[bold]预设列表：[/bold]")
        for preset in presets:
            preset_type = "系统内置" if preset.is_builtin else "个人预设"
            console.print(f"- ID: {preset.id} | 名称: {preset.name} | 类型: {preset_type}")
            console.print(f"  说明: {preset.description}")

    async def create_preset_flow(self) -> None:
        """新增个人预设的 TUI 流程。"""
        current_user = self._require_user_manager().get_current_user()
        if current_user is None or current_user.id is None:
            print_warning("请先选择当前用户，再新增个人预设。")
            return

        name = await self._prompt_text("请输入预设名称：")
        description = await self._prompt_text("请输入预设说明：")
        system_prompt = await self._prompt_text("请输入 system_prompt：")
        try:
            preset = await self._require_preset_manager().create_user_preset(
                user_id=current_user.id,
                name=name,
                description=description,
                system_prompt=system_prompt,
            )
            print_info(f"个人预设创建成功：{preset.name}，ID: {preset.id}")
        except ValueError as exc:
            print_error(str(exc))

    async def update_preset_flow(self) -> None:
        """编辑个人预设的 TUI 流程。"""
        if self._get_current_user_id() is None:
            print_warning("请先选择当前用户，再编辑个人预设。")
            return

        preset_id = await self._prompt_preset_id("请输入要编辑的 preset_id：")
        if preset_id is None:
            return

        name = await self._prompt_text("请输入新的预设名称：")
        description = await self._prompt_text("请输入新的预设说明：")
        system_prompt = await self._prompt_text("请输入新的 system_prompt：")
        try:
            preset = await self._require_preset_manager().update_user_preset(
                preset_id=preset_id,
                name=name,
                description=description,
                system_prompt=system_prompt,
            )
            print_info(f"个人预设更新成功：{preset.name}")
        except ValueError as exc:
            print_error(str(exc))

    async def delete_preset_flow(self) -> None:
        """删除个人预设的 TUI 流程。"""
        if self._get_current_user_id() is None:
            print_warning("请先选择当前用户，再删除个人预设。")
            return

        preset_id = await self._prompt_preset_id("请输入要删除的 preset_id：")
        if preset_id is None:
            return

        confirm = await self._prompt_text("确认删除该个人预设？输入 yes 确认：")
        if confirm.strip().lower() != "yes":
            print_warning("已取消删除。")
            return

        try:
            await self._require_preset_manager().delete_user_preset(preset_id)
            print_info(f"个人预设已删除，ID: {preset_id}")
        except ValueError as exc:
            print_error(str(exc))

    async def _prompt_preset_id(self, message: str) -> int | None:
        """读取并校验 preset_id。"""
        raw_value = (await self._prompt_text(message)).strip()
        try:
            return int(raw_value)
        except ValueError:
            print_error("preset_id 必须是数字。")
            return None

    async def show_stub(self, feature_name: str) -> None:
        """显示功能占位提示。"""
        print_warning(f"{feature_name} 功能将在后续步骤实现。")

    async def exit_app(self) -> None:
        """退出 TUI 应用。"""
        self.is_running = False
        print_info("程序已退出。")
