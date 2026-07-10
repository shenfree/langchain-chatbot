"""模型配置与运行时模型状态管理。

ModelManager 只负责读取模型配置、维护当前运行时默认模型，以及校验模型是否可用。
它不直接调用大模型；真正的调用仍由 ChatEngine 完成。
"""

from typing import Any

from src.core.config_manager import ConfigManager


class ModelManager:
    """模型管理器。"""

    def __init__(self, config_manager: ConfigManager) -> None:
        """初始化模型管理器。"""
        self.config_manager = config_manager
        self._current_model = self.get_default_model()

    def list_models(self) -> list[dict[str, Any]]:
        """从 config.yaml 读取可用模型列表。"""
        config = self.config_manager.get_config()
        models_config = config.get("models", {})
        available = models_config.get("available", [])
        return available if isinstance(available, list) else []

    def get_default_model(self) -> str:
        """获取默认模型。

        优先读取 .env 中 MODEL_NAME；如果没有，则读取 config.yaml 的 models.default。
        """
        env_model = self.config_manager.get_env("MODEL_NAME")
        if env_model and env_model.strip():
            return env_model.strip()

        config = self.config_manager.get_config()
        return str(config.get("models", {}).get("default", "deepseek-chat"))

    def get_current_model(self) -> str:
        """返回当前运行时默认模型。"""
        return self._current_model

    def switch_model(self, model_name: str) -> dict[str, Any]:
        """切换当前运行时默认模型。

        model_name 可以是模型 value，也可以是展示名称 name。
        """
        model_config = self.get_model_config(model_name)
        self._current_model = str(model_config["value"])
        return model_config

    def get_model_config(self, model_name: str) -> dict[str, Any]:
        """根据模型名称或模型值获取配置。"""
        cleaned_name = model_name.strip()
        for model in self.list_models():
            name = str(model.get("name", ""))
            value = str(model.get("value", ""))
            if cleaned_name in {name, value}:
                return model

        # 旧配置兼容：如果 config.yaml 没有列出该模型，允许回退到通用配置。
        legacy_default = self.get_default_model()
        if cleaned_name == legacy_default:
            return {
                "name": cleaned_name,
                "value": cleaned_name,
                "provider": "legacy",
                "base_url": self.config_manager.get_env("API_BASE_URL", "https://api.deepseek.com/v1"),
                "env_key": "API_KEY",
            }

        raise ValueError(f"模型 {cleaned_name} 不在可用模型列表中。")
