"""对话引擎核心模块。

ChatEngine 负责模型调用：读取模型配置、创建 ChatOpenAI、支持历史消息、system_prompt 和
异步流式输出。Step 10 增加了按 model_name 选择不同 OpenAI 兼容模型的能力。
"""

from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.core.config_manager import ConfigManager
from src.core.model_manager import ModelManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChatEngine:
    """LangChain Chat 的对话引擎。"""

    def __init__(
        self,
        config_manager: ConfigManager,
        system_prompt: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """初始化对话引擎。"""
        self.config_manager = config_manager
        self.default_system_prompt = system_prompt
        self.model_manager = ModelManager(config_manager)

        self.model_name = model_name or self.model_manager.get_current_model()
        model_config = self._resolve_model_config(self.model_name)
        self.api_base_url = self._resolve_base_url(model_config)
        self.api_key = self._resolve_api_key(model_config)

        config = self.config_manager.get_config()
        llm_config = config.get("llm", {})
        self.timeout = int(llm_config.get("timeout", 60))
        self.max_retries = int(llm_config.get("max_retries", 3))
        self.temperature = float(llm_config.get("temperature", 0.7))

        logger.info(
            "初始化 ChatEngine：model_name=%s timeout=%s max_retries=%s temperature=%s",
            self.model_name,
            self.timeout,
            self.max_retries,
            self.temperature,
        )

        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.api_base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            temperature=self.temperature,
            streaming=True,
        )

    async def stream_chat(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """异步流式调用模型，并逐块返回文本。"""
        cleaned_input = user_input.strip()
        if not cleaned_input:
            raise ValueError("用户输入不能为空。")

        history_count = len(history or [])
        logger.info(
            "模型调用开始：model_name=%s input_length=%s history_count=%s has_system_prompt=%s",
            self.model_name,
            len(cleaned_input),
            history_count,
            bool(system_prompt or self.default_system_prompt),
        )

        try:
            messages = self._build_messages(cleaned_input, history, system_prompt)
            chunk_count = 0
            async for chunk in self.llm.astream(messages):
                text = self._extract_chunk_text(chunk.content)
                if text:
                    chunk_count += 1
                    yield text
            logger.info("模型调用完成：model_name=%s chunk_count=%s", self.model_name, chunk_count)
        except Exception:
            logger.exception("模型调用失败：model_name=%s input_length=%s", self.model_name, len(cleaned_input))
            raise

    async def chat_once(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """一次性返回完整模型回复。"""
        parts: list[str] = []
        async for text in self.stream_chat(user_input, history, system_prompt):
            parts.append(text)
        return "".join(parts)

    def _resolve_model_config(self, model_name: str) -> dict[str, Any]:
        """解析模型配置；找不到时回退到旧版通用配置。"""
        try:
            return self.model_manager.get_model_config(model_name)
        except ValueError:
            logger.warning("模型配置未找到，使用旧版通用配置：model_name=%s", model_name)
            return {
                "name": model_name,
                "value": model_name,
                "provider": "legacy",
                "base_url": self.config_manager.get_env("API_BASE_URL", "https://api.deepseek.com/v1"),
                "env_key": "API_KEY",
            }

    def _resolve_base_url(self, model_config: dict[str, Any]) -> str:
        """解析当前模型 base_url。"""
        value = str(model_config.get("value", ""))
        if value == self.config_manager.get_env("MODEL_NAME", ""):
            return self.config_manager.get_env("API_BASE_URL", str(model_config.get("base_url", ""))) or ""
        return str(model_config.get("base_url") or self.config_manager.get_env("API_BASE_URL", ""))

    def _resolve_api_key(self, model_config: dict[str, Any]) -> str:
        """解析当前模型 API Key。"""
        env_key = str(model_config.get("env_key") or "API_KEY")
        value = self.config_manager.get_env(env_key)
        if value and value.strip():
            return value.strip()

        legacy_key = self.config_manager.get_env("API_KEY")
        if env_key == "API_KEY" and legacy_key and legacy_key.strip():
            return legacy_key.strip()

        logger.error("模型缺少 API Key 环境变量：model_name=%s env_key=%s", self.model_name, env_key)
        raise ValueError(f"当前模型 {self.model_name} 缺少环境变量 {env_key}，请在 .env 中配置。")

    def _build_messages(
        self,
        user_input: str,
        history: list[dict[str, str]] | None,
        system_prompt: str | None,
    ) -> list[BaseMessage]:
        """组装 LangChain 消息列表。"""
        messages: list[BaseMessage] = []
        active_system_prompt = system_prompt or self.default_system_prompt
        if active_system_prompt:
            messages.append(SystemMessage(content=active_system_prompt))

        for item in history or []:
            message = self._dict_to_message(item)
            if message is not None:
                messages.append(message)

        messages.append(HumanMessage(content=user_input))
        return messages

    def _dict_to_message(self, item: dict[str, str]) -> BaseMessage | None:
        """把字典消息转换为 LangChain 消息对象。"""
        role = self._normalize_role(item.get("role", ""))
        content = item.get("content", "").strip()
        if not role or not content:
            return None
        if role == "human":
            return HumanMessage(content=content)
        if role == "ai":
            return AIMessage(content=content)
        if role == "system":
            return SystemMessage(content=content)
        raise ValueError(f"不支持的消息角色：{item.get('role')}")

    @staticmethod
    def _normalize_role(role: str) -> str:
        """统一消息角色名称。"""
        role_mapping = {
            "human": "human",
            "user": "human",
            "ai": "ai",
            "assistant": "ai",
            "system": "system",
        }
        return role_mapping.get(role.strip().lower(), "")

    @staticmethod
    def _extract_chunk_text(content: Any) -> str:
        """从 LangChain 流式 chunk 中提取文本。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    value = item.get("text") or item.get("content")
                    if isinstance(value, str):
                        parts.append(value)
            return "".join(parts)
        return ""
