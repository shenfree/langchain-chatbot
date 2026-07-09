"""项目入口文件。

Step 2 开始，入口不再只打印文本，而是启动一个最小可交互 TUI 主菜单。
本步仍然不实现数据库、LangChain 调用或真实聊天功能。
"""

import asyncio
import sys
from pathlib import Path

# 当使用 `python src/main.py` 运行时，Python 默认只把 src 目录加入导入路径。
# 这里主动补充项目根目录，确保 `from src...` 形式的包导入始终可用。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.tui.app import TUIApp


async def main() -> None:
    """创建并运行 TUI 应用。"""
    app = TUIApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
