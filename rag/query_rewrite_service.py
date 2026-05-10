from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from Agent_project.utils.logger_handler import logger
from Agent_project.utils.prompt_loader import load_query_rewrite_prompts
from model.factory import chat_model


class QueryRewriteService:
    def __init__(self):
        self.prompt_template = PromptTemplate.from_template(load_query_rewrite_prompts())
        self.chain = self.prompt_template | chat_model | StrOutputParser()

    def rewrite(self, query: str, history_messages: list[dict], history_limit: int = 6) -> str:
        if not history_messages:
            return query

        history = self._format_history(history_messages[-history_limit:])

        if not history:
            return query

        try:
            rewritten_query = self.chain.invoke({
                "history": history,
                "query": query,
            }).strip()
        except Exception as e:
            logger.warning(f"[RAG查询改写]查询改写失败，使用原始query: {e}")
            return query

        return rewritten_query or query

    def _format_history(self, history_messages: list[dict]) -> str:
        lines = []

        for message in history_messages:
            role = message.get("role")
            content = " ".join(str(message.get("content", "")).split())

            if not content:
                continue

            if role == "user":
                lines.append(f"用户：{content}")
            elif role == "assistant":
                lines.append(f"助手：{content}")

        return "\n".join(lines)
