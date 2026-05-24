"""
KG增强RAG服务
整合 NER实体抽取 + KG图采样 + VS向量检索，生成增强上下文
"""
from pathlib import Path
from typing import Dict, List, Optional, Set, AsyncGenerator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

from rag.graph_sampler import GraphSampler, SampledSubgraph
from rag.vector_store import VectorStoreService
from rag.reranker import init_reranker, reranker as cross_encoder_reranker
from agent.knowledge.ner import health_ner
from model.factory import chat_model
from project.config_hander import chroma_conf, rag_conf
from project.logger_handler import logger


# KG增强RAG prompt文件路径
_KG_ENHANCED_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "rag_summarize_kg_enhanced.txt"


class KGEnhancedRAG:
    """KG增强RAG服务：融合知识图谱子图与向量检索结果"""

    def __init__(self):
        self.graph_sampler = GraphSampler()
        self.ner = health_ner
        self.model = chat_model

        # 初始化向量检索器
        self._vector_store = VectorStoreService()
        retriever_config = chroma_conf.get("retriever", {})
        search_type = retriever_config.get("search_type", "similarity")
        self.retriever = self._vector_store.get_retrive(search_type=search_type)

        # 初始化 Cross-Encoder Reranker
        reranker_cfg = rag_conf.get("reranker", {})
        if reranker_cfg.get("enabled", True):
            init_reranker(reranker_cfg)

        # 加载KG增强prompt
        self.prompt_text = self._load_kg_enhanced_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)

        # 构建chain
        self.chain = self.prompt_template | self.model | StrOutputParser()

        logger.info("[KGEnhancedRAG] KG增强RAG服务初始化完成")

    def _load_kg_enhanced_prompt(self) -> str:
        """加载KG增强prompt模板"""
        try:
            with open(str(_KG_ENHANCED_PROMPT_PATH), "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"[KGEnhancedRAG] 加载KG增强prompt失败: {e}，使用默认prompt")
            # 回退到基础prompt
            from project.prompt_loader import load_rag_prompts
            return load_rag_prompts()

    def query(self, query_str: str, chat_history: Optional[list] = None) -> str:
        """
        [DEPRECATED] 请使用 query_stream_async。
        KG增强RAG查询（同步，返回完整回答）
        """
        logger.info(f"[KGEnhancedRAG] 查询: {query_str}")

        kg_context, vs_context = self._prepare_context(query_str)

        if not kg_context and not vs_context:
            return "抱歉，知识库中没有找到与您问题相关的资料。请尝试换一种方式提问或提供更多信息。"

        if not kg_context:
            logger.info("[KGEnhancedRAG] 无KG上下文，使用纯VS检索")
            return self._pure_vs_query(query_str, vs_context, chat_history=chat_history)

        return self._generate_answer(query_str, kg_context, vs_context, chat_history=chat_history)

    def _prepare_context(self, query_str: str):
        """NER + 图采样 + 向量检索 + rerank，返回 (kg_context, vs_context)"""
        entities = self.ner.extract_entities(query_str)
        logger.info(f"[KGEnhancedRAG] NER抽取实体: {entities}")

        seed_nodes = [name for name, etype in entities if name]

        kg_context = ""
        if seed_nodes:
            subgraph = self.graph_sampler.sample(seed_nodes)
            if subgraph.text:
                kg_context = subgraph.text
                logger.info(
                    f"[KGEnhancedRAG] 图采样: {len(subgraph.nodes)}个节点, "
                    f"{len(subgraph.edges)}条边"
                )

        query_entity_names = {name for name, _ in entities}
        candidates = self._retrieve_vs_candidates(query_str, k=15)
        ranked_docs = self._rerank_by_kg_overlap(candidates, query_entity_names, top_k=5)

        if cross_encoder_reranker:
            reranked = cross_encoder_reranker.rerank(query_str, ranked_docs)
            ranked_docs = [doc for doc, score in reranked if score >= 0.3]
            if not ranked_docs:
                ranked_docs = candidates[:5]

        vs_context = "\n\n".join(doc.page_content for doc in ranked_docs) if ranked_docs else ""
        return kg_context, vs_context

    async def query_stream_async(
        self, query_str: str, chat_history: Optional[list] = None,
    ) -> AsyncGenerator[Dict, None]:
        """KG增强RAG查询（异步 token 级流式，yield SSE 事件字典）

        内部处理所有异常和回退逻辑，保证始终 yield done 事件。
        """
        import asyncio

        try:
            kg_context, vs_context = await asyncio.to_thread(self._prepare_context, query_str)

            if not kg_context and not vs_context:
                yield {"event": "message", "data": "抱歉，知识库中没有找到与您问题相关的资料。请尝试换一种方式提问或提供更多信息。"}
                yield {"event": "done", "data": ""}
                return

            if not kg_context:
                kg_context = "暂无相关知识图谱信息。"

            chain_input = {
                "input": query_str,
                "kg_context": kg_context,
                "vs_context": vs_context,
                "chat_history": self._format_chat_history(chat_history),
            }

            try:
                async for token in self.chain.astream(chain_input):
                    yield {"event": "message", "data": token}
            except Exception as stream_err:
                logger.error(f"[KGEnhancedRAG] 异步流式失败，回退同步: {stream_err}")
                try:
                    answer = self.chain.invoke(chain_input)
                    yield {"event": "message", "data": answer}
                except Exception as invoke_err:
                    logger.error(f"[KGEnhancedRAG] 同步回退也失败: {invoke_err}")
                    yield {"event": "error", "data": f"查询失败: {str(invoke_err)}"}

        except Exception as e:
            logger.error(f"[KGEnhancedRAG] query_stream_async 外层异常: {e}")
            yield {"event": "error", "data": f"查询失败: {str(e)}"}

        yield {"event": "done", "data": ""}

    def _retrieve_vs_candidates(self, query_str: str, k: int = 15) -> List[Document]:
        """向量检索获取候选文档（用于后续 rerank）"""
        try:
            retriever = self._vector_store.get_retrive(search_type="similarity", k=k)
            docs = retriever.invoke(query_str)
            logger.info(f"[KGEnhancedRAG] 向量检索到 {len(docs)} 个候选文档")
            return docs
        except Exception as e:
            logger.error(f"[KGEnhancedRAG] 向量检索失败: {e}")
            return []

    def _rerank_by_kg_overlap(
        self, docs: List[Document], query_entities: Set[str], top_k: int = 5
    ) -> List[Document]:
        """利用文档 metadata 中的 kg_entities 做 rerank"""
        if not query_entities:
            return docs[:top_k]

        scored = []
        for doc in docs:
            doc_entities = set(doc.metadata.get("kg_entities", []))
            overlap = len(query_entities & doc_entities)
            scored.append((overlap, doc))

        # 按 KG 实体重叠数降序，重叠数相同保持原始向量排序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def _pure_vs_query(self, query_str: str, vs_context: str, chat_history: Optional[list] = None) -> str:
        """纯VS回退查询（无KG上下文时使用）"""
        # 使用KG增强prompt，但kg_context留空
        try:
            return self.chain.invoke({
                "input": query_str,
                "kg_context": "暂无相关知识图谱信息。",
                "vs_context": vs_context,
                "chat_history": self._format_chat_history(chat_history),
            })
        except Exception as e:
            logger.error(f"[KGEnhancedRAG] 纯VS查询失败: {e}")
            return f"查询失败: {str(e)}"

    def _generate_answer(
        self,
        query_str: str,
        kg_context: str,
        vs_context: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """融合KG和VS上下文生成回答"""
        try:
            return self.chain.invoke({
                "input": query_str,
                "kg_context": kg_context,
                "vs_context": vs_context,
                "chat_history": self._format_chat_history(chat_history),
            })
        except Exception as e:
            logger.error(f"[KGEnhancedRAG] 生成回答失败: {e}")
            # 回退：如果有VS上下文，尝试纯VS
            if vs_context:
                return self._pure_vs_query(query_str, vs_context, chat_history=chat_history)
            return f"查询失败: {str(e)}"

    @staticmethod
    def _format_chat_history(chat_history: Optional[list]) -> str:
        """将对话历史格式化为文本"""
        if not chat_history:
            return "无"
        lines = []
        for m in chat_history:
            role = "用户" if m.get("role") == "user" else "助手"
            lines.append(f"{role}: {m.get('content', '')}")
        return "\n".join(lines)


if __name__ == "__main__":
    rag = KGEnhancedRAG()
    print(rag.query("高血压有什么症状"))
