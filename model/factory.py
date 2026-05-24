from abc import ABC, abstractmethod
from typing import Optional
import os

from dotenv import load_dotenv
load_dotenv()

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from project.config_hander import rag_conf
from project.logger_handler import logger


class _FallbackLogCallback(BaseCallbackHandler):
    """记录 fallback 切换事件"""
    def on_llm_error(self, error, *, run_id, **kwargs):
        logger.warning(f"[LLM主备] 模型调用失败: {error}")

    def on_llm_start(self, serialized, prompts, *, run_id, **kwargs):
        model = serialized.get("kwargs", {}).get("model", serialized.get("name", "unknown"))
        logger.debug(f"[LLM主备] 调用模型: {model}")


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        pass

class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        model_name = os.environ.get("DASHSCOPE_CHAT_MODEL", rag_conf["chat_model_name"])
        primary = ChatTongyi(model=model_name)

        fallback_url = os.environ.get("FALLBACK_BASE_URL", "")
        fallback_key = os.environ.get("FALLBACK_API_KEY", "")
        fallback_model = os.environ.get("FALLBACK_MODEL", "")

        if fallback_url and fallback_key and fallback_model:
            fallback = ChatOpenAI(
                model=fallback_model,
                api_key=fallback_key,
                base_url=fallback_url,
                max_retries=0,
                callbacks=[_FallbackLogCallback()],
            )
            logger.info(
                f"[LLM主备] 已配置备用模型: {fallback_model} @ {fallback_url}"
            )
            return primary.with_fallbacks([fallback])

        logger.info("[LLM主备] 未配置备用 API，仅使用主模型")
        return primary

class EmbeddingsFactory(BaseModelFactory):
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        model_name = os.environ.get("DASHSCOPE_EMBEDDING_MODEL", rag_conf["embedding_model"])
        return DashScopeEmbeddings(model=model_name)

chat_model=ChatModelFactory().generator()
embed_model=EmbeddingsFactory().generator()
