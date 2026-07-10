"""FileBackend 冒烟测试脚本。

运行方式：
    uv run python scripts/test_file_backend.py

说明：
- 如果 config.yaml 中 storage.type 不是 file，本脚本会直接跳过。
- 如果 storage.type=file，会创建临时用户、会话、消息和预设，验证基本功能。
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 使用脚本方式运行时补充项目根目录，确保可以导入 src 包。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config_manager import ConfigManager
from src.storage.factory import StorageFactory


async def main() -> None:
    """执行 FileBackend 最小闭环测试。"""
    config_manager = ConfigManager(project_root=PROJECT_ROOT)
    config = config_manager.get_config()
    storage_config = config.get("storage", {})
    storage_type = storage_config.get("type", "sqlite")

    if storage_type != "file":
        print("当前 storage.type 不是 file，跳过 FileBackend 冒烟测试。")
        return

    storage = StorageFactory.create(config, project_root=PROJECT_ROOT)
    await storage.init_storage()

    username = f"file_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        # 1. 创建或获取用户。
        user = await storage.get_user_by_username(username)
        if user is None:
            user = await storage.create_user(username)
        if user.id is None:
            raise RuntimeError("测试用户没有 ID。")

        # 2. 创建会话并保存消息。
        session = await storage.create_session(
            user_id=user.id,
            title="FileBackend 冒烟测试会话",
            model_name="test-model",
        )
        if session.id is None:
            raise RuntimeError("测试会话没有 ID。")

        await storage.add_message(session.id, "human", "FileBackend 冒烟测试 keyword-step12")
        await storage.add_message(session.id, "ai", "收到，FileBackend 文件存储工作正常。")

        messages = await storage.list_messages(session.id)
        if len(messages) < 2:
            raise RuntimeError("没有查询到完整的测试消息。")

        # 3. 创建个人预设 Prompt，并验证可以查询到。
        preset = await storage.create_preset(
            user_id=user.id,
            name="FileBackend 测试预设",
            description="用于 Step 12 文件后端冒烟测试",
            system_prompt="你是 FileBackend 测试助手。",
            is_builtin=False,
        )
        if preset.id is None:
            raise RuntimeError("测试预设没有 ID。")

        presets = await storage.list_presets(user.id)
        if not any(item.id == preset.id for item in presets):
            raise RuntimeError("没有查询到刚创建的测试预设。")

        # 4. 搜索当前用户历史消息，验证不会依赖数据库 JOIN 也能工作。
        results = await storage.search_messages(user.id, "keyword-step12")
        if not results:
            raise RuntimeError("搜索没有命中刚写入的测试消息。")

        # 5. 清理临时用户，FileBackend 会手动级联删除关联数据。
        await storage.delete_user(user.id)
        print("FileBackend 冒烟测试通过")
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
