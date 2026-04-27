"""
核心路由器 - 根据意图分发请求

路由策略：
- FAQ问答 → 直接走 RAG + KG 查询
- Agent处理 → 调用 HealthAgent（支持工具调用）

优化：
- FAQ问答响应快，不走 LLM tool-calling
- Agent处理支持复杂任务和多轮对话
"""
import json
from typing import Dict, Generator, List, Optional
from project.logger_handler import logger

from agent.router.intent_classifier import IntentClassifier, intent_classifier
from agent.core.health_agent import HealthAgent, health_agent
from agent.knowledge.kg_qa import KGQA, kg_qa
from rag.rag_service import RagSummarizeService
from rag.kg_enhanced_rag import KGEnhancedRAG


class HealthRouter:
    """
    健康路由器

    根据用户意图智能分发请求到不同服务
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.health_agent = HealthAgent()
        self.kg_qa = kg_qa
        self._rag_service = None  # 延迟初始化
        self._kg_enhanced_rag = None  # KG增强RAG延迟初始化
        logger.info("[HealthRouter] 路由器初始化完成")

    @property
    def rag_service(self) -> RagSummarizeService:
        """延迟初始化 RAG 服务"""
        if self._rag_service is None:
            self._rag_service = RagSummarizeService()
        return self._rag_service

    @property
    def kg_enhanced_rag(self) -> KGEnhancedRAG:
        """延迟初始化 KG增强RAG 服务"""
        if self._kg_enhanced_rag is None:
            self._kg_enhanced_rag = KGEnhancedRAG()
        return self._kg_enhanced_rag

    def route(self, query: str, history: Optional[List[Dict]] = None) -> Dict:
        """
        路由请求（非流式）

        Args:
            query: 用户输入
            history: 对话历史（可选）

        Returns:
            包含回答和元数据的字典
        """
        # 1. 意图分类
        intent_result = self.intent_classifier.classify(query)
        logger.info(f"[HealthRouter] 意图分类: {intent_result.intent}, 置信度: {intent_result.confidence}")

        # 2. 路由执行
        if intent_result.intent == "faq":
            return self._route_faq(query, intent_result, history=history)
        else:
            return self._route_agent(query, intent_result, history=history)

    def route_stream(self, query: str, history: Optional[List[Dict]] = None) -> Generator[Dict, None, None]:
        """
        路由请求（流式输出）

        Args:
            query: 用户输入
            history: 对话历史（可选）

        Yields:
            流式事件字典 {"event": "xxx", "data": "xxx"}
        """
        # 1. 意图分类
        intent_result = self.intent_classifier.classify(query)
        logger.info(f"[HealthRouter] 意图分类: {intent_result.intent}, 置信度: {intent_result.confidence}")

        # 2. 路由执行
        if intent_result.intent == "faq":
            # FAQ: 先发送意图信息，然后发送KG数据和RAG回答
            yield {"event": "intent", "data": json.dumps({
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
                "matched_pattern": intent_result.matched_pattern
            }, ensure_ascii=False)}

            # KG查询获取图谱数据
            kg_result = self.kg_qa.answer(query)
            relations = kg_result.get("relations", [])

            if relations:
                graph_data = {
                    "answer": kg_result.get("answer", ""),
                    "relations": relations,
                    "confidence": kg_result.get("confidence", 0)
                }
                yield {"event": "graph_data", "data": json.dumps(graph_data, ensure_ascii=False)}

            # KG增强RAG回答
            try:
                rag_answer = self.kg_enhanced_rag.query(query, chat_history=history)
                yield {"event": "message", "data": rag_answer}
            except Exception as e:
                logger.error(f"[HealthRouter] KG增强RAG查询失败: {e}")
                # KG增强RAG失败时回退到基础RAG
                try:
                    rag_answer = self.rag_service.rag_summarize(query)
                    yield {"event": "message", "data": rag_answer}
                except Exception as e2:
                    logger.error(f"[HealthRouter] 基础RAG也失败: {e2}")
                    if kg_result.get("answer"):
                        yield {"event": "message", "data": kg_result.get("answer")}
                    else:
                        yield {"event": "message", "data": f"查询失败: {str(e)}"}

            yield {"event": "done", "data": ""}

        else:
            # Agent: 调用 health_agent，支持工具调用（不发送 intent/graph_data，只输出结果）
            logger.info(f"[HealthRouter] Agent路径，跳过KG查询，直接调用health_agent")

            # 流式输出 Agent 对话
            try:
                for chunk in self.health_agent.chat(query, history=history):
                    yield {"event": "message", "data": chunk}
            except Exception as e:
                logger.error(f"[HealthRouter] Agent对话失败: {e}")
                yield {"event": "error", "data": str(e)}

            yield {"event": "done", "data": ""}

    def _route_faq(self, query: str, intent_result, history: Optional[List[Dict]] = None) -> Dict:
        """FAQ路由 - 快速响应"""
        result = {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "matched_pattern": intent_result.matched_pattern
        }

        # KG查询
        kg_result = self.kg_qa.answer(query)
        result["kg_data"] = {
            "answer": kg_result.get("answer"),
            "relations": kg_result.get("relations", []),
            "confidence": kg_result.get("confidence", 0)
        }

        # KG增强RAG回答
        try:
            result["answer"] = self.kg_enhanced_rag.query(query, chat_history=history)
        except Exception as e:
            logger.error(f"[HealthRouter] KG增强RAG失败: {e}")
            # KG增强RAG失败时回退到基础RAG
            try:
                result["answer"] = self.rag_service.rag_summarize(query)
            except Exception as e2:
                logger.error(f"[HealthRouter] 基础RAG也失败: {e2}")
                result["answer"] = kg_result.get("answer", f"查询失败: {str(e)}")

        return result

    def _route_agent(self, query: str, intent_result, history: Optional[List[Dict]] = None) -> Dict:
        """Agent路由 - 支持复杂任务"""
        result = {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "is_complex": intent_result.is_complex,
            "matched_pattern": intent_result.matched_pattern
        }

        # KG查询（获取图谱数据）
        kg_result = self.kg_qa.answer(query)
        result["kg_data"] = {
            "answer": kg_result.get("answer"),
            "relations": kg_result.get("relations", []),
            "confidence": kg_result.get("confidence", 0)
        }

        # Agent对话
        answer_parts = []
        try:
            for chunk in self.health_agent.chat(query, history=history):
                answer_parts.append(chunk)
            result["answer"] = "".join(answer_parts)
        except Exception as e:
            logger.error(f"[HealthRouter] Agent失败: {e}")
            result["answer"] = f"对话失败: {str(e)}"
            result["error"] = str(e)

        return result

    def analyze(self, query: str) -> Dict:
        """
        分析意图（诊断接口）

        用于调试和查看路由决策
        """
        intent_result = self.intent_classifier.classify(query)
        return {
            "query": query,
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "is_complex": intent_result.is_complex,
            "matched_pattern": intent_result.matched_pattern
        }


# 全局路由器实例
health_router = HealthRouter()