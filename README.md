# LangChain Chat

项目名：`langchain-chat`  
GitHub 仓库名：`langchain-chatbot`

`langchain-chat` 是一个课程实训项目，目标是从零实现一个支持多用户、多会话、多角色 Prompt 和多模型切换的 LangChain 命令行多轮会话系统。

项目当前保留 TUI 命令行交互，并新增 FastAPI + Streamlit 前后端分离 WebUI 扩展。WebUI 是展示与操作入口之一，不替代 TUI。项目支持 SQLite / MySQL / JSON File 三种存储后端切换，并提供结构化日志和 Markdown 导出能力。

## 技术栈

- Python 3.10+
- uv 环境和依赖管理
- LangChain / langchain-openai
- FastAPI 后端接口
- Streamlit 前端页面
- rich + prompt_toolkit 命令行 TUI
- Pydantic 数据模型
- SQLite + aiosqlite
- MySQL + aiomysql
- JSON File Storage
- python-dotenv + PyYAML 配置管理
- 结构化日志 logging.yaml

## 当前已实现功能

- 多用户管理：创建、列表、切换、删除用户
- 多会话管理：新建、列表、加载、重命名、删除会话
- 多角色 Prompt：支持系统内置预设和用户个人预设
- LangChain 对话引擎：支持 OpenAI 兼容接口和异步流式输出
- 多模型切换：支持 DeepSeek、Qwen 等 OpenAI 兼容模型配置
- 对话搜索：按关键词搜索当前用户历史消息
- Markdown 导出：导出会话记录为 Markdown 文件
- SQLite / MySQL / File 三种存储后端切换
- 结构化日志：控制台、`logs/app.log`、`logs/error.log`
- 配置检查脚本：检查项目关键配置文件是否完整
- 前后端分离 WebUI：FastAPI 提供接口，Streamlit 通过 HTTP 调用后端

## 项目目录结构

```text
langchain-chat/
  config/
    presets.yaml
    logging.yaml
  docs/
    configuration.md
    git_flow.md
    workflow_log.md
  logs/
    .gitkeep
  backend/
    main.py
    routers/
  frontend/
    app.py
    api_client.py
  scripts/
    init_db.py
    check_project_config.py
    test_chat_engine.py
    test_file_backend.py
    test_logging.py
    test_mysql_backend.py
  src/
    core/
    interface/
    models/
    storage/
    ui/tui/
    utils/
    main.py
  .env.example
  .gitignore
  config.yaml
  logging.yaml
  pyproject.toml
  README.md
```

## 环境准备

确认已安装：

- Python 3.10 或更高版本
- uv
- Git

进入项目目录：

```powershell
cd D:\langchain-chat
```

## 安装依赖

```powershell
uv sync --extra dev
```

如果只安装运行依赖，也可以使用：

```powershell
uv sync
```

## 配置 .env

复制示例文件：

```powershell
copy .env.example .env
```

然后在 `.env` 中填写真实 API Key。

DeepSeek 示例：

```env
API_KEY=你的DeepSeekKey
API_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

Qwen 示例：

```env
QWEN_API_KEY=你的DashScopeKey
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

MySQL 密码示例：

```env
MYSQL_PASSWORD=你的MySQL密码
```

注意：`.env` 不应提交到 Git 仓库。

## 初始化数据库或存储

默认使用 SQLite：

```yaml
storage:
  type: sqlite
```

初始化：

```powershell
uv run python scripts\init_db.py
```

默认会生成：

```text
data/sqlite/app.db
```

## 启动项目

```powershell
uv run python src\main.py
```

启动后会进入 TUI 主菜单，可进行用户管理、会话管理、预设管理、开始对话、设置、搜索和导出。

## 启动前后端分离 WebUI

WebUI 是扩展功能，不替代已有 TUI。需要分别启动 FastAPI 后端和 Streamlit 前端。

终端 1 启动后端：

```powershell
uv run uvicorn backend.main:app --reload
```

终端 2 启动前端：

```powershell
uv run streamlit run frontend/app.py
```

浏览器打开：

```text
http://localhost:8501
```

FastAPI 文档地址：

```text
http://127.0.0.1:8000/docs
```

当前 WebUI 支持：用户创建与切换、会话列表与新建、历史会话查看、预设选择、模型选择、普通聊天、历史搜索和 Markdown 导出。MVP 阶段聊天接口返回完整回复，后续可扩展为 SSE 流式接口。

## 运行测试脚本

配置检查：

```powershell
uv run python scripts\check_project_config.py
```

日志系统检查：

```powershell
uv run python scripts\test_logging.py
```

ChatEngine 测试，需要先配置模型 API Key：

```powershell
uv run python scripts\test_chat_engine.py
```

FileBackend 冒烟测试，需要先把 `storage.type` 改为 `file`：

```powershell
uv run python scripts\test_file_backend.py
```

MySQLBackend 冒烟测试，需要先配置 MySQL 并把 `storage.type` 改为 `mysql`：

```powershell
uv run python scripts\test_mysql_backend.py
```

## 存储后端切换说明

修改 `config.yaml` 的 `storage.type`。

SQLite：

```yaml
storage:
  type: sqlite
```

MySQL：

```yaml
storage:
  type: mysql
```

MySQL 使用前需要创建数据库：

```sql
CREATE DATABASE langchain_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

File：

```yaml
storage:
  type: file
```

File 后端数据目录：

```text
data/file_storage/
  users.json
  sessions.json
  messages.json
  presets.json
```

更多配置说明见 [docs/configuration.md](docs/configuration.md)。

## 日志说明

日志配置文件：

```text
logging.yaml
```

日志输出位置：

```text
logs/app.log
logs/error.log
```

日志中不会记录 API Key、MySQL 密码，也不会完整记录用户消息内容。真实日志文件会被 `.gitignore` 忽略。

## Git Step 记录说明

每完成一个 Step 后建议提交并打 tag：

```powershell
git add .
git commit -m "step 14: organize configuration and docs"
git tag step-14-config-docs
git push
git push origin step-14-config-docs
```

详细 Git 流程见 [docs/git_flow.md](docs/git_flow.md)。  
项目演进记录见 [docs/workflow_log.md](docs/workflow_log.md)。

## 后续计划

以下能力尚未实现，仅作为后续扩展方向：

- RAG 知识库问答
- 文件上传和图文输入
- 语音输入输出
- Tool Calling
- 多模型并行对比
- 更完整的自动化测试体系
