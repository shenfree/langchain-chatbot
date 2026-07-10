"""FastAPI 后端接口测试。"""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


class FakeChatEngine:
    """用于 API 测试的假 ChatEngine，避免调用真实大模型。"""

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def stream_chat(self, *args, **kwargs):
        yield "流式"
        yield "回复"

    async def chat_once(self, *args, **kwargs) -> str:
        return "完整回复"


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


def test_chat_stream_route_validation(tmp_path: Path, monkeypatch) -> None:
    """缺少必要参数时，/chat/stream 应返回请求校验错误。"""
    project_root = _write_test_project(tmp_path)
    monkeypatch.setenv("LANGCHAIN_CHAT_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)

    with TestClient(app) as client:
        response = client.post("/chat/stream", json={})
        assert response.status_code == 422


def test_chat_stream_route_returns_stream_content(tmp_path: Path, monkeypatch) -> None:
    """mock ChatEngine 后，/chat/stream 应返回流式内容并保存消息。"""
    project_root = _write_test_project(tmp_path)
    monkeypatch.setenv("LANGCHAIN_CHAT_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.setattr("backend.routers.chat.ChatEngine", FakeChatEngine)

    with TestClient(app) as client:
        created_user = client.post("/users", json={"username": "stream_user"})
        assert created_user.status_code == 200
        switched = client.post("/users/current", json={"username": "stream_user"})
        assert switched.status_code == 200
        session = client.post("/sessions", json={"title": "流式测试会话", "model_name": "fake-model"})
        assert session.status_code == 200

        with client.stream(
            "POST",
            "/chat/stream",
            json={"session_id": session.json()["id"], "message": "请流式回答"},
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())

        assert body == "流式回复"
        detail = client.get(f"/sessions/{session.json()['id']}")
        assert detail.status_code == 200
        messages = detail.json()["messages"]
        assert [message["role"] for message in messages] == ["human", "ai"]
        assert messages[-1]["content"] == "流式回复"