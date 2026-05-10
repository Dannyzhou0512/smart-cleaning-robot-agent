"""
总结服务类：用户提问，搜索参考资料，将提问和参考资料提交给模型，让模型总结回复
"""
import os
import re

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from Agent_project.utils.prompt_loader import load_rag_prompts
from model.factory import chat_model
from rag.vector_store import VectorStoreService


def print_prompt(prompt):
    print("="*20)
    print(prompt.to_string())
    print("="*20)
    return prompt


def _build_content_summary(content: str, max_length: int = 160) -> str:
    summary = re.sub(r"\s+", " ", content or "").strip()

    if len(summary) <= max_length:
        return summary

    return f"{summary[:max_length]}..."


def _normalize_score(score: float | None) -> float | None:
    if score is None:
        return None

    try:
        return round(float(score), 4)
    except (TypeError, ValueError):
        return None


def _build_source_item(doc: Document, score: float | None, index: int) -> dict:
    metadata = dict(doc.metadata or {})
    source_path = metadata.get("source") or metadata.get("file_path") or metadata.get("path") or ""
    document_name = os.path.basename(str(source_path)) if source_path else f"参考资料{index}"

    return {
        "index": index,
        "document_name": document_name,
        "summary": _build_content_summary(doc.page_content),
        "metadata": metadata,
        "similarity_score": _normalize_score(score),
    }


class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()
        self.last_sources: list[dict] = []

    def _init_chain(self):
        chain = self.prompt_template | print_prompt | self.model | StrOutputParser()
        return chain

    def retriever_docs(self, query : str) -> list[Document]:
        return self.retriever.invoke(query)

    def retriever_docs_with_scores(self, query: str) -> list[tuple[Document, float | None]]:
        return self.vector_store.similarity_search_with_scores(query)

    def clear_last_sources(self) -> None:
        self.last_sources = []

    def get_last_sources(self) -> list[dict]:
        return self.last_sources

    def rag_summarize(self, query : str) -> str:
        context_docs = self.retriever_docs_with_scores(query)
        context = ""
        self.clear_last_sources()

        for counter, (doc, score) in enumerate(context_docs, start=1):
            source_item = _build_source_item(doc, score, counter)
            self.last_sources.append(source_item)
            score_text = source_item["similarity_score"]
            context += (
                f"【参考资料{counter}:】"
                f"参考资料:{doc.page_content}|"
                f"参考元数据:{doc.metadata}|"
                f"相似度分数:{score_text if score_text is not None else '未知'}\n"
            )

        return self.chain.invoke(
            {
                "input": query,
                "context": context
            }
        )



if __name__ == '__main__':
    rag = RagSummarizeService()
    print(rag.rag_summarize("大户型合适的扫地机器人"))


