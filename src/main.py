"""项目入口文件。

入口负责初始化日志系统、创建 TUIApp，并把项目根目录传给应用。
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
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
    """创建并运行 TUI 应用。"""
    setup_logging(PROJECT_ROOT / "logging.yaml")
    logger.info("应用启动")
    app = TUIApp(project_root=PROJECT_ROOT)
    await app.run()
    logger.info("应用退出")


if __name__ == "__main__":
    asyncio.run(main())
