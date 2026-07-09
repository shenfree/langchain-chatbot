"""项目数据模型定义。

本文件只负责描述数据结构，不负责数据库建表或数据持久化。
后续 SQLite 后端会复用这些模型作为输入输出的数据契约。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class User(BaseModel):
    """用户数据模型。

    一个用户可以拥有多个会话、多个自定义预设和自己的默认模型配置。
    """

    id: int | None = Field(default=None, description="用户 ID，数据库生成前可以为空")
    username: str = Field(description="用户名")
    default_model: str | None = Field(default=None, description="用户默认使用的模型名称")
    default_preset_id: int | None = Field(default=None, description="用户默认预设 ID")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class Session(BaseModel):
    """会话数据模型。

    一次会话代表用户和模型之间的一组连续多轮消息。
    """

    id: int | None = Field(default=None, description="会话 ID，数据库生成前可以为空")
    user_id: int = Field(description="所属用户 ID")
    title: str = Field(description="会话标题")
    model_name: str = Field(description="本会话使用的模型名称")
    preset_id: int | None = Field(default=None, description="本会话使用的预设 ID")
    total_prompt_tokens: int = Field(default=0, description="累计输入 token 数")
    total_completion_tokens: int = Field(default=0, description="累计输出 token 数")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class Message(BaseModel):
    """消息数据模型。

    一条消息属于某个会话，role 用于区分 user、assistant、system 等角色。
    """

    id: int | None = Field(default=None, description="消息 ID，数据库生成前可以为空")
    session_id: int = Field(description="所属会话 ID")
    role: str = Field(description="消息角色，例如 human、ai、system")
    content: str = Field(description="消息正文")
    prompt_tokens: int = Field(default=0, description="该消息消耗的输入 token 数")
    completion_tokens: int = Field(default=0, description="该消息消耗的输出 token 数")
    created_at: datetime | None = Field(default=None, description="创建时间")


class Preset(BaseModel):
    """预设数据模型。

    预设用于保存系统提示词和对话风格，既可以是内置预设，也可以是用户自定义预设。
    """

    id: int | None = Field(default=None, description="预设 ID，数据库生成前可以为空")
    user_id: int | None = Field(default=None, description="所属用户 ID；内置预设可以为空")
    name: str = Field(description="预设名称")
    description: str = Field(description="预设说明")
    system_prompt: str = Field(description="系统提示词")
    is_builtin: bool = Field(default=False, description="是否为系统内置预设")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class UserConfig(BaseModel):
    """用户配置数据模型。

    使用 key/value 结构保存用户级别的偏好设置，方便后续扩展更多配置项。
    """

    id: int | None = Field(default=None, description="配置 ID，数据库生成前可以为空")
    user_id: int = Field(description="所属用户 ID")
    key: str = Field(description="配置键")
    value: str = Field(description="配置值")
    updated_at: datetime | None = Field(default=None, description="更新时间")

