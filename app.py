import time
import streamlit as st
from agent.react_agent import ReactAgent

from streamlit_js_eval import get_geolocation

from Agent_project.utils.location_service import (
    reverse_geocode_by_amap,
    format_location_text,
)

from agent.tools.agent_tools import set_user_location_context


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
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

# 这个session_state相当于是一个全局的记忆盒子
if "messages" not in st.session_state:
    st.session_state["messages"] = []

#每次脚本刷新代码都会遍历messages所有的历史记录，按照顺寻重新渲染在页面上
for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input()

if prompt:
    # 1. 立即在界面显示用户的问题，并存入历史
    st.chat_message("user").write(prompt)
    st.session_state["messages"].append({"role":"user","content":prompt})

    response_messages = []
    with st.spinner("智能客服思考中..."):

        #页面上仍然显示用户原始问题 prompt，只是传给 Agent 的内容多了定位上下文
        #接受数据流
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

        res_stream = st.session_state["agent"].execute_stream(agent_prompt)
        def capture(generator,cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                for char in chunk:
                    time.sleep(0.01)
                    yield char

        st.chat_message("assistant").write_stream(capture(res_stream,response_messages))
        st.session_state["messages"].append({"role":"assistant","content":response_messages[-1]})
        st.rerun()



