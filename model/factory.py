from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

from Agent_project.utils.config_handler import rag_config, agents_config


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self):
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> BaseChatModel:
        return ChatTongyi(
            model=agents_config["chat_model_name"]
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Embeddings:
        return DashScopeEmbeddings(
            model=agents_config["embedding_model_name"]
        )


chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()