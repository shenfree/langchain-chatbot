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

USER_MENU_OPTIONS = {
    "1": "创建用户",
    "2": "查看用户列表",
    "3": "切换用户",
    "4": "删除用户",
    "5": "查看当前用户",
    "0": "返回主菜单",
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


def render_user_menu() -> None:
    """渲染用户管理子菜单。

    这里只展示菜单项，不包含任何业务逻辑。
    """
    print_blank_line()
    print_title("用户管理")

    for key, label in USER_MENU_OPTIONS.items():
        console.print(f"[bold]{key}.[/bold] {label}")

    print_blank_line()
