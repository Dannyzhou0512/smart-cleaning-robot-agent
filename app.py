import time
import streamlit as st
from agent.react_agent import ReactAgent

from streamlit_js_eval import get_geolocation

from Agent_project.utils.location_service import (
    reverse_geocode_by_amap,
    format_location_text,
)

from agent.tools.agent_tools import (
    clear_last_query_rewrite,
    clear_last_rag_sources,
    get_last_query_rewrite,
    get_last_rag_sources,
    set_conversation_memory_context,
    set_user_location_context,
)


AGENT_SESSION_VERSION = "query_rewrite_v1"
MEMORY_TURNS = 20


CURRENT_LOCATION_KEYWORDS = (
    "我这里",
    "我这边",
    "我所在",
    "当前位置",
    "当前地区",
    "当前城市",
    "本地",
    "当地",
    "附近",
    "周边",
    "这边",
    "这里",
)


def should_attach_location_context(user_prompt: str) -> bool:
    """仅在用户明确询问当前位置/本地场景时附加定位上下文。"""
    return any(keyword in user_prompt for keyword in CURRENT_LOCATION_KEYWORDS)


def render_rag_sources(sources: list[dict] | None) -> None:
    if not sources:
        return

    with st.expander("参考来源", expanded=False):
        for source in sources:
            index = source.get("index", "")
            document_name = source.get("document_name", "未知文档")
            score = source.get("relevance_score", source.get("similarity_score"))
            score_text = "未知" if score is None else str(score)

            st.markdown(f"**{index}. 命中文档：{document_name}**")
            st.write(f"相关性分数：{score_text}")
            st.write(f"片段摘要：{source.get('summary', '')}")

            metadata = source.get("metadata") or {}
            if metadata:
                st.write("metadata：")
                st.json(metadata, expanded=False)


def render_process_steps(process_steps: list[dict] | None) -> None:
    if not process_steps:
        return

    with st.expander("处理过程", expanded=False):
        for index, step in enumerate(process_steps, start=1):
            title = step.get("title", "步骤")
            content = step.get("content", "")
            st.markdown(f"**{index}. {title}**")
            st.write(content)


def render_live_process_steps(process_steps: list[dict], target) -> None:
    target.empty()

    if not process_steps:
        return

    with target.container():
        st.markdown("**处理过程**")
        for index, step in enumerate(process_steps, start=1):
            title = step.get("title", "步骤")
            content = step.get("content", "")
            st.markdown(f"**{index}. {title}**")
            st.write(content)


def build_short_term_memory(messages: list[dict], max_turns: int = MEMORY_TURNS) -> list[dict]:
    memory_messages = []

    for message in messages:
        role = message.get("role")
        content = message.get("content", "")

        if role in {"user", "assistant"} and content:
            memory_messages.append({
                "role": role,
                "content": content,
            })

    return memory_messages[-max_turns * 2:]


def append_query_rewrite_step(process_steps: list[dict], query_rewrite: dict | None) -> list[dict]:
    if not query_rewrite:
        return process_steps

    original_query = query_rewrite.get("original_query", "")
    rewritten_query = query_rewrite.get("rewritten_query", "")

    if not original_query or not rewritten_query:
        return process_steps

    content = (
        f"原始检索词：{original_query}\n\n"
        f"改写后检索词：{rewritten_query}"
    )

    rewrite_step = {
        "title": "RAG查询改写",
        "content": content,
    }

    for index, step in enumerate(process_steps):
        if step.get("title") == "工具调用" and "rag_summarize" in step.get("content", ""):
            return process_steps[:index + 1] + [rewrite_step] + process_steps[index + 1:]

    return [rewrite_step] + process_steps


# 标题
st.title("智能扫地机器人")
st.divider()

#定位模块
st.sidebar.title("用户设置")

st.sidebar.subheader("当前位置")

geo_location = get_geolocation()

if geo_location and "coords" in geo_location:
    coords = geo_location["coords"]
    latitude = coords.get("latitude")
    longitude = coords.get("longitude")

    if latitude is not None and longitude is not None:
        location_info = reverse_geocode_by_amap(
            longitude=longitude,
            latitude=latitude,
        )

        if location_info.get("success"):
            st.session_state["location_info"] = location_info
            set_user_location_context(location_info)

            location_text = format_location_text(location_info)
            st.sidebar.success(location_text)
        else:
            st.sidebar.warning(location_info.get("message", "定位解析失败"))
else:
    st.sidebar.info("浏览器定位未授权或暂未获取到，将使用 IP 城市定位兜底。")

#如果智能体不在这个列表里面则重新创建智能体
if st.session_state.get("agent_session_version") != AGENT_SESSION_VERSION:
    st.session_state["agent"] = ReactAgent()
    st.session_state["agent_session_version"] = AGENT_SESSION_VERSION

# 这个session_state相当于是一个全局的记忆盒子
if "messages" not in st.session_state:
    st.session_state["messages"] = []

#每次脚本刷新代码都会遍历messages所有的历史记录，按照顺寻重新渲染在页面上
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_process_steps(message.get("process_steps"))
            st.write(message["content"])
            render_rag_sources(message.get("sources"))
        else:
            st.write(message["content"])

prompt = st.chat_input()

if prompt:
    history_messages = build_short_term_memory(st.session_state["messages"])
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    response_messages = []

    with st.spinner("智能客服思考中..."):
        clear_last_rag_sources()
        clear_last_query_rewrite()
        set_conversation_memory_context(history_messages)

        location_context = ""

        if "location_info" in st.session_state:
            location_context = format_location_text(st.session_state["location_info"])

        agent_prompt = prompt

        if location_context and should_attach_location_context(prompt):
            agent_prompt = (
                f"【用户当前位置】{location_context}\n"
                f"位置使用规则：仅当用户询问当前位置、本地、附近、当地等场景时使用该定位信息；"
                f"如果用户问题明确指定了其他城市或地区，必须以用户指定地区为准。\n\n"
                f"用户问题：{prompt}"
            )

        with st.chat_message("assistant"):
            process_steps = []
            answer_text = ""
            process_slot = st.empty()
            answer_slot = st.empty()

            for event in st.session_state["agent"].execute_events(
                agent_prompt,
                history_messages=history_messages,
            ):
                event_type = event.get("type")

                if event_type == "process":
                    step = event.get("step")
                    if step:
                        process_steps.append(step)
                        render_live_process_steps(process_steps, process_slot)

                if event_type == "answer":
                    chunk = event.get("content", "")
                    response_messages.append(chunk)

                    for char in chunk:
                        answer_text += char
                        answer_slot.markdown(answer_text)
                        time.sleep(0.01)

            process_steps = st.session_state["agent"].get_last_process_steps()
            query_rewrite = get_last_query_rewrite()
            process_steps = append_query_rewrite_step(process_steps, query_rewrite)
            rag_sources = get_last_rag_sources()

            process_slot.empty()
            with process_slot.container():
                render_process_steps(process_steps)

            render_rag_sources(rag_sources)

        full_response = "".join(response_messages)

        st.session_state["messages"].append({
            "role": "assistant",
            "content": full_response,
            "process_steps": process_steps,
            "sources": rag_sources,
        })

        st.rerun()



