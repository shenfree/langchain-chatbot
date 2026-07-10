"""MySQL 存储后端冒烟测试脚本。"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config_manager import ConfigManager
from src.storage.factory import StorageFactory
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
    """执行 MySQLBackend 最小闭环测试。"""
    setup_logging(PROJECT_ROOT / "logging.yaml")
    logger.info("MySQLBackend 冒烟测试开始")

    config_manager = ConfigManager(project_root=PROJECT_ROOT)
    config = config_manager.get_config()
    storage_config = config.get("storage", {})
    storage_type = storage_config.get("type", "sqlite")

    if storage_type != "mysql":
        logger.warning("跳过 MySQLBackend 冒烟测试：storage_type=%s", storage_type)
        print("当前 storage.type 不是 mysql，跳过 MySQLBackend 冒烟测试。")
        return

    storage = StorageFactory.create(config, project_root=PROJECT_ROOT)
    await storage.init_storage()

    username = f"mysql_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        user = await storage.create_user(username)
        if user.id is None:
            raise RuntimeError("创建用户后没有返回用户 ID。")

        session = await storage.create_session(
            user_id=user.id,
            title="MySQL 冒烟测试会话",
            model_name="test-model",
        )
        if session.id is None:
            raise RuntimeError("创建会话后没有返回会话 ID。")

        await storage.add_message(session.id, "human", "MySQLBackend 冒烟测试 keyword-step11")
        await storage.add_message(session.id, "ai", "收到，MySQL 存储后端工作正常。")

        sessions = await storage.list_sessions(user.id)
        messages = await storage.list_messages(session.id)
        results = await storage.search_messages(user.id, "keyword-step11")

        if not sessions:
            raise RuntimeError("没有查询到测试会话。")
        if len(messages) < 2:
            raise RuntimeError("没有查询到完整的测试消息。")
        if not results:
            raise RuntimeError("搜索没有命中刚写入的测试消息。")

        await storage.delete_user(user.id)
        logger.info("MySQLBackend 冒烟测试通过：user_id=%s session_id=%s", user.id, session.id)
        print("MySQLBackend 冒烟测试通过")
    except Exception:
        logger.exception("MySQLBackend 冒烟测试失败")
        raise
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
