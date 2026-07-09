"""ChatEngine 独立测试脚本。

运行方式：
    uv run python scripts/test_chat_engine.py

本脚本只用于测试 Step 6 的 ChatEngine，不接入 TUI，不创建会话，也不写聊天记录。
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.chat_engine import ChatEngine
from src.core.config_manager import ConfigManager


async def main() -> None:
    """创建 ChatEngine，并执行一次流式模型调用。"""
    config_manager = ConfigManager(project_root=PROJECT_ROOT)
    engine = ChatEngine(
        config_manager=config_manager,
        system_prompt="你是一个简洁的中文助手。",
    )

    print("用户：请用一句话介绍 LangChain。")
    print("助手：", end="", flush=True)

    async for text in engine.stream_chat("请用一句话介绍 LangChain。"):
        print(text, end="", flush=True)

    print("\nChatEngine 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
