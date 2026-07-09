"""TUI 输出小组件。

这里集中封装 rich 的 Console，避免每个界面文件都重复创建 Console。
后续如果要统一主题、颜色或日志输出，也可以从这里扩展。
"""

from rich.console import Console
from rich.panel import Panel

console = Console()


def print_title(title: str) -> None:
    """打印标题面板。"""
    console.print(Panel.fit(title, style="bold cyan"))


def print_info(message: str) -> None:
    """打印普通提示信息。"""
    console.print(f"[green]{message}[/green]")


def print_warning(message: str) -> None:
    """打印警告信息。"""
    console.print(f"[yellow]{message}[/yellow]")


def print_error(message: str) -> None:
    """打印错误信息。"""
    console.print(f"[red]{message}[/red]")


def print_blank_line() -> None:
    """打印空行，让菜单显示更清爽。"""
    console.print()
