"""TUI 主菜单视图。"""

from src.ui.tui.widgets import console, print_blank_line, print_title


MENU_OPTIONS = {
    "1": "用户管理",
    "2": "会话管理",
    "3": "预设管理",
    "4": "开始对话",
    "5": "设置",
    "6": "对话搜索",
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

SESSION_MENU_OPTIONS = {
    "1": "查看会话列表",
    "2": "加载历史会话继续对话",
    "3": "重命名会话",
    "4": "删除会话",
    "5": "新建会话并开始对话",
    "0": "返回主菜单",
}

PRESET_MENU_OPTIONS = {
    "1": "查看预设列表",
    "2": "新增个人预设",
    "3": "编辑个人预设",
    "4": "删除个人预设",
    "0": "返回主菜单",
}


def render_main_menu() -> None:
    """渲染主菜单。"""
    print_blank_line()
    print_title("LangChain Chat")
    for key, label in MENU_OPTIONS.items():
        console.print(f"[bold]{key}.[/bold] {label}")
    print_blank_line()


def render_user_menu() -> None:
    """渲染用户管理子菜单。"""
    print_blank_line()
    print_title("用户管理")
    for key, label in USER_MENU_OPTIONS.items():
        console.print(f"[bold]{key}.[/bold] {label}")
    print_blank_line()


def render_session_menu() -> None:
    """渲染会话管理子菜单。"""
    print_blank_line()
    print_title("会话管理")
    for key, label in SESSION_MENU_OPTIONS.items():
        console.print(f"[bold]{key}.[/bold] {label}")
    print_blank_line()


def render_preset_menu() -> None:
    """渲染预设管理子菜单。"""
    print_blank_line()
    print_title("预设管理")
    for key, label in PRESET_MENU_OPTIONS.items():
        console.print(f"[bold]{key}.[/bold] {label}")
    print_blank_line()

