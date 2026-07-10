"""ChatEngine 独立测试脚本。"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.chat_engine import ChatEngine
from src.core.config_manager import ConfigManager
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
    """创建 ChatEngine，并执行一次流式模型调用。"""
    setup_logging(PROJECT_ROOT / "logging.yaml")
    logger.info("ChatEngine 测试开始")

    try:
        config_manager = ConfigManager(project_root=PROJECT_ROOT)
        engine = ChatEngine(
            config_manager=config_manager,
            system_prompt="你是一个简洁的中文助手。",
        )

        user_input = "请用一句话介绍 LangChain。"
        print(f"用户：{user_input}")
        print("助手：", end="", flush=True)

        async for text in engine.stream_chat(user_input):
            print(text, end="", flush=True)

        logger.info("ChatEngine 测试完成：model_name=%s input_length=%s", engine.model_name, len(user_input))
        print("\nChatEngine 测试完成")
    except Exception:
        logger.exception("ChatEngine 测试失败")
        raise


if __name__ == "__main__":
    asyncio.run(main())
