"""日志系统验证脚本。

运行方式：
    uv run python scripts/test_logging.py

验证内容：
- 初始化日志系统；
- 写入 info / warning / error 三种日志；
- 确认 logs/app.log 被创建。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logger import get_logger, setup_logging


def main() -> None:
    """执行日志系统最小验证。"""
    setup_logging(PROJECT_ROOT / "logging.yaml")
    logger = get_logger(__name__)

    logger.info("日志系统 info 测试")
    logger.warning("日志系统 warning 测试")
    logger.error("日志系统 error 测试")

    app_log = PROJECT_ROOT / "logs" / "app.log"
    if not app_log.exists():
        raise RuntimeError("logs/app.log 未创建，日志系统测试失败。")

    print("日志系统测试通过")


if __name__ == "__main__":
    main()
