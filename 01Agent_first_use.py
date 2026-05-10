from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool

@tool(description="查询天气")
def get_weather() -> str:
    return "阴天"

agent = create_agent(
    model = ChatTongyi(model = "qwen3-max"),    #智能体的大脑LLM
    tools = [get_weather],     #向智能体提供工具列表
    system_prompt="你是一个聊天助手，可以回答用户的问题",
)

res = agent.invoke(
    {
        "messages": [
            {"role":"user","content":"明天上海的天气如何，多少度？"}
  ]
    }
)

for msg in res["messages"]:
    print(type(msg).__name__,msg.content)