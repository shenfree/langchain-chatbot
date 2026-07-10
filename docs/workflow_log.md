# 项目实施记录

本文档按 Step 记录 `langchain-chat` 的课程实训演进过程，便于答辩时说明项目是逐步完成的。

## Step 1：项目初始化与工程化配置

- 目标：搭建项目骨架，配置 `uv`、基础配置文件和入口文件。
- 修改内容：新增 `pyproject.toml`、`.gitignore`、`.env.example`、`config.yaml`、`README.md`、`src/main.py` 等基础文件。
- 验证方式：`uv run python src/main.py`。
- 是否完成：已完成。

## Step 2：数据模型、存储接口、配置管理、TUI 骨架

- 目标：定义 Pydantic 数据模型、存储抽象接口、配置管理和 TUI 主菜单。
- 修改内容：新增 `schemas.py`、`storage/base.py`、`config_manager.py`、TUI 菜单骨架。
- 验证方式：运行主程序，确认能看到可交互主菜单。
- 是否完成：已完成。

## Step 3：SQLite 存储后端与数据库初始化

- 目标：实现 SQLite 后端和数据库表初始化。
- 修改内容：新增 `SQLiteBackend`、`StorageFactory`、`scripts/init_db.py`。
- 验证方式：`uv run python scripts/init_db.py`，确认生成 `data/sqlite/app.db`。
- 是否完成：已完成。

## Step 4：用户管理模块与 TUI 用户菜单

- 目标：实现用户创建、列表、切换、删除和当前用户状态。
- 修改内容：新增 `UserManager`，接入 TUI 用户管理菜单。
- 验证方式：运行主程序，创建、切换、删除用户。
- 是否完成：已完成。

## Step 5：预设 Prompt 管理模块与 TUI 预设菜单

- 目标：实现系统内置预设和用户个人预设管理。
- 修改内容：新增 `PresetManager`，补充预设 CRUD，加载 `config/presets.yaml`。
- 验证方式：查看内置预设，创建、编辑、删除个人预设。
- 是否完成：已完成。

## Step 6：对话引擎核心

- 目标：实现 ChatEngine，支持 OpenAI 兼容接口和异步流式输出。
- 修改内容：新增 `chat_engine.py` 和 `scripts/test_chat_engine.py`。
- 验证方式：配置 `.env` 后运行 `uv run python scripts/test_chat_engine.py`。
- 是否完成：已完成。

## Step 7：会话管理与 TUI 对话视图对接

- 目标：实现真实多轮流式对话和会话自动保存。
- 修改内容：新增 `SessionManager`，ChatEngine 接入 TUI 对话流程。
- 验证方式：创建用户后开始对话，确认消息保存和 `/sessions` 可用。
- 是否完成：已完成。

## Step 8：会话管理完善

- 目标：支持会话列表、加载、重命名、删除和新建会话入口。
- 修改内容：完善 `SessionManager` 和 TUI 会话管理菜单。
- 验证方式：创建会话后重命名、加载继续对话、删除会话。
- 是否完成：已完成。

## Step 9：对话搜索

- 目标：在当前用户历史消息中按关键词搜索。
- 修改内容：新增存储层 `search_messages`，TUI 新增对话搜索入口和聊天命令 `/search`。
- 验证方式：发送包含关键词的消息后搜索，确认不能跨用户看到数据。
- 是否完成：已完成。

## Step 10：对话导出与模型切换

- 目标：支持 Markdown 导出和模型切换。
- 修改内容：新增模型管理能力，导出当前或指定会话为 Markdown。
- 验证方式：使用 `/model`、`/switch`、`/export` 和主菜单导出入口。
- 是否完成：已完成。

## Step 11：MySQL 存储后端

- 目标：新增 MySQLBackend，实现 sqlite / mysql 切换。
- 修改内容：新增 `src/storage/mysql_backend.py`，工厂支持 `storage.type=mysql`，新增 `scripts/test_mysql_backend.py`。
- 验证方式：默认 SQLite 下脚本跳过；配置 MySQL 后运行初始化和冒烟测试。
- 是否完成：已完成。

## Step 12：File 存储后端

- 目标：新增 JSON FileBackend，实现 sqlite / mysql / file 三种存储切换。
- 修改内容：新增 `src/storage/file_backend.py`，配置 `storage.file.base_dir`，新增 `scripts/test_file_backend.py`。
- 验证方式：临时切换 `storage.type=file`，运行初始化和冒烟测试。
- 是否完成：已完成。

## Step 13：结构化日志系统

- 目标：新增统一日志系统，记录关键事件、错误和调试信息。
- 修改内容：新增 `logging.yaml`、`src/utils/logger.py`、`scripts/test_logging.py`，核心模块接入日志。
- 验证方式：`uv run python scripts/test_logging.py`，确认生成 `logs/app.log`。
- 是否完成：已完成。

## Step 14：配置系统整理与 README 补充

- 目标：整理配置文件，补充 README 和 docs 文档，提供配置检查脚本。
- 修改内容：整理 `config.yaml`、`.env.example`、`README.md`，新增 `docs/configuration.md`、`docs/workflow_log.md`、`docs/git_flow.md`、`scripts/check_project_config.py`。
- 验证方式：运行 `uv run python scripts/check_project_config.py`。
- 是否完成：已完成。

## 扩展：FastAPI + Streamlit 前后端分离 WebUI

- 目标：在保留 TUI 的基础上新增 FastAPI 后端接口和 Streamlit 前端页面。
- 修改内容：新增 `backend/`、`frontend/`、`tests/test_api.py`，前端只通过 HTTP 调用后端，后端复用现有 core/storage 管理器。
- 验证方式：运行 `uv run pytest`、`uv run python -m compileall src scripts tests backend frontend`，手动启动后端和前端验证页面。
- 是否完成：已完成。
## Step 15：多环境配置

- 目标：支持 development / testing / production 三种环境配置。
- 修改内容：新增 `config/envs/*.yaml`，增强 `ConfigManager`，补充配置检查和单元测试。
- 验证方式：运行 `uv run pytest`、`uv run python scripts/check_project_config.py`、`uv run python -m compileall src scripts tests backend frontend`。
- 是否完成：已完成。