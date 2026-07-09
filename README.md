# LangChain Chat

项目名为 `langchain-chat`，GitHub 仓库名为 `langchain-chatbot`。

LangChain Chat 是一个课程实训项目，目标是从零实现一个支持多轮会话的 LangChain 命令行聊天系统。

## Step 1：项目初始化与工程化配置

本步骤只完成项目骨架和工程配置，不实现数据库、TUI 菜单、LangChain 调用或用户管理。

### 当前 MVP

运行：

```bash
uv run python src/main.py
```

输出：

```text
LangChain Chat 项目已启动
```

## 技术规划

- Python 3.10+
- uv 管理环境和依赖
- LangChain
- 全链路异步 async/await
- SQLite + aiosqlite
- rich + prompt_toolkit
- pydantic / pydantic-settings
- `.env` 保存 API Key
- `config.yaml` 保存全局配置

## 后续预留方向

- WebUI
- 多模型对比
- 图文上传
- 语音输入输出
- Tool Calling
