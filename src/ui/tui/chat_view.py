"""TUI 聊天视图。

本模块只负责聊天界面的展示，不负责业务规则。
真正的会话创建、消息保存、加载、重命名、删除、搜索、导出和模型调用分别由
SessionManager 与 ChatEngine 完成。
"""

from rich.table import Table

from src.models.schemas import Preset, Session
from src.ui.tui.widgets import console, print_blank_line, print_info, print_title, print_warning


def render_chat_help() -> None:
    """显示聊天命令帮助。"""
    print_title("聊天帮助")
    console.print("/exit     返回主菜单")
    console.print("/new      新建会话")
    console.print("/help     查看帮助")
    console.print("/model    查看当前模型")
    console.print("/sessions 查看当前用户会话列表")
    console.print("/rename   重命名当前会话")
    console.print("/delete   删除当前会话并返回主菜单")
    console.print("/load     加载历史会话继续对话")
    console.print("/search   搜索当前用户历史消息")
    console.print("/switch   切换当前会话模型")
    console.print("/export   导出当前会话为 Markdown")


def render_chat_header(username: str, model_name: str, preset: Preset | None) -> None:
    """显示聊天界面头部信息。"""
    preset_name = preset.name if preset else "未使用预设"
    print_blank_line()
    print_title("开始对话")
    print_info(f"当前用户：{username}")
    print_info(f"当前模型：{model_name}")
    print_info(f"当前预设：{preset_name}")
    print_warning("输入 /help 查看可用命令，输入 /exit 返回主菜单。")


def render_preset_choices(presets: list[Preset]) -> None:
    """显示可选预设列表。"""
    print_title("选择预设")
    if not presets:
        print_warning("暂无可用预设，直接回车将不使用预设。")
        return

    console.print("可用预设：")
    for preset in presets:
        preset_type = "系统内置" if preset.is_builtin else "个人预设"
        console.print(f"- ID: {preset.id} | {preset.name} | {preset_type} | {preset.description}")
    console.print("直接回车：不使用预设")


def render_sessions_table(sessions: list[Session]) -> None:
    """显示当前用户的会话列表。"""
    if not sessions:
        print_warning("当前用户暂无会话。")
        return

    print_title("当前用户会话列表")
    console.print("ID | 标题 | 模型 | 预设ID | 创建时间 | 更新时间 | 总token")
    for session in sessions:
        total_tokens = session.total_prompt_tokens + session.total_completion_tokens
        console.print(
            f"{session.id} | {session.title} | {session.model_name} | "
            f"{session.preset_id or '-'} | {session.created_at} | {session.updated_at} | {total_tokens}"
        )


def render_new_session_created(session: Session) -> None:
    """提示新会话已创建。"""
    print_info(f"已创建新会话：ID={session.id}，标题={session.title}")


def render_loaded_session(session: Session, preset: Preset | None) -> None:
    """提示历史会话已加载。"""
    preset_name = preset.name if preset else "未使用预设"
    print_info(f"已加载会话：ID={session.id}，标题={session.title}，预设：{preset_name}")


def render_search_results(results: list[dict]) -> None:
    """使用 rich Table 展示搜索结果。"""
    if not results:
        print_warning("未找到匹配的历史消息。")
        return

    table = Table(title="对话搜索结果")
    table.add_column("序号", justify="right")
    table.add_column("会话 ID", justify="right")
    table.add_column("会话标题")
    table.add_column("角色")
    table.add_column("命中内容")
    table.add_column("时间")

    for index, item in enumerate(results, start=1):
        content = str(item.get("content", "")).replace("\n", " ").strip()
        if len(content) > 80:
            content = content[:80] + "..."
        table.add_row(
            str(index),
            str(item.get("session_id", "")),
            str(item.get("session_title", "")),
            str(item.get("role", "")),
            content,
            str(item.get("created_at", "")),
        )

    console.print(table)
