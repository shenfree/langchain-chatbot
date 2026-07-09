"""TUI 主菜单视图。"""

from src.ui.tui.widgets import console, print_blank_line, print_title


MENU_OPTIONS = {
    "1": "用户管理",
    "2": "会话管理",
    "3": "预设管理",
    "4": "开始对话",
    "5": "设置",
    "0": "退出程序",
}


def render_main_menu() -> None:
    """渲染主菜单。

    本函数只负责展示，不处理用户输入，输入逻辑由 TUIApp 统一管理。
    """
    print_blank_line()
    print_title("LangChain Chat")

    for key, label in MENU_OPTIONS.items():
        console.print(f"[bold]{key}.[/bold] {label}")

    print_blank_line()
