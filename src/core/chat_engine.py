"""对话引擎核心模块。

Step 6 只实现可独立调用的 ChatEngine，不把真实聊天接入 TUI。
ChatEngine 负责：
- 从 .env 读取模型 API 配置。
- 从 config.yaml 读取超时、重试和温度参数。
- 使用 langchain-openai 的 ChatOpenAI 调用 OpenAI 兼容接口。
- 支持历史消息、system_prompt 和异步流式输出。
"""

from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.core.config_manager import ConfigManager


class ChatEngine:
    """LangChain Chat 的对话引擎。

    本类只关注模型调用，不关心数据库、不关心 TUI，也不负责会话菜单。
    后续 Step 7 可以在 TUI 中调用它，但本步不做接入。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        system_prompt: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """初始化对话引擎。

        Args:
            config_manager: 配置管理器，用于读取 .env 和 config.yaml。
            system_prompt: 默认系统提示词；stream_chat 可传入新的 system_prompt 覆盖它。
            model_name: 可选模型名，用于加载历史会话时沿用会话原模型。

        Raises:
            ValueError: 当 .env 中没有配置 API_KEY 时抛出清晰错误。
        """
        self.config_manager = config_manager
        self.default_system_prompt = system_prompt

        self.api_key = self._read_required_env("API_KEY")
        self.api_base_url = self.config_manager.get_env(
            "API_BASE_URL",
            "https://api.deepseek.com/v1",
        )
        self.model_name = model_name or self.config_manager.get_env("MODEL_NAME", "deepseek-chat")

        config = self.config_manager.get_config()
        llm_config = config.get("llm", {})
        self.timeout = int(llm_config.get("timeout", 60))
        self.max_retries = int(llm_config.get("max_retries", 3))
        self.temperature = float(llm_config.get("temperature", 0.7))

        # ChatOpenAI 支持 OpenAI 兼容接口。只要服务端兼容 /chat/completions，
        # DeepSeek、Qwen 等模型都可以通过 base_url + api_key + model 接入。
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
        """异步流式调用模型，并逐块返回文本。

        Args:
            user_input: 当前用户输入。
            history: 历史消息列表，格式为 {"role": "human", "content": "..."}。
            system_prompt: 本次调用使用的系统提示词；为空时使用初始化时的默认值。

        Yields:
            模型流式输出的文本片段。
        """
        cleaned_input = user_input.strip()
        if not cleaned_input:
            raise ValueError("用户输入不能为空。")

        messages = self._build_messages(
            user_input=cleaned_input,
            history=history,
            system_prompt=system_prompt,
        )

        async for chunk in self.llm.astream(messages):
            text = self._extract_chunk_text(chunk.content)
            if text:
                yield text

    async def chat_once(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """一次性返回完整模型回复。

        内部复用 stream_chat，方便脚本测试或后续非流式场景使用。
        """
        parts: list[str] = []
        async for text in self.stream_chat(
            user_input=user_input,
            history=history,
            system_prompt=system_prompt,
        ):
            parts.append(text)
        return "".join(parts)

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
        """把项目内部字典消息转换为 LangChain 消息对象。

        项目统一使用 human / ai / system，同时兼容 user / assistant，方便接入不同来源数据。
        """
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
        """从 LangChain 流式 chunk 中提取文本。

        不同 OpenAI 兼容服务返回的 chunk.content 可能是字符串，也可能是列表结构。
        这里做一个保守兼容：能识别文本就返回，识别不了就跳过。
        """
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

    def _read_required_env(self, name: str) -> str:
        """读取必填环境变量。"""
        value = self.config_manager.get_env(name)
        if value is None or not value.strip():
            raise ValueError(
                f"缺少环境变量 {name}。请复制 .env.example 为 .env，并填写真实 API Key。"
            )
        return value.strip()




