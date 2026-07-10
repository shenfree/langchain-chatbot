"""ChatEngine 单元测试。

这些测试不调用真实大模型，也不依赖真实 API Key。
"""

from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.core.chat_engine import ChatEngine
from src.core.config_manager import ConfigManager


class FakeChunk:
    """模拟 LangChain 流式返回的 chunk。"""

    def __init__(self, content: str) -> None:
        self.content = content


class FakeChatOpenAI:
    """模拟 ChatOpenAI，记录调用时收到的 messages。"""

    instances: list["FakeChatOpenAI"] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.messages = None
        self.instances.append(self)

    async def astream(self, messages):
        self.messages = messages
        yield FakeChunk("你好")
        yield FakeChunk("，测试成功")


@pytest.fixture
def temp_project_config(tmp_path: Path) -> Path:
    """创建只用于测试的临时 config.yaml，不读取项目真实 .env。"""
    config_text = """
models:
  default: fake-model
  available:
    - name: Fake Model
      value: fake-model
      provider: fake
      base_url: https://example.test/v1
      env_key: TEST_API_KEY
llm:
  timeout: 10
  max_retries: 1
  temperature: 0.1
"""
    (tmp_path / "config.yaml").write_text(config_text, encoding="utf-8")
    return tmp_path


def test_chat_engine_missing_api_key_raises_clear_error(
    temp_project_config: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """缺少模型 API Key 时，应给出包含环境变量名的错误。"""
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    config_manager = ConfigManager(project_root=temp_project_config)

    with pytest.raises(ValueError, match="TEST_API_KEY"):
        ChatEngine(config_manager=config_manager)


@pytest.mark.asyncio
async def test_chat_engine_builds_messages_and_streams_with_fake_model(
    temp_project_config: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """使用 fake model 验证消息组装和流式文本拼接。"""
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.setattr("src.core.chat_engine.ChatOpenAI", FakeChatOpenAI)
    FakeChatOpenAI.instances.clear()

    config_manager = ConfigManager(project_root=temp_project_config)
    engine = ChatEngine(config_manager=config_manager, system_prompt="默认系统提示")

    history = [
        {"role": "human", "content": "你好"},
        {"role": "ai", "content": "你好，有什么可以帮你？"},
        {"role": "system", "content": "历史系统消息"},
        {"role": "user", "content": "兼容 user 角色"},
        {"role": "assistant", "content": "兼容 assistant 角色"},
    ]
    reply = await engine.chat_once("请继续", history=history, system_prompt="本轮系统提示")

    assert reply == "你好，测试成功"
    fake_llm = FakeChatOpenAI.instances[-1]
    assert fake_llm.kwargs["model"] == "fake-model"
    assert fake_llm.kwargs["api_key"] == "fake-key"
    assert fake_llm.messages is not None
    assert isinstance(fake_llm.messages[0], SystemMessage)
    assert fake_llm.messages[0].content == "本轮系统提示"
    assert isinstance(fake_llm.messages[1], HumanMessage)
    assert isinstance(fake_llm.messages[2], AIMessage)
    assert isinstance(fake_llm.messages[3], SystemMessage)
    assert isinstance(fake_llm.messages[4], HumanMessage)
    assert isinstance(fake_llm.messages[5], AIMessage)
    assert isinstance(fake_llm.messages[-1], HumanMessage)
    assert fake_llm.messages[-1].content == "请继续"
