"""LangChain Chat Streamlit 前端。"""

from __future__ import annotations

from typing import Any

import streamlit as st

from api_client import ApiClient


st.set_page_config(page_title="LangChain Chat WebUI", page_icon="💬", layout="wide")


def main() -> None:
    """渲染 Streamlit 前后端分离 WebUI。"""
    st.title("LangChain Chat WebUI")
    st.caption("前后端分离版本：Streamlit 前端只通过 FastAPI HTTP 接口调用后端。")

    client = build_sidebar()
    current_user = load_current_user(client)

    if current_user is None:
        st.info("请先在左侧创建或选择一个演示用户。")
        return

    st.success(f"当前用户：{current_user['username']}")
    session_id = ensure_current_session(client)
    if session_id is None:
        st.warning("暂时无法创建或加载会话，请检查后端状态。")
        return

    render_chat_area(client, int(session_id))


def build_sidebar() -> ApiClient:
    """渲染侧边栏并返回 API 客户端。"""
    with st.sidebar.expander("高级设置 / 后端连接", expanded=False):
        base_url = st.text_input(
            "FastAPI 地址",
            value=st.session_state.get("base_url", "http://127.0.0.1:8000"),
        )
    st.session_state["base_url"] = base_url
    client = ApiClient(base_url)

    try:
        health = client.health()
        st.sidebar.caption(f"后端状态：正常（{health.get('status', 'ok')}）")
    except Exception as exc:
        st.sidebar.error(f"后端不可用：{exc}")
        st.stop()

    render_user_controls(client)
    current_user = load_current_user(client)
    if current_user is not None:
        render_session_controls(client)
        render_preset_and_model_controls(client)
        render_search_controls(client)
        render_export_controls(client)
    return client


def small_hint(text: str) -> None:
    """在侧边栏显示弱化的小号说明文字。"""
    st.sidebar.markdown(
        f"<div style='font-size: 12px; color: #8b8b8b; line-height: 1.45; margin: -0.35rem 0 0.45rem 0;'>{text}</div>",
        unsafe_allow_html=True,
    )

def render_user_controls(client: ApiClient) -> None:
    """侧边栏多用户演示管理。"""
    st.sidebar.header("多用户演示")
    small_hint("当前入口用于课程演示多用户隔离能力，真实产品中应替换为登录注册与权限鉴权。")

    users = safe_call(client.list_users, [])
    user_names = [user["username"] for user in users]
    user_by_name = {user["username"]: user for user in users}
    current_user = load_current_user(client)

    new_username = st.sidebar.text_input("创建演示用户")
    if st.sidebar.button("创建演示用户", use_container_width=True):
        if not new_username.strip():
            st.sidebar.warning("用户名不能为空。")
        else:
            username = new_username.strip()
            created_user = safe_action(lambda: client.create_user(username), "用户创建成功")
            if created_user:
                switched_user = safe_action(
                    lambda: client.switch_user(username=username),
                    "用户创建成功，已切换为当前用户",
                )
                if switched_user:
                    st.session_state.pop("current_session_id", None)
            st.rerun()

    if user_names:
        selected_name = st.sidebar.selectbox("切换演示用户", user_names)
        if st.sidebar.button("切换用户", use_container_width=True):
            user = safe_action(lambda: client.switch_user(username=selected_name), "用户切换成功")
            if user:
                st.session_state.pop("current_session_id", None)
            st.rerun()
    else:
        st.sidebar.info("暂无演示用户。")

    st.sidebar.subheader("删除演示用户")
    small_hint("⚠ 删除演示用户会同时删除该用户的会话和聊天记录，请谨慎操作。")
    if user_names:
        delete_name = st.sidebar.selectbox("选择要删除的演示用户", user_names, key="delete_user_name")
        confirm_name = st.sidebar.text_input("输入用户名确认删除", key="delete_user_confirm")
        can_delete = confirm_name.strip() == delete_name
        if st.sidebar.button("删除演示用户", use_container_width=True, disabled=not can_delete):
            target_user = user_by_name[delete_name]
            result = safe_action(lambda: client.delete_user(int(target_user["id"])), "演示用户已删除")
            if result:
                if current_user is not None and current_user.get("id") == target_user.get("id"):
                    st.session_state.pop("current_session_id", None)
                    st.sidebar.info("已删除当前演示用户，请重新选择演示用户。")
                st.rerun()
    else:
        st.sidebar.caption("暂无可删除的演示用户。")


def render_session_controls(client: ApiClient) -> None:
    """侧边栏会话管理。"""
    st.sidebar.header("会话")
    sessions = safe_call(client.list_sessions, [])
    session_options = {format_session_label(session): session["id"] for session in sessions}

    if session_options:
        labels = list(session_options.keys())
        current_id = st.session_state.get("current_session_id")
        default_index = next(
            (index for index, label in enumerate(labels) if session_options[label] == current_id),
            0,
        )
        selected_label = st.sidebar.selectbox("会话列表", labels, index=default_index)
        if st.sidebar.button("加载会话", use_container_width=True):
            st.session_state["current_session_id"] = session_options[selected_label]
            st.rerun()
    else:
        st.sidebar.info("暂无会话。")

    if st.sidebar.button("新建会话", use_container_width=True):
        session = safe_action(
            lambda: client.create_session(
                title="新会话",
                model_name=st.session_state.get("selected_model"),
                preset_id=st.session_state.get("selected_preset_id"),
            ),
            "会话创建成功",
        )
        if session:
            st.session_state["current_session_id"] = session["id"]
        st.rerun()

    current_id = st.session_state.get("current_session_id")
    if current_id is not None:
        new_title = st.sidebar.text_input("重命名当前会话")
        if st.sidebar.button("重命名", use_container_width=True):
            safe_action(lambda: client.rename_session(int(current_id), new_title), "会话重命名成功")
            st.rerun()

        confirm_delete = st.sidebar.checkbox("确认删除当前会话")
        if st.sidebar.button("删除当前会话", use_container_width=True, disabled=not confirm_delete):
            safe_action(lambda: client.delete_session(int(current_id)), "会话已删除")
            st.session_state.pop("current_session_id", None)
            st.rerun()


def render_preset_and_model_controls(client: ApiClient) -> None:
    """侧边栏预设和模型选择。"""
    st.sidebar.header("预设与模型")
    presets = safe_call(client.list_presets, [])
    preset_labels = ["不使用预设"] + [f"{item['id']} | {item['name']}" for item in presets]
    selected_preset = st.sidebar.selectbox("预设 Prompt", preset_labels)
    if selected_preset == "不使用预设":
        st.session_state["selected_preset_id"] = None
    else:
        st.session_state["selected_preset_id"] = int(selected_preset.split(" | ", 1)[0])

    models_payload = safe_call(client.list_models, {"models": [], "current_model": ""})
    models = models_payload.get("models", [])
    model_values = [model.get("value", "") for model in models if model.get("value")]
    if model_values:
        current_model = models_payload.get("current_model") or model_values[0]
        index = model_values.index(current_model) if current_model in model_values else 0
        st.session_state["selected_model"] = st.sidebar.selectbox("模型", model_values, index=index)
    else:
        st.sidebar.info("暂无模型配置。")
        st.session_state["selected_model"] = None


def render_search_controls(client: ApiClient) -> None:
    """侧边栏搜索历史消息。"""
    st.sidebar.header("搜索")
    keyword = st.sidebar.text_input("搜索历史消息")
    if st.sidebar.button("搜索", use_container_width=True):
        if not keyword.strip():
            st.sidebar.warning("关键词不能为空。")
        else:
            results = safe_call(lambda: client.search(keyword.strip()), [])
            st.session_state["search_results"] = results

    for result in st.session_state.get("search_results", [])[:5]:
        content = str(result.get("content", "")).replace("\n", " ")[:80]
        st.sidebar.caption(f"会话 {result.get('session_id')} | {result.get('role')} | {content}")


def render_export_controls(client: ApiClient) -> None:
    """侧边栏导出当前会话。"""
    st.sidebar.header("导出")
    session_id = st.session_state.get("current_session_id")
    if session_id is None:
        st.sidebar.caption("请选择会话后再导出。")
        return
    if st.sidebar.button("导出当前会话", use_container_width=True):
        result = safe_action(lambda: client.export_session(int(session_id)), "导出完成")
        if result:
            st.sidebar.code(result.get("path", ""))


def ensure_current_session(client: ApiClient) -> int | None:
    """确保当前用户有一个可用会话，并返回会话 ID。"""
    current_id = st.session_state.get("current_session_id")
    sessions = safe_call(client.list_sessions, [])
    session_ids = {session.get("id") for session in sessions}

    if current_id in session_ids:
        return int(current_id)

    if sessions:
        # 后端会话列表按 updated_at 倒序返回，第一个就是最近会话。
        recent_session = sessions[0]
        st.session_state["current_session_id"] = recent_session["id"]
        return int(recent_session["id"])

    session = safe_action(
        lambda: client.create_session(
            title="Web 新会话",
            model_name=st.session_state.get("selected_model"),
            preset_id=st.session_state.get("selected_preset_id"),
        ),
        "已自动创建默认会话",
    )
    if not session:
        return None
    st.session_state["current_session_id"] = session["id"]
    return int(session["id"])

def render_chat_area(client: ApiClient, session_id: int) -> None:
    """主聊天区。"""
    detail = safe_call(lambda: client.get_session(session_id), None)
    if not detail:
        st.warning("当前会话不存在，请重新选择。")
        st.session_state.pop("current_session_id", None)
        return

    session = detail["session"]
    messages = detail["messages"]
    st.subheader(session.get("title") or "新会话")
    st.caption(f"会话 ID：{session_id} | 模型：{session.get('model_name')} | 预设 ID：{session.get('preset_id') or '-'}")

    if st.button("刷新会话消息"):
        st.rerun()

    for message in messages:
        role = "assistant" if message.get("role") == "ai" else "user"
        with st.chat_message(role):
            st.write(message.get("content", ""))

    user_input = st.chat_input("输入你的问题")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("AI 正在回复..."):
                response = safe_action(
                    lambda: client.chat(
                        session_id=session_id,
                        message=user_input,
                        preset_id=st.session_state.get("selected_preset_id"),
                        model_name=st.session_state.get("selected_model"),
                    ),
                    "回复完成",
                )
                if response:
                    st.write(response.get("reply", ""))
        st.rerun()


def load_current_user(client: ApiClient) -> dict[str, Any] | None:
    """读取当前用户。"""
    payload = safe_call(client.get_current_user, {"user": None})
    return payload.get("user") if payload else None


def format_session_label(session: dict[str, Any]) -> str:
    """格式化会话下拉框标签。"""
    title = session.get("title") or "新会话"
    return f"{session.get('id')} | {title}"


def safe_call(func, default):
    """执行 API 调用，失败时展示错误并返回默认值。"""
    try:
        return func()
    except Exception as exc:
        st.error(str(exc))
        return default


def safe_action(func, success_message: str):
    """执行有副作用的 API 调用。"""
    try:
        result = func()
        st.success(success_message)
        return result
    except Exception as exc:
        st.error(str(exc))
        return None


if __name__ == "__main__":
    main()
