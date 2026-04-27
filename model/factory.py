from abc import ABC, abstractmethod
from typing import Optional
import os

from dotenv import load_dotenv
load_dotenv()

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from project.config_hander import rag_conf
from project.logger_handler import logger

# 备用 LLM 客户端（通过环境变量配置，可选）
_fallback_client = None


def get_fallback_client():
    """获取备用 LLM 客户端实例（延迟初始化）。"""
    global _fallback_client
    if _fallback_client is None:
        fallback_key = os.environ.get("FALLBACK_API_KEY", "")
        fallback_url = os.environ.get("FALLBACK_BASE_URL", "")
        fallback_model = os.environ.get("FALLBACK_MODEL", "")
        if fallback_key and fallback_url and fallback_model:
            from project.llm_client import FallbackLLMClient
            primary_key = os.environ.get("DASHSCOPE_API_KEY", "")
            primary_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            primary_model = os.environ.get("DASHSCOPE_CHAT_MODEL", rag_conf.get("chat_model_name", "qwen-plus"))
            _fallback_client = FallbackLLMClient(
                primary_api_key=primary_key,
                primary_base_url=primary_url,
                primary_model_name=primary_model,
                fallback_api_key=fallback_key,
                fallback_base_url=fallback_url,
                fallback_model_name=fallback_model,
            )
            logger.info("备用 LLM 客户端已初始化。")
        else:
            logger.info("未配置备用 API，跳过容错客户端初始化。")
    return _fallback_client


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        pass

class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        model_name = os.environ.get("DASHSCOPE_CHAT_MODEL", rag_conf["chat_model_name"])
        return ChatTongyi(model=model_name)

class EmbeddingsFactory(BaseModelFactory):
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        model_name = os.environ.get("DASHSCOPE_EMBEDDING_MODEL", rag_conf["embedding_model"])
        return DashScopeEmbeddings(model=model_name)

chat_model=ChatModelFactory().generator()
embed_model=EmbeddingsFactory().generator()
