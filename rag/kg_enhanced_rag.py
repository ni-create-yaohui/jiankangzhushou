"""
KG增强RAG服务
整合 NER实体抽取 + KG图采样 + VS向量检索，生成增强上下文
"""
from pathlib import Path
from typing import Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from rag.graph_sampler import GraphSampler, SampledSubgraph
from rag.vector_store import VectorStoreService
from agent.knowledge.ner import health_ner
from model.factory import chat_model
from project.config_hander import chroma_conf
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
        KG增强RAG查询

        流程:
        1. NER实体抽取 → 种子节点
        2. 图采样 → KG子图文本
        3. 向量检索 → VS chunks
        4. 上下文融合 → 增强context
        5. LLM生成 → 回答

        Args:
            query_str: 用户查询
            chat_history: 对话历史（可选），格式为 [{"role": "user/assistant", "content": "..."}]

        Returns:
            回答文本
        """
        logger.info(f"[KGEnhancedRAG] 查询: {query_str}")

        # 1. NER实体抽取
        entities = self.ner.extract_entities(query_str)
        logger.info(f"[KGEnhancedRAG] NER抽取实体: {entities}")

        # 2. 种子节点确定
        seed_nodes = [name for name, etype in entities if name]

        # 3. 图采样（如果有种子节点）
        kg_context = ""
        if seed_nodes:
            subgraph = self.graph_sampler.sample(seed_nodes)
            if subgraph.text:
                kg_context = subgraph.text
                logger.info(
                    f"[KGEnhancedRAG] 图采样: {len(subgraph.nodes)}个节点, "
                    f"{len(subgraph.edges)}条边"
                )

        # 4. 向量检索
        vs_context = self._retrieve_vs_context(query_str)

        # 5. 回退逻辑：如果两者都为空，返回提示
        if not kg_context and not vs_context:
            return "抱歉，知识库中没有找到与您问题相关的资料。请尝试换一种方式提问或提供更多信息。"

        # 6. 如果只有VS结果（NER未识别实体或图谱无匹配），回退到纯VS
        if not kg_context:
            logger.info("[KGEnhancedRAG] 无KG上下文，使用纯VS检索")
            return self._pure_vs_query(query_str, vs_context, chat_history=chat_history)

        # 7. 上下文融合 + LLM生成
        return self._generate_answer(query_str, kg_context, vs_context, chat_history=chat_history)

    def _retrieve_vs_context(self, query_str: str) -> str:
        """向量检索获取VS上下文"""
        try:
            docs = self.retriever.invoke(query_str)
            if not docs:
                return ""
            context = "\n\n".join(doc.page_content for doc in docs)
            logger.info(f"[KGEnhancedRAG] VS检索到 {len(docs)} 个文档片段")
            return context
        except Exception as e:
            logger.error(f"[KGEnhancedRAG] VS检索失败: {e}")
            return ""

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
