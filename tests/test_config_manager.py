"""ConfigManager 多环境配置测试。"""

from pathlib import Path

import pytest

from src.core.config_manager import ConfigManager


BASE_CONFIG = """
app:
  name: langchain-chat
  env: base
  debug: false
models:
  default: base-model
  available:
    - name: DeepSeek Chat
      value: deepseek-chat
      provider: deepseek
      base_url: https://api.deepseek.com/v1
      env_key: API_KEY
storage:
  type: sqlite
  sqlite:
    path: data/sqlite/app.db
  mysql:
    host: localhost
    port: 3306
    user: root
    database: langchain_chat
    charset: utf8mb4
  file:
    base_dir: data/file_storage
"""

ENV_CONFIGS = {
    "development": """
app:
  env: development
  debug: true
storage:
  type: sqlite
  sqlite:
    path: data/sqlite/app_dev.db
logging:
  level: DEBUG
models:
  default: deepseek-chat
""",
    "testing": """
app:
  env: testing
  debug: true
storage:
  type: sqlite
  sqlite:
    path: data/sqlite/app_test.db
logging:
  level: DEBUG
models:
  default: deepseek-chat
""",
    "production": """
app:
  env: production
  debug: false
storage:
  type: sqlite
  sqlite:
    path: data/sqlite/app.db
logging:
  level: INFO
models:
  default: deepseek-chat
""",
}


def make_project(tmp_path: Path) -> Path:
    """创建临时项目配置目录。"""
    project_root = tmp_path / "project"
    env_dir = project_root / "config" / "envs"
    env_dir.mkdir(parents=True)
    (project_root / "config.yaml").write_text(BASE_CONFIG, encoding="utf-8")
    for name, content in ENV_CONFIGS.items():
        (env_dir / f"{name}.yaml").write_text(content, encoding="utf-8")
    return project_root


def test_load_base_config_when_app_env_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """未设置 APP_ENV 时，只读取基础 config.yaml。"""
    project_root = make_project(tmp_path)
    monkeypatch.delenv("APP_ENV", raising=False)

    config = ConfigManager(project_root=project_root).get_config()

    assert config["app"]["env"] == "base"
    assert config["app"]["debug"] is False
    assert config["storage"]["sqlite"]["path"] == "data/sqlite/app.db"


@pytest.mark.parametrize(
    ("app_env", "sqlite_path", "debug"),
    [
        ("development", "data/sqlite/app_dev.db", True),
        ("testing", "data/sqlite/app_test.db", True),
        ("production", "data/sqlite/app.db", False),
    ],
)
def test_app_env_overrides_base_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
    sqlite_path: str,
    debug: bool,
) -> None:
    """APP_ENV 应读取对应环境文件并覆盖基础配置。"""
    project_root = make_project(tmp_path)
    monkeypatch.setenv("APP_ENV", app_env)

    config = ConfigManager(project_root=project_root).get_config()

    assert config["app"]["env"] == app_env
    assert config["app"]["debug"] is debug
    assert config["storage"]["sqlite"]["path"] == sqlite_path
    assert config["models"]["default"] == "deepseek-chat"


def test_unknown_app_env_raises_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """未知 APP_ENV 应抛出清晰异常。"""
    project_root = make_project(tmp_path)
    monkeypatch.setenv("APP_ENV", "unknown")

    with pytest.raises(ValueError, match="不支持的 APP_ENV"):
        ConfigManager(project_root=project_root).get_config()


def test_env_merge_keeps_models_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """环境配置覆盖时不能丢失基础配置里的 models.available。"""
    project_root = make_project(tmp_path)
    monkeypatch.setenv("APP_ENV", "development")

    config = ConfigManager(project_root=project_root).get_config()

    assert config["models"]["available"]
    assert config["models"]["available"][0]["value"] == "deepseek-chat"


def test_env_merge_keeps_storage_mysql_and_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """环境配置覆盖时不能丢失 storage.mysql 和 storage.file。"""
    project_root = make_project(tmp_path)
    monkeypatch.setenv("APP_ENV", "testing")

    config = ConfigManager(project_root=project_root).get_config()

    assert config["storage"]["mysql"]["database"] == "langchain_chat"
    assert config["storage"]["file"]["base_dir"] == "data/file_storage"
    assert config["storage"]["sqlite"]["path"] == "data/sqlite/app_test.db"
