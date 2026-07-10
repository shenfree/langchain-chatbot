"""LangChain Chat Streamlit 前端。"""

from __future__ import annotations

from typing import Any

import streamlit as st

from api_client import ApiClient


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_SESSION_TITLES = {"", "新会话", "Web 新会话", "未命名会话"}
AUTO_TITLE_MAX_LENGTH = 20

st.set_page_config(page_title="LangChain Chat WebUI", page_icon="💬", layout="wide")


def main() -> None:
    """渲染 Streamlit 前后端分离 WebUI。"""
    st.title("LangChain Chat WebUI")
    st.caption("基于 FastAPI + Streamlit 的前后端分离 AI Chatbot。")

    client = build_sidebar()
    current_user = load_current_user(client)

    if current_user is None:
        st.info("请先在左侧多用户演示中创建或选择一个演示用户。")
        return

    session_id = ensure_current_session(client)
    if session_id is None:
        st.warning("暂时无法创建或加载会话，请检查后端状态。")
        return

    render_chat_area(client, int(session_id))


def build_sidebar() -> ApiClient:
    """渲染左侧会话导航，并返回 API 客户端。"""
    st.sidebar.title("LangChain Chat")

    base_url = st.session_state.get("base_url", DEFAULT_BASE_URL)
    client = ApiClient(base_url)
    health_status = check_backend_health(client)

    current_user = load_current_user(client) if health_status else None
    if current_user is not None:
        ensure_current_session(client)
        render_new_session_button(client)
        render_search_controls(client)
        render_session_navigation(client)
        render_current_user_info(current_user)
    else:
        st.sidebar.info("请先在下方多用户演示中创建或选择用户。")

    render_secondary_controls(client, current_user, health_status)
    return client


def check_backend_health(client: ApiClient) -> bool:
    """检查后端状态，侧边栏只保留轻量提示。"""
    try:
        health = client.health()
        st.sidebar.caption(f"后端状态：正常（{health.get('status', 'ok')}）")
        return True
    except Exception as exc:
        st.sidebar.error(f"后端不可用：{exc}")
        return False


def render_new_session_button(client: ApiClient) -> None:
    """侧边栏顶部的新建会话按钮。"""
    if st.sidebar.button("＋ 新建会话", use_container_width=True, type="primary"):
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


def render_session_navigation(client: ApiClient) -> None:
    """左侧核心会话导航。"""
    st.sidebar.markdown("#### 会话")
    sessions = safe_call(client.list_sessions, [])
    if not sessions:
        st.sidebar.caption("暂无会话。")
        return

    current_id = st.session_state.get("current_session_id")
    for session in sessions:
        session_id = session.get("id")
        title = session.get("title") or "新会话"
        marker = "●" if session_id == current_id else "○"
        button_label = f"{marker} {title}"
        if st.sidebar.button(button_label, key=f"session_nav_{session_id}", use_container_width=True):
            st.session_state["current_session_id"] = session_id
            st.rerun()


def render_current_user_info(current_user: dict[str, Any]) -> None:
    """侧边栏显示当前用户信息。"""
    st.sidebar.divider()
    st.sidebar.caption(f"当前演示用户：{current_user['username']}")


def render_secondary_controls(
    client: ApiClient,
    current_user: dict[str, Any] | None,
    health_status: bool,
) -> None:
    """渲染低频功能折叠区。"""
    st.sidebar.divider()

    with st.sidebar.expander("模型与角色设置", expanded=False):
        if current_user is None:
            st.caption("选择演示用户后可设置模型和预设。")
        else:
            render_preset_and_model_controls(client)

    with st.sidebar.expander("会话操作", expanded=False):
        if current_user is None:
            st.caption("选择演示用户和会话后可管理会话。")
        else:
            render_session_action_controls(client)

    with st.sidebar.expander("导出", expanded=False):
        if current_user is None:
            st.caption("选择演示用户和会话后可导出。")
        else:
            render_export_controls(client)

    with st.sidebar.expander("多用户演示", expanded=False):
        render_user_controls(client)

    with st.sidebar.expander("高级设置 / 后端连接", expanded=False):
        new_base_url = st.text_input("FastAPI 地址", value=st.session_state.get("base_url", DEFAULT_BASE_URL))
        st.session_state["base_url"] = new_base_url
        if health_status:
            st.caption("后端连接正常。")
        else:
            st.caption("后端连接异常，请检查地址或服务状态。")


def small_hint(text: str) -> None:
    """显示弱化的小号说明文字。"""
    st.markdown(
        f"<div style='font-size: 12px; color: #8b8b8b; line-height: 1.45; margin: -0.35rem 0 0.45rem 0;'>{text}</div>",
        unsafe_allow_html=True,
    )


def render_session_action_controls(client: ApiClient) -> None:
    """当前会话的低频管理操作。"""
    message = st.session_state.pop("session_action_message", None)
    if message:
        st.success(message)

    session_id = st.session_state.get("current_session_id")
    if session_id is None:
        st.caption("当前没有可操作的会话。")
        return

    detail = safe_call(lambda: client.get_session(int(session_id)), None)
    if not detail:
        st.caption("当前会话不存在，请刷新后重试。")
        return

    session = detail["session"]
    title = session.get("title") or "新会话"
    st.caption(f"当前会话：{title}")
    small_hint("删除当前会话会同时删除该会话的聊天记录，请谨慎操作。")

    confirm_key = f"confirm_delete_session_{session_id}"
    confirmed = st.checkbox("我确认删除当前会话及其聊天记录", key=confirm_key)
    if st.button("删除当前会话", disabled=not confirmed, use_container_width=True):
        result = safe_action(lambda: client.delete_session(int(session_id)), "会话已删除")
        if result is not None:
            st.session_state.pop("current_session_id", None)
            st.session_state.pop(confirm_key, None)
            st.session_state["session_action_message"] = "会话已删除"
            st.rerun()


def render_user_controls(client: ApiClient) -> None:
    """多用户演示管理。"""
    small_hint("当前入口用于课程演示多用户隔离能力，真实产品中应替换为登录注册与权限鉴权。")

    users = safe_call(client.list_users, [])
    user_names = [user["username"] for user in users]
    user_by_name = {user["username"]: user for user in users}
    current_user = load_current_user(client)

    new_username = st.text_input("创建演示用户")
    if st.button("创建演示用户", use_container_width=True):
        if not new_username.strip():
            st.warning("用户名不能为空。")
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
        selected_name = st.selectbox("切换演示用户", user_names)
        if st.button("切换用户", use_container_width=True):
            user = safe_action(lambda: client.switch_user(username=selected_name), "用户切换成功")
            if user:
                st.session_state.pop("current_session_id", None)
            st.rerun()
    else:
        st.caption("暂无演示用户。")

    st.markdown("##### 删除演示用户")
    small_hint("⚠ 删除演示用户会同时删除该用户的会话和聊天记录，请谨慎操作。")
    if user_names:
        delete_name = st.selectbox("选择要删除的演示用户", user_names, key="delete_user_name")
        confirm_name = st.text_input("输入用户名确认删除", key="delete_user_confirm")
        can_delete = confirm_name.strip() == delete_name
        if st.button("删除演示用户", use_container_width=True, disabled=not can_delete):
            target_user = user_by_name[delete_name]
            result = safe_action(lambda: client.delete_user(int(target_user["id"])), "演示用户已删除")
            if result:
                if current_user is not None and current_user.get("id") == target_user.get("id"):
                    st.session_state.pop("current_session_id", None)
                    st.info("已删除当前演示用户，请重新选择演示用户。")
                st.rerun()
    else:
        st.caption("暂无可删除的演示用户。")


def render_preset_and_model_controls(client: ApiClient) -> None:
    """预设和模型选择。"""
    presets = safe_call(client.list_presets, [])
    preset_options: list[dict[str, Any] | None] = [None, *presets]
    current_preset_id = st.session_state.get("selected_preset_id")
    current_index = next(
        (
            index
            for index, preset in enumerate(preset_options)
            if preset is not None and preset.get("id") == current_preset_id
        ),
        0,
    )
    selected_preset = st.selectbox(
        "预设 Prompt",
        preset_options,
        index=current_index,
        format_func=format_preset_option,
    )
    st.session_state["selected_preset_id"] = None if selected_preset is None else selected_preset.get("id")

    models_payload = safe_call(client.list_models, {"models": [], "current_model": ""})
    models = models_payload.get("models", [])
    model_values = [model.get("value", "") for model in models if model.get("value")]
    if model_values:
        current_model = models_payload.get("current_model") or model_values[0]
        index = model_values.index(current_model) if current_model in model_values else 0
        st.session_state["selected_model"] = st.selectbox("模型", model_values, index=index)
    else:
        st.info("暂无模型配置。")
        st.session_state["selected_model"] = None


def format_preset_option(preset: dict[str, Any] | None) -> str:
    """预设下拉框只展示角色名称，不展示数据库 ID。"""
    if preset is None:
        return "不使用预设"
    return str(preset.get("name") or "未命名预设")

def get_preset_name(client: ApiClient, preset_id: int | None) -> str:
    """根据 preset_id 获取展示用角色名称，不向用户展示数据库 ID。"""
    if preset_id is None:
        return "未使用预设"
    presets = safe_call(client.list_presets, [])
    for preset in presets:
        if preset.get("id") == preset_id:
            return str(preset.get("name") or "未命名预设")
    return "未使用预设"

def render_search_controls(client: ApiClient) -> None:
    """侧边栏搜索历史消息。"""
    keyword = st.sidebar.text_input("搜索历史", placeholder="输入关键词")
    if keyword.strip():
        results = safe_call(lambda: client.search(keyword.strip()), [])
        st.session_state["search_results"] = results
    else:
        results = st.session_state.get("search_results", [])

    for result in results[:5]:
        content = str(result.get("content", "")).replace("\n", " ")[:64]
        session_id = result.get("session_id")
        if st.sidebar.button(f"会话 {session_id} · {content}", key=f"search_{result.get('message_id')}", use_container_width=True):
            st.session_state["current_session_id"] = session_id
            st.rerun()


def render_export_controls(client: ApiClient) -> None:
    """导出当前会话。"""
    session_id = st.session_state.get("current_session_id")
    if session_id is None:
        st.caption("请选择会话后再导出。")
        return
    if st.button("导出当前会话", use_container_width=True):
        result = safe_action(lambda: client.export_session(int(session_id)), "导出完成")
        if result:
            st.code(result.get("path", ""))


def ensure_current_session(client: ApiClient) -> int | None:
    """确保当前用户有一个可用会话，并返回会话 ID。"""
    current_id = st.session_state.get("current_session_id")
    sessions = safe_call(client.list_sessions, [])
    session_ids = {session.get("id") for session in sessions}

    if current_id in session_ids:
        return int(current_id)

    if sessions:
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
    title_col, action_col = st.columns([0.78, 0.22])
    with title_col:
        st.subheader(f"当前会话：{session.get('title') or '新会话'}")
        role_name = get_preset_name(client, session.get("preset_id"))
        st.caption(f"模型：{session.get('model_name')} · 角色：{role_name}")
    with action_col:
        if st.button("刷新", use_container_width=True):
            st.rerun()

    if not messages:
        st.info("这是一个新会话，直接在底部输入消息开始对话。")

    for message in messages:
        role = "assistant" if message.get("role") == "ai" else "user"
        with st.chat_message(role):
            st.write(message.get("content", ""))

    user_input = st.chat_input("输入消息，按发送开始对话")
    if user_input:
        maybe_auto_rename_session(
            client=client,
            session_id=session_id,
            current_title=session.get("title"),
            user_input=user_input,
            is_first_message=not messages,
        )
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            answer = ""
            try:
                for chunk in client.stream_chat(
                    session_id=session_id,
                    message=user_input,
                    preset_id=st.session_state.get("selected_preset_id"),
                    model_name=st.session_state.get("selected_model"),
                ):
                    answer += chunk
                    placeholder.markdown(answer)
            except Exception as exc:
                placeholder.error(f"流式接口调用失败：{exc}")
                return
        st.rerun()


def maybe_auto_rename_session(
    client: ApiClient,
    session_id: int,
    current_title: str | None,
    user_input: str,
    is_first_message: bool,
) -> None:
    """在默认标题会话的首轮提问后，使用用户第一条消息自动生成标题。"""
    if not is_first_message or not is_default_session_title(current_title):
        return

    new_title = build_session_title(user_input)
    if not new_title:
        return

    try:
        client.rename_session(session_id, new_title)
    except Exception as exc:
        st.caption(f"会话标题自动生成失败：{exc}")


def is_default_session_title(title: str | None) -> bool:
    """判断当前标题是否仍是系统默认标题。"""
    return (title or "").strip() in DEFAULT_SESSION_TITLES


def build_session_title(user_input: str) -> str:
    """根据用户首条消息生成简短标题。"""
    normalized = " ".join((user_input or "").strip().split())
    if len(normalized) <= AUTO_TITLE_MAX_LENGTH:
        return normalized
    return f"{normalized[:AUTO_TITLE_MAX_LENGTH]}..."


def load_current_user(client: ApiClient) -> dict[str, Any] | None:
    """读取当前用户。"""
    payload = safe_call(client.get_current_user, {"user": None})
    return payload.get("user") if payload else None


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
