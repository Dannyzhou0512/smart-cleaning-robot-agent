from langchain.agents import create_agent
from model.factory import chat_model
from Agent_project.utils.prompt_loader import load_system_prompts

from .tools.agent_tools import (
    rag_summarize,
    get_weather,
    get_current_location_weather,
    get_user_location,
    get_user_id,
    get_current_month,
    fetch_external_data,
    fill_context_for_report,
)

from agent.tools.middleware import (
    monitor_tool,
    log_before_model,
    report_prompt_switch,
)


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts).strip()

    return str(content).strip() if content else ""


def _shorten_text(text: str, max_length: int = 300) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[
            rag_summarize,
            get_weather,
            get_user_location,
            get_user_id,
            get_current_month,
            fetch_external_data,
            fill_context_for_report,
            get_current_location_weather,
            ],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )
        self.last_process_steps: list[dict] = []

    def clear_last_process_steps(self) -> None:
        self.last_process_steps = []

    def get_last_process_steps(self) -> list[dict]:
        return self.last_process_steps

    def _append_process_step(self, title: str, content: str) -> dict | None:
        if not content:
            return None

        step = {
            "title": title,
            "content": content,
        }
        self.last_process_steps.append(step)
        return step

    def execute_events(self, query: str, history_messages: list[dict] | None = None):
        self.clear_last_process_steps()
        messages = []

        for message in history_messages or []:
            role = message.get("role")
            content = message.get("content", "")

            if role in {"user", "assistant"} and content:
                messages.append({
                    "role": role,
                    "content": content,
                })

        messages.append({
            "role": "user",
            "content": query,
        })

        input_dict = {
            "messages": messages
        }
        # 第三个参数context就是上下文runtime中的信息，就是我们做提示词切换的标记
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            message_type = type(latest_message).__name__
            content = _content_to_text(getattr(latest_message, "content", ""))

            if message_type == "HumanMessage":
                continue

            tool_calls = getattr(latest_message, "tool_calls", None) or []
            if tool_calls:
                step = self._append_process_step("模型判断", content)
                if step:
                    yield {
                        "type": "process",
                        "step": step,
                    }

                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "未知工具")
                    tool_args = tool_call.get("args", {})
                    step = self._append_process_step(
                        "工具调用",
                        f"{tool_name}，参数：{tool_args}",
                    )
                    if step:
                        yield {
                            "type": "process",
                            "step": step,
                        }
                continue

            if message_type == "ToolMessage":
                tool_name = getattr(latest_message, "name", "工具")
                step = self._append_process_step(
                    "工具结果",
                    f"{tool_name} 返回完成。{_shorten_text(content)}",
                )
                if step:
                    yield {
                        "type": "process",
                        "step": step,
                    }
                continue

            if content:
                yield {
                    "type": "answer",
                    "content": content + "\n",
                }

    def execute_stream(self, query: str, history_messages: list[dict] | None = None):
        for event in self.execute_events(query, history_messages=history_messages):
            if event.get("type") == "answer":
                yield event.get("content", "")


if __name__ == '__main__':
    agent = ReactAgent()
    # for chunk in agent.execute_stream("扫地机器人在我所在的地区的气温下如何保养"):
    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)

