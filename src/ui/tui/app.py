"""TUI 应用主程序。

本模块负责组织命令行界面的主循环：显示菜单、读取输入、分发到对应功能。
Step 2 中所有业务功能都还是 stub，占位提示即可。
"""

import asyncio

from prompt_toolkit import PromptSession

from src.interface.ui_protocol import AbstractUI
from src.ui.tui.chat_view import show_chat_placeholder
from src.ui.tui.menu_view import MENU_OPTIONS, render_main_menu
from src.ui.tui.widgets import print_error, print_info, print_warning


class TUIApp(AbstractUI):
    """LangChain Chat 的 TUI 应用。"""

    def __init__(self) -> None:
        """初始化 TUI 应用。

        这里不立即创建 PromptSession，而是在 run() 中延迟创建。
        这样在某些没有完整控制台的自动化验证环境中，也可以正常导入和测试菜单逻辑。
        """
        self.prompt_session: PromptSession | None = None
        self.is_running = True

    async def run(self) -> None:
        """启动 TUI 主循环。

        用户每次选择菜单项后，程序执行对应占位逻辑，然后回到主菜单。
        输入 0 时退出程序。
        """
        self.prompt_session = self._create_prompt_session()
        print_info("LangChain Chat 项目已启动。")

        while self.is_running:
            render_main_menu()
            choice = (await self._prompt_choice()).strip()
            await self.handle_choice(choice)

    def _create_prompt_session(self) -> PromptSession | None:
        """创建 prompt_toolkit 输入会话。

        在真实终端中会返回 PromptSession；如果当前环境没有标准控制台，返回 None，
        后续输入会自动退回到 Python 内置 input，方便自动化验证。
        """
        try:
            return PromptSession()
        except Exception:
            return None

    async def _prompt_choice(self) -> str:
        """异步读取用户输入。"""
        if self.prompt_session is not None:
            return await self.prompt_session.prompt_async("请选择功能编号：")

        # fallback 只用于没有完整控制台的环境；真实 TUI 仍优先使用 prompt_toolkit。
        return await asyncio.to_thread(input, "请选择功能编号：")

    async def handle_choice(self, choice: str) -> None:
        """根据用户输入分发菜单动作。"""
        if choice == "0":
            await self.exit_app()
        elif choice == "1":
            await self.show_stub("用户管理")
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

    async def show_stub(self, feature_name: str) -> None:
        """显示功能占位提示。

        Args:
            feature_name: 当前选择的功能名称。
        """
        print_warning(f"{feature_name} 功能将在后续步骤实现。")

    async def exit_app(self) -> None:
        """退出 TUI 应用。"""
        self.is_running = False
        print_info("程序已退出。")
