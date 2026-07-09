"""预设 Prompt 管理业务逻辑。

本模块负责处理预设 Prompt 的业务规则：
- 启动时加载系统内置预设。
- 用户可以新增、编辑、删除自己的个人预设。
- 系统内置预设不允许被修改或删除。
TUI 只调用 PresetManager，不直接写数据库。
"""

from pathlib import Path
from typing import Any

import yaml

from src.models.schemas import Preset
from src.storage.base import StorageBackend


class PresetManager:
    """预设 Prompt 管理器。"""

    def __init__(self, storage: StorageBackend, project_root: Path) -> None:
        """初始化预设管理器。

        Args:
            storage: 存储后端实例。
            project_root: 项目根目录，用于定位 config/presets.yaml。
        """
        self.storage = storage
        self.project_root = project_root
        self.presets_path = self.project_root / "config" / "presets.yaml"

    async def load_builtin_presets(self) -> None:
        """读取 config/presets.yaml，并同步系统内置预设到数据库。

        如果同名内置预设已经存在，则跳过，避免每次启动重复插入。
        """
        if not self.presets_path.exists():
            return

        with self.presets_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        raw_presets = data.get("presets", [])
        if not isinstance(raw_presets, list):
            return

        builtin_presets = await self.storage.list_presets(user_id=None)
        existing_names = {preset.name for preset in builtin_presets if preset.is_builtin}

        for item in raw_presets:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).strip()
            description = str(item.get("description", "")).strip()
            system_prompt = str(item.get("system_prompt", "")).strip()

            if not name or not system_prompt or name in existing_names:
                continue

            await self.storage.create_preset(
                user_id=None,
                name=name,
                description=description,
                system_prompt=system_prompt,
                is_builtin=True,
            )
            existing_names.add(name)

    async def list_presets(self, user_id: int | None = None) -> list[Preset]:
        """返回系统内置预设，以及当前用户的个人预设。"""
        return await self.storage.list_presets(user_id=user_id)

    async def create_user_preset(
        self,
        user_id: int,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Preset:
        """创建用户个人预设。"""
        cleaned_name, cleaned_description, cleaned_prompt = self._clean_preset_fields(
            name,
            description,
            system_prompt,
        )
        return await self.storage.create_preset(
            user_id=user_id,
            name=cleaned_name,
            description=cleaned_description,
            system_prompt=cleaned_prompt,
            is_builtin=False,
        )

    async def update_user_preset(
        self,
        preset_id: int,
        name: str,
        description: str,
        system_prompt: str,
    ) -> Preset:
        """更新用户个人预设。

        内置预设由存储层再次保护，这里也先查一次，方便给出清晰错误。
        """
        preset = await self.storage.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"预设 ID {preset_id} 不存在。")
        if preset.is_builtin:
            raise ValueError("系统内置预设不允许修改。")

        cleaned_name, cleaned_description, cleaned_prompt = self._clean_preset_fields(
            name,
            description,
            system_prompt,
        )
        return await self.storage.update_preset(
            preset_id=preset_id,
            name=cleaned_name,
            description=cleaned_description,
            system_prompt=cleaned_prompt,
        )

    async def delete_user_preset(self, preset_id: int) -> None:
        """删除用户个人预设。"""
        preset = await self.storage.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"预设 ID {preset_id} 不存在。")
        if preset.is_builtin:
            raise ValueError("系统内置预设不允许删除。")

        await self.storage.delete_preset(preset_id)

    async def get_preset(self, preset_id: int) -> Preset | None:
        """根据 ID 查询预设。"""
        return await self.storage.get_preset(preset_id)

    @staticmethod
    def _clean_preset_fields(
        name: str,
        description: str,
        system_prompt: str,
    ) -> tuple[str, str, str]:
        """清理并校验预设字段。"""
        cleaned_name = name.strip()
        cleaned_description = description.strip()
        cleaned_prompt = system_prompt.strip()

        if not cleaned_name:
            raise ValueError("预设名称不能为空。")
        if not cleaned_prompt:
            raise ValueError("系统提示词不能为空。")

        return cleaned_name, cleaned_description, cleaned_prompt
