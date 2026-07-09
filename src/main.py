"""项目入口文件。

Step 4 中，入口负责创建 TUIApp，并把项目根目录传给应用。
本步只实现用户管理，不实现预设管理、会话管理、LangChain 调用或真实聊天。
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
    app = TUIApp(project_root=PROJECT_ROOT)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
