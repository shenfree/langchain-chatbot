"""TUI 应用主程序。

本模块负责组织命令行界面的主循环：显示菜单、读取输入、分发到对应功能。
Step 8 完善会话管理：列表、加载、重命名、删除，以及聊天循环中的 /load、/rename、/delete。
"""

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession

from src.core.chat_engine import ChatEngine
from src.core.config_manager import ConfigManager
from src.core.model_manager import ModelManager
from src.core.preset_manager import PresetManager
from src.core.session_manager import SessionManager
from src.core.user_manager import UserManager
from src.interface.ui_protocol import AbstractUI
from src.models.schemas import Preset, Session, User
from src.storage.base import StorageBackend
from src.storage.factory import StorageFactory
from src.ui.tui.chat_view import (
    render_chat_header,
    render_chat_help,
    render_loaded_session,
    render_new_session_created,
    render_preset_choices,
    render_search_results,
    render_sessions_table,
)
from src.ui.tui.menu_view import (
    MENU_OPTIONS,
    PRESET_MENU_OPTIONS,
    SESSION_MENU_OPTIONS,
    SETTING_MENU_OPTIONS,
    USER_MENU_OPTIONS,
    render_main_menu,
    render_preset_menu,
    render_session_menu,
    render_setting_menu,
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
        self.config_manager: ConfigManager | None = None
        self.storage: StorageBackend | None = None
        self.user_manager: UserManager | None = None
        self.preset_manager: PresetManager | None = None
        self.session_manager: SessionManager | None = None
        self.model_manager: ModelManager | None = None
        self.chat_engine: ChatEngine | None = None

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
        self.config_manager = ConfigManager(project_root=self.project_root)
        config = self.config_manager.get_config()
        self.storage = StorageFactory.create(config, project_root=self.project_root)
        await self.storage.init_storage()
        self.user_manager = UserManager(self.storage)
        self.preset_manager = PresetManager(self.storage, project_root=self.project_root)
        self.session_manager = SessionManager(self.storage)
        self.model_manager = ModelManager(self.config_manager)
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
        """异步读取用户输入。

        自动化管道输入结束时可能抛出 EOFError，这里返回 0 让当前菜单安全退出。
        """
        try:
            if self.prompt_session is not None:
                return await self.prompt_session.prompt_async(message)
            return await asyncio.to_thread(input, message)
        except EOFError:
            return "0"

    async def handle_choice(self, choice: str) -> None:
        """根据主菜单输入分发动作。"""
        if choice == "0":
            await self.exit_app()
        elif choice == "1":
            await self.show_user_menu()
        elif choice == "2":
            await self.show_session_menu()
        elif choice == "3":
            await self.show_preset_menu()
        elif choice == "4":
            await self.start_chat_flow()
        elif choice == "5":
            await self.show_setting_menu()
        elif choice == "6":
            await self.search_messages_flow()
        elif choice == "7":
            await self.export_session_flow()
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

    async def show_session_menu(self) -> None:
        """显示并处理会话管理子菜单。"""
        while self.is_running:
            render_session_menu()
            choice = (await self._prompt_text("请选择会话管理功能编号：")).strip()
            if choice == "0":
                return
            if choice == "1":
                await self.list_sessions_flow()
            elif choice == "2":
                await self.load_session_flow()
            elif choice == "3":
                await self.rename_session_flow()
            elif choice == "4":
                await self.delete_session_flow()
            elif choice == "5":
                await self.start_chat_flow()
            else:
                valid_options = "、".join(SESSION_MENU_OPTIONS.keys())
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

    async def start_chat_flow(self) -> None:
        """新建会话并开始对话。"""
        current_user = self._require_current_user()
        if current_user is None:
            return

        chat_engine = self._get_or_create_chat_engine()
        if chat_engine is None:
            return

        selected_preset = await self.select_preset_for_chat(current_user)
        session = await self._create_chat_session(current_user, chat_engine, selected_preset)
        render_new_session_created(session)
        render_chat_header(current_user.username, chat_engine.model_name, selected_preset)
        render_chat_help()
        await self.chat_loop(current_user, chat_engine, session, selected_preset)

    async def load_session_flow(self) -> None:
        """从会话管理菜单加载历史会话继续对话。"""
        current_user = self._require_current_user()
        if current_user is None:
            return

        session = await self.prompt_session_from_current_user(current_user)
        if session is None:
            return

        await self.continue_loaded_session(current_user, session)

    async def continue_loaded_session(self, current_user: User, session: Session) -> None:
        """加载已有会话并进入聊天循环。"""
        selected_preset = await self.get_session_preset(session)
        chat_engine = self._get_or_create_chat_engine(model_name=session.model_name)
        if chat_engine is None:
            return

        render_loaded_session(session, selected_preset)
        render_chat_header(current_user.username, session.model_name, selected_preset)
        render_chat_help()
        await self.chat_loop(current_user, chat_engine, session, selected_preset)

    async def select_preset_for_chat(self, current_user: User) -> Preset | None:
        """让用户为新会话选择预设。"""
        presets = await self._require_preset_manager().list_presets(user_id=current_user.id)
        render_preset_choices(presets)
        raw_value = (await self._prompt_text("请输入 preset_id，或直接回车跳过：")).strip()
        if not raw_value:
            return None

        try:
            preset_id = int(raw_value)
        except ValueError:
            print_warning("preset_id 不是数字，本次不使用预设。")
            return None

        preset = await self._require_preset_manager().get_preset(preset_id)
        if preset is None:
            print_warning("未找到该预设，本次不使用预设。")
            return None

        print_info(f"已选择预设：{preset.name}")
        return preset

    async def _create_chat_session(
        self,
        current_user: User,
        chat_engine: ChatEngine,
        selected_preset: Preset | None,
    ) -> Session:
        """创建一个新的聊天会话。"""
        if current_user.id is None:
            raise ValueError("当前用户 ID 为空，无法创建会话。")
        return await self._require_session_manager().create_session(
            user_id=current_user.id,
            title="新会话",
            model_name=chat_engine.model_name,
            preset_id=selected_preset.id if selected_preset else None,
        )

    async def chat_loop(
        self,
        current_user: User,
        chat_engine: ChatEngine,
        session: Session,
        selected_preset: Preset | None,
    ) -> None:
        """聊天循环，处理普通消息和聊天命令。"""
        active_session = session
        active_preset = selected_preset

        while self.is_running:
            user_input = (await self._prompt_text("\n你：")).strip()
            if not user_input:
                continue

            result = await self.handle_chat_command(
                command=user_input,
                current_user=current_user,
                chat_engine=chat_engine,
                current_session=active_session,
                selected_preset=active_preset,
            )
            if result["new_session"] is not None:
                active_session = result["new_session"]
            if result["new_preset"] is not None or result["preset_changed"]:
                active_preset = result["new_preset"]
            if result["new_engine"] is not None:
                chat_engine = result["new_engine"]
            if result["handled"]:
                if result["exit_chat"]:
                    return
                continue

            system_prompt = active_preset.system_prompt if active_preset else None
            await self.handle_chat_message(active_session, chat_engine, user_input, system_prompt)

    async def handle_chat_command(
        self,
        command: str,
        current_user: User,
        chat_engine: ChatEngine,
        current_session: Session,
        selected_preset: Preset | None,
    ) -> dict[str, object]:
        """处理聊天命令。"""
        result: dict[str, object] = {
            "handled": False,
            "exit_chat": False,
            "new_session": None,
            "new_preset": None,
            "new_engine": None,
            "preset_changed": False,
        }
        if not command.startswith("/"):
            return result

        result["handled"] = True
        if command == "/exit":
            print_info("已返回主菜单。")
            result["exit_chat"] = True
        elif command == "/help":
            render_chat_help()
        elif command == "/model":
            print_info(f"当前模型：{current_session.model_name}")
        elif command == "/sessions":
            await self.show_chat_sessions(current_user)
        elif command == "/new":
            new_session = await self._create_chat_session(current_user, chat_engine, selected_preset)
            render_new_session_created(new_session)
            result["new_session"] = new_session
        elif command == "/rename":
            renamed = await self.rename_specific_session(current_user, current_session)
            if renamed is not None:
                result["new_session"] = renamed
        elif command == "/delete":
            deleted = await self.delete_specific_session(current_user, current_session)
            if deleted:
                result["exit_chat"] = True
        elif command == "/search":
            await self.search_messages_flow()
        elif command == "/switch":
            switched = await self.switch_chat_model_flow(current_session)
            if switched is not None:
                result["new_session"] = switched["session"]
                result["new_engine"] = switched["engine"]
        elif command == "/export":
            await self.export_current_session(current_user, current_session)
        elif command == "/load":
            loaded_session = await self.prompt_session_from_current_user(current_user)
            if loaded_session is not None:
                loaded_preset = await self.get_session_preset(loaded_session)
                loaded_engine = self._get_or_create_chat_engine(model_name=loaded_session.model_name)
                if loaded_engine is not None:
                    render_loaded_session(loaded_session, loaded_preset)
                    result["new_session"] = loaded_session
                    result["new_preset"] = loaded_preset
                    result["new_engine"] = loaded_engine
                    result["preset_changed"] = True
        else:
            print_warning("未知命令，输入 /help 查看可用命令。")
        return result

    async def handle_chat_message(
        self,
        session: Session,
        chat_engine: ChatEngine,
        user_input: str,
        system_prompt: str | None,
    ) -> None:
        """处理一轮用户消息：保存 human、流式回复、保存 ai。"""
        if session.id is None:
            print_error("当前会话 ID 为空，无法保存消息。")
            return

        try:
            existing_messages = await self._require_session_manager().get_messages(session.id)
            is_first_user_message = not any(message.role == "human" for message in existing_messages)
            await self._require_session_manager().add_user_message(session.id, user_input)

            history = await self._require_session_manager().build_history(session.id)
            console.print("AI：", end="")
            ai_parts: list[str] = []
            async for chunk in chat_engine.stream_chat(
                user_input=user_input,
                history=history[:-1],
                system_prompt=system_prompt,
            ):
                ai_parts.append(chunk)
                console.print(chunk, end="")
            console.print()

            ai_content = "".join(ai_parts).strip()
            if ai_content:
                await self._require_session_manager().add_ai_message(session.id, ai_content)

            if is_first_user_message:
                await self._require_session_manager().auto_title_from_first_message(session.id, user_input)
        except Exception as exc:
            print_error(f"模型调用失败：{exc}")

    async def list_sessions_flow(self) -> None:
        """查看当前用户会话列表。"""
        current_user = self._require_current_user()
        if current_user is None:
            return
        await self.show_chat_sessions(current_user)

    async def search_messages_flow(self) -> None:
        """搜索当前用户历史消息。

        TUI 只负责读取关键词和展示结果；关键词校验和搜索逻辑由 SessionManager 完成。
        """
        current_user = self._require_current_user()
        if current_user is None:
            return

        keyword = await self._prompt_text("请输入搜索关键词：")
        try:
            results = await self._require_session_manager().search_messages(current_user.id, keyword)  # type: ignore[arg-type]
            render_search_results(results)
        except ValueError as exc:
            print_error(str(exc))

    async def rename_session_flow(self) -> None:
        """会话管理菜单中的重命名流程。"""
        current_user = self._require_current_user()
        if current_user is None:
            return
        session = await self.prompt_session_from_current_user(current_user)
        if session is None:
            return
        await self.rename_specific_session(current_user, session)

    async def delete_session_flow(self) -> None:
        """会话管理菜单中的删除流程。"""
        current_user = self._require_current_user()
        if current_user is None:
            return
        session = await self.prompt_session_from_current_user(current_user)
        if session is None:
            return
        await self.delete_specific_session(current_user, session)

    async def rename_specific_session(self, current_user: User, session: Session) -> Session | None:
        """重命名指定会话。"""
        if not self._session_belongs_to_user(session, current_user):
            print_error("该会话不属于当前用户。")
            return None
        new_title = await self._prompt_text("请输入新的会话标题：")
        try:
            renamed = await self._require_session_manager().rename_session(session.id, new_title)  # type: ignore[arg-type]
            print_info(f"会话已重命名：{renamed.title}")
            return renamed
        except ValueError as exc:
            print_error(str(exc))
            return None

    async def delete_specific_session(self, current_user: User, session: Session) -> bool:
        """删除指定会话。"""
        if not self._session_belongs_to_user(session, current_user):
            print_error("该会话不属于当前用户。")
            return False
        confirm = await self._prompt_text("确认删除该会话及其全部消息？输入 yes 确认：")
        if confirm.strip().lower() != "yes":
            print_warning("已取消删除。")
            return False
        try:
            await self._require_session_manager().delete_session(session.id)  # type: ignore[arg-type]
            print_info(f"会话已删除：ID={session.id}")
            return True
        except ValueError as exc:
            print_error(str(exc))
            return False

    async def prompt_session_from_current_user(self, current_user: User) -> Session | None:
        """展示当前用户会话列表，并让用户输入 session_id。"""
        await self.show_chat_sessions(current_user)
        raw_session_id = (await self._prompt_text("请输入 session_id：")).strip()
        try:
            session_id = int(raw_session_id)
        except ValueError:
            print_error("session_id 必须是数字。")
            return None

        session = await self._require_session_manager().get_session(session_id)
        if session is None:
            print_error(f"会话 ID {session_id} 不存在。")
            return None
        if not self._session_belongs_to_user(session, current_user):
            print_error("该会话不属于当前用户。")
            return None
        return session

    async def get_session_preset(self, session: Session) -> Preset | None:
        """读取会话关联的预设。"""
        if session.preset_id is None:
            return None
        return await self._require_preset_manager().get_preset(session.preset_id)

    async def show_chat_sessions(self, current_user: User) -> None:
        """显示当前用户会话列表。"""
        if current_user.id is None:
            print_warning("当前用户 ID 为空，无法查询会话。")
            return
        sessions = await self._require_session_manager().list_sessions(current_user.id)
        render_sessions_table(sessions)

    def _session_belongs_to_user(self, session: Session, current_user: User) -> bool:
        """校验会话是否属于当前用户。"""
        return current_user.id is not None and session.user_id == current_user.id

    def _require_current_user(self) -> User | None:
        """获取当前用户；未选择用户时给出提示。"""
        current_user = self._require_user_manager().get_current_user()
        if current_user is None or current_user.id is None:
            print_warning("请先在用户管理中创建并切换用户。")
            return None
        return current_user

    def _get_or_create_chat_engine(self, model_name: str | None = None) -> ChatEngine | None:
        """按需创建 ChatEngine。"""
        if self.chat_engine is not None and (model_name is None or self.chat_engine.model_name == model_name):
            return self.chat_engine
        try:
            active_model = model_name or self._require_model_manager().get_current_model()
            self.chat_engine = ChatEngine(
                config_manager=self._require_config_manager(),
                model_name=active_model,
            )
            return self.chat_engine
        except ValueError as exc:
            print_error(str(exc))
            return None

    def _require_config_manager(self) -> ConfigManager:
        """获取配置管理器。"""
        if self.config_manager is None:
            raise RuntimeError("配置管理器尚未初始化。")
        return self.config_manager

    def _require_user_manager(self) -> UserManager:
        """获取用户管理器。"""
        if self.user_manager is None:
            raise RuntimeError("用户管理器尚未初始化。")
        return self.user_manager

    def _require_preset_manager(self) -> PresetManager:
        """获取预设管理器。"""
        if self.preset_manager is None:
            raise RuntimeError("预设管理器尚未初始化。")
        return self.preset_manager

    def _require_session_manager(self) -> SessionManager:
        """获取会话管理器。"""
        if self.session_manager is None:
            raise RuntimeError("会话管理器尚未初始化。")
        return self.session_manager

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

    async def show_setting_menu(self) -> None:
        """显示并处理设置菜单。"""
        while self.is_running:
            render_setting_menu()
            choice = (await self._prompt_text("请选择设置功能编号：")).strip()
            if choice == "0":
                return
            if choice == "1":
                print_info(f"当前默认模型：{self._require_model_manager().get_current_model()}")
            elif choice == "2":
                self.render_available_models()
            elif choice == "3":
                model_config = await self.prompt_model_choice()
                if model_config is not None:
                    switched = self._require_model_manager().switch_model(str(model_config["value"]))
                    # 默认模型变化后清空 ChatEngine 缓存，后续新会话会使用新模型。
                    self.chat_engine = None
                    print_info(f"默认模型已切换为：{switched['value']}")
            else:
                valid_options = "、".join(SETTING_MENU_OPTIONS.keys())
                print_error(f"无效输入：{choice or '空输入'}。请输入以下编号之一：{valid_options}")

    def render_available_models(self) -> None:
        """展示 config.yaml 中配置的可用模型。"""
        models = self._require_model_manager().list_models()
        if not models:
            print_warning("暂无可用模型配置。")
            return
        console.print("[bold]可用模型：[/bold]")
        for index, model in enumerate(models, start=1):
            console.print(
                f"{index}. {model.get('name')} | {model.get('value')} | "
                f"provider={model.get('provider')} | env_key={model.get('env_key')}"
            )

    async def prompt_model_choice(self) -> dict | None:
        """提示用户按编号或模型名称选择模型。"""
        models = self._require_model_manager().list_models()
        if not models:
            print_warning("暂无可用模型配置。")
            return None
        self.render_available_models()
        raw_value = (await self._prompt_text("请输入模型编号或模型名称：")).strip()
        if not raw_value:
            print_warning("未输入模型。")
            return None
        if raw_value.isdigit():
            index = int(raw_value)
            if 1 <= index <= len(models):
                return models[index - 1]
            print_error("模型编号超出范围。")
            return None
        try:
            return self._require_model_manager().get_model_config(raw_value)
        except ValueError as exc:
            print_error(str(exc))
            return None

    async def switch_chat_model_flow(self, current_session: Session) -> dict | None:
        """切换当前会话使用的模型。"""
        model_config = await self.prompt_model_choice()
        if model_config is None or current_session.id is None:
            return None
        model_name = str(model_config["value"])
        try:
            engine = ChatEngine(config_manager=self._require_config_manager(), model_name=model_name)
            updated_session = await self._require_session_manager().update_session_model(
                current_session.id,
                model_name,
            )
            self.chat_engine = engine
            print_info(f"当前会话模型已切换为：{model_name}")
            return {"session": updated_session, "engine": engine}
        except ValueError as exc:
            print_error(str(exc))
            return None

    async def export_session_flow(self) -> None:
        """主菜单导出指定会话。"""
        current_user = self._require_current_user()
        if current_user is None:
            return
        session = await self.prompt_session_from_current_user(current_user)
        if session is None:
            return
        await self.export_current_session(current_user, session)

    async def export_current_session(self, current_user: User, session: Session) -> None:
        """导出当前会话为 Markdown 文件。"""
        if not self._session_belongs_to_user(session, current_user):
            print_error("该会话不属于当前用户。")
            return
        if session.id is None:
            print_error("当前会话 ID 为空，无法导出。")
            return
        try:
            path = await self._require_session_manager().export_session_to_markdown(
                session.id,
                current_user.username,
            )
            print_info(f"会话已导出：{path}")
        except ValueError as exc:
            print_error(str(exc))

    def _require_model_manager(self) -> ModelManager:
        """获取模型管理器。"""
        if self.model_manager is None:
            raise RuntimeError("模型管理器尚未初始化。")
        return self.model_manager
    async def show_stub(self, feature_name: str) -> None:
        """显示功能占位提示。"""
        print_warning(f"{feature_name} 功能将在后续步骤实现。")

    async def exit_app(self) -> None:
        """退出 TUI 应用。"""
        self.is_running = False
        print_info("程序已退出。")




