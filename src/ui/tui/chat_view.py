"""聊天视图占位模块。

Step 2 不实现真实聊天，也不调用 LangChain。
这里只提供一个占位函数，证明菜单可以跳转到“开始对话”入口。
"""

from src.ui.tui.widgets import print_info


async def show_chat_placeholder() -> None:
    """显示聊天功能占位提示。"""
    print_info("真实对话功能将在 Step 7 实现。")
