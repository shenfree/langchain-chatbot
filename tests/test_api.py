"""FastAPI 后端接口测试。"""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


def _write_test_project(tmp_path: Path) -> Path:
    """创建临时项目配置，使用临时 SQLite 数据库。"""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "config").mkdir()
    (project_root / "logs").mkdir()

    db_path = (project_root / "test.db").as_posix()
    (project_root / "config.yaml").write_text(
        f"""
models:
  default: fake-model
  available:
    - name: Fake Model
      value: fake-model
      provider: fake
      base_url: https://example.test/v1
      env_key: TEST_API_KEY
llm:
  timeout: 10
  max_retries: 1
  temperature: 0.1
storage:
  type: sqlite
  sqlite:
    path: {db_path}
  mysql:
    host: localhost
    port: 3306
    user: root
    database: langchain_chat
    charset: utf8mb4
  file:
    base_dir: data/file_storage
""",
        encoding="utf-8",
    )
    (project_root / "config" / "presets.yaml").write_text(
        """
presets:
  - name: 测试助手
    description: 测试用内置预设
    system_prompt: 你是测试助手。
""",
        encoding="utf-8",
    )
    return project_root


def test_health_users_presets_models_and_session_api(tmp_path: Path, monkeypatch) -> None:
    """测试 FastAPI MVP 核心接口，不调用真实模型。"""
    project_root = _write_test_project(tmp_path)
    monkeypatch.setenv("LANGCHAIN_CHAT_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        users = client.get("/users")
        assert users.status_code == 200
        assert users.json() == []

        created_user = client.post("/users", json={"username": "alice"})
        assert created_user.status_code == 200
        assert created_user.json()["username"] == "alice"

        switched = client.post("/users/current", json={"username": "alice"})
        assert switched.status_code == 200
        assert switched.json()["username"] == "alice"

        presets = client.get("/presets")
        assert presets.status_code == 200
        assert presets.json()["presets"][0]["name"] == "测试助手"

        models = client.get("/models")
        assert models.status_code == 200
        assert models.json()["current_model"] == "fake-model"
        assert models.json()["models"][0]["value"] == "fake-model"

        session = client.post("/sessions", json={"title": "API 测试会话", "model_name": "fake-model"})
        assert session.status_code == 200
        assert session.json()["title"] == "API 测试会话"

        sessions = client.get("/sessions")
        assert sessions.status_code == 200
        assert len(sessions.json()) == 1

        detail = client.get(f"/sessions/{session.json()['id']}")
        assert detail.status_code == 200
        assert detail.json()["session"]["title"] == "API 测试会话"
        assert detail.json()["messages"] == []
