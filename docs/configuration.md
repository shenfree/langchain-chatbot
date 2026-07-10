# 配置说明

本文档说明 `langchain-chat` 项目的配置文件、环境变量、存储切换、模型切换和日志位置。

## config.yaml 的作用

`config.yaml` 保存项目的非敏感全局配置，例如：

- `app`：应用名称、版本、运行环境。
- `models`：可用模型列表、默认模型、模型服务地址、对应环境变量名。
- `llm`：模型调用超时、重试次数、温度等参数。
- `storage`：存储后端类型和各后端的非敏感配置。
- `export`：Markdown 导出目录模板说明。
- `logging`：日志配置文件和日志输出位置说明。
- `tui`：命令行界面配置。

不要把 API Key、MySQL 密码等敏感信息写入 `config.yaml`。

## .env 的作用

`.env` 保存本地敏感信息和可选运行时覆盖项，例如：

- 模型 API Key
- MySQL 密码
- 可选 MySQL 主机、端口、用户名、数据库名覆盖项

项目仓库只提交 `.env.example`，真实 `.env` 会被 `.gitignore` 忽略。

## 为什么 API Key 放在 .env

API Key 属于敏感凭据，一旦提交到 Git 仓库，可能导致账号额度被盗用或隐私泄露。
因此项目约定：

- `config.yaml` 只写模型名称、base_url、env_key。
- `.env` 写真实 API Key。
- 日志中也不输出 API Key 或 MySQL 密码。

## 切换存储后端

修改 `config.yaml` 中的 `storage.type`。

### SQLite

默认配置：

```yaml
storage:
  type: sqlite
  sqlite:
    path: data/sqlite/app.db
```

初始化：

```powershell
uv run python scripts/init_db.py
```

SQLite 适合本地开发和课程演示，开箱即用。

### MySQL

配置示例：

```yaml
storage:
  type: mysql
  mysql:
    host: localhost
    port: 3306
    user: root
    database: langchain_chat
    charset: utf8mb4
```

`.env` 中填写：

```env
MYSQL_PASSWORD=你的MySQL密码
```

第一次使用前在 MySQL 中创建数据库：

```sql
CREATE DATABASE langchain_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

初始化和测试：

```powershell
uv run python scripts/init_db.py
uv run python scripts/test_mysql_backend.py
```

### File

配置示例：

```yaml
storage:
  type: file
  file:
    base_dir: data/file_storage
```

初始化和测试：

```powershell
uv run python scripts/init_db.py
uv run python scripts/test_file_backend.py
```

File 后端使用 JSON 文件保存数据，便于人工查看，不适合高并发生产场景。

## 配置 MySQL

1. 安装并启动 MySQL。
2. 创建数据库 `langchain_chat`。
3. 在 `.env` 中填写 `MYSQL_PASSWORD`。
4. 如需覆盖 `config.yaml` 中的非敏感项，可在 `.env` 中启用：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_DATABASE=langchain_chat
```

5. 把 `storage.type` 改为 `mysql`。
6. 运行 `uv run python scripts/init_db.py`。

## 切换模型

模型列表在 `config.yaml` 的 `models.available` 中维护。

示例：

```yaml
models:
  default: deepseek-chat
  available:
    - name: DeepSeek Chat
      value: deepseek-chat
      provider: deepseek
      base_url: https://api.deepseek.com/v1
      env_key: API_KEY
```

`env_key` 表示读取 `.env` 中哪个变量作为 API Key。
TUI 中可以通过设置菜单或聊天命令切换当前模型，已有会话也可以记录自己的模型名。

## 日志文件位置

日志规则在 `logging.yaml` 中配置。

默认输出：

- 普通日志：`logs/app.log`
- 错误日志：`logs/error.log`
- 终端控制台

真实日志文件不会提交到 Git，`logs/.gitkeep` 用于保留目录。

## 常见配置错误

### 1. 启动模型调用时报缺少 API Key

检查 `.env` 是否存在，并确认对应环境变量已填写。例如 DeepSeek 默认使用：

```env
API_KEY=
```

Qwen 默认使用：

```env
QWEN_API_KEY=
```

### 2. MySQL 初始化提示缺少 MYSQL_PASSWORD

当前 `storage.type=mysql`，但 `.env` 中没有填写：

```env
MYSQL_PASSWORD=你的MySQL密码
```

### 3. MySQL 提示 Unknown database

需要先执行：

```sql
CREATE DATABASE langchain_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. File 后端看不到 JSON 文件

先确认：

```yaml
storage:
  type: file
```

然后运行：

```powershell
uv run python scripts/init_db.py
```

### 5. 日志文件没有生成

运行：

```powershell
uv run python scripts/test_logging.py
```

如果仍未生成，检查 `logging.yaml` 是否存在，以及项目根目录下是否有 `logs/` 目录。
