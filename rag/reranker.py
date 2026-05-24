"""DashScope Reranker 模块"""
__all__ = ["DashScopeReranker", "init_reranker", "reranker"]

import dashscope
from http import HTTPStatus
from typing import List, Tuple
from langchain_core.documents import Document
from project.logger_handler import logger


class DashScopeReranker:
    """基于 DashScope gte-rerank-v2 的文档重排序器"""

    def __init__(self, model: str = "gte-rerank-v2", top_n: int = 5):
        self.model = model
        self.top_n = top_n

    def rerank(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """
        对文档列表进行重排序

        Returns:
            [(Document, relevance_score), ...] 按 score 降序
        """
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        try:
            resp = dashscope.TextReRank.call(
                model=self.model,
                query=query,
                documents=texts,
                top_n=self.top_n,
                return_documents=False,
            )
            if resp.status_code != HTTPStatus.OK:
                logger.warning(f"[Reranker] API 调用失败: {resp.code} - {resp.message}")
                return [(doc, 1.0) for doc in documents[:self.top_n]]

            results = resp.output.get("results", [])
            reranked = []
            for r in results:
                idx = r["index"]
                score = r["relevance_score"]
                reranked.append((documents[idx], score))
            return reranked

        except Exception as e:
            logger.warning(f"[Reranker] rerank 失败，使用原始排序: {e}")
            return [(doc, 1.0) for doc in documents[:self.top_n]]


# 全局单例
reranker = None


def init_reranker(config: dict):
    global reranker
    enabled = config.get("enabled", True)
    if not enabled:
        reranker = None
        return
    reranker = DashScopeReranker(
        model=config.get("model", "gte-rerank-v2"),
        top_n=config.get("top_n", 5),
    )
    logger.info(f"[Reranker] 初始化完成, model={reranker.model}, top_n={reranker.top_n}")
