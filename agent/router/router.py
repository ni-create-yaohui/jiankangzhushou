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
from typing import Dict, Generator, AsyncGenerator, List, Optional
from project.logger_handler import logger
from project.config_hander import dynamic_prompts_conf

from agent.router.intent_classifier import IntentClassifier, intent_classifier
from agent.core.health_agent import HealthAgent, health_agent
from agent.knowledge.kg_qa import KGQA, kg_qa
from rag.rag_service import RagSummarizeService
from rag.kg_enhanced_rag import KGEnhancedRAG

# 动态提示词预处理组件
from agent.preprocessing.input_denoiser import input_denoiser, init_denoiser
from agent.preprocessing.prompt_matcher import prompt_matcher, init_prompt_matcher
from agent.preprocessing.dynamic_prompt_builder import dynamic_prompt_builder, init_dynamic_prompt_builder
from agent.preprocessing.query_rewriter import query_rewriter, init_query_rewriter

# 初始化预处理组件
def _init_preprocessing():
    cfg = dynamic_prompts_conf or {}
    denoiser_cfg = cfg.get("denoiser", {})
    if denoiser_cfg.get("enabled", True):
        init_denoiser(denoiser_cfg)
    rules = cfg.get("prompt_rules", [])
    if rules:
        init_prompt_matcher(rules)
    ctx_cfg = cfg.get("dynamic_context", {})
    if ctx_cfg.get("enabled", True):
        init_dynamic_prompt_builder(ctx_cfg)
    # CQR 查询改写器
    cqr_cfg = cfg.get("cqr", {})
    if cqr_cfg.get("enabled", True):
        init_query_rewriter(cqr_cfg)

_init_preprocessing()


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

    def route(self, query: str, history: Optional[List[Dict]] = None, original_query: str = None) -> Dict:
        """
        路由请求（非流式）

        Args:
            query: 用户输入（已去噪）
            history: 对话历史（可选）
            original_query: 原始用户输入（去噪前）

        Returns:
            包含回答和元数据的字典
        """
        # 1. 意图分类 — 用原始去噪文本
        intent_result = self.intent_classifier.classify(query)
        logger.info(f"[HealthRouter] 意图分类: {intent_result.intent}, 置信度: {intent_result.confidence}")

        # 2. 路由执行
        if intent_result.intent == "faq":
            # FAQ路径：启用CQR改写，解决指代消解问题
            rewritten_query = self._rewrite_query(query, history)
            return self._route_faq(rewritten_query, intent_result, history=history)
        else:
            # Agent路径：CQR改写 → 用改写文本做 prompt匹配和 agent执行
            rewritten_query = self._rewrite_query(query, history)
            dynamic_context = self._build_dynamic_context(rewritten_query, original_query, history)
            return self._route_agent(rewritten_query, intent_result, history=history, dynamic_context=dynamic_context)

    def route_stream(self, query: str, history: Optional[List[Dict]] = None, original_query: str = None) -> Generator[Dict, None, None]:
        """
        [DEPRECATED] 请使用 route_stream_async。
        路由请求（同步流式输出）

        Args:
            query: 用户输入（已去噪）
            history: 对话历史（可选）
            original_query: 原始用户输入（去噪前）

        Yields:
            流式事件字典 {"event": "xxx", "data": "xxx"}
        """
        # 1. 意图分类 — 用原始去噪文本
        intent_result = self.intent_classifier.classify(query)
        logger.info(f"[HealthRouter] 意图分类: {intent_result.intent}, 置信度: {intent_result.confidence}")

        # 2. 路由执行
        if intent_result.intent == "faq":
            # FAQ路径：启用CQR改写，解决指代消解问题
            rewritten_query = self._rewrite_query(query, history)
            logger.info(f"[HealthRouter] FAQ路径 CQR改写: query={query[:30]}, rewritten={rewritten_query[:30]}")

            yield {"event": "intent", "data": json.dumps({
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
                "matched_pattern": intent_result.matched_pattern
            }, ensure_ascii=False)}

            # KG查询获取图谱数据
            kg_result = self.kg_qa.answer(rewritten_query)
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
                rag_answer = self.kg_enhanced_rag.query(rewritten_query, chat_history=history)
                yield {"event": "message", "data": rag_answer}
            except Exception as e:
                logger.error(f"[HealthRouter] KG增强RAG查询失败: {e}")
                # KG增强RAG失败时回退到基础RAG
                try:
                    rag_answer = self.rag_service.rag_summarize(rewritten_query)
                    yield {"event": "message", "data": rag_answer}
                except Exception as e2:
                    logger.error(f"[HealthRouter] 基础RAG也失败: {e2}")
                    if kg_result.get("answer"):
                        yield {"event": "message", "data": kg_result.get("answer")}
                    else:
                        yield {"event": "message", "data": f"查询失败: {str(e)}"}

            yield {"event": "done", "data": ""}

        else:
            # Agent路径：CQR改写 → 用改写文本做 prompt匹配和 agent执行
            rewritten_query = self._rewrite_query(query, history)
            dynamic_context = self._build_dynamic_context(rewritten_query, original_query, history)

            logger.info(f"[HealthRouter] Agent路径 (query={query[:30]}, rewritten={rewritten_query[:30]})")

            # 流式输出 Agent 对话（用改写文本）
            try:
                for chunk in self.health_agent.chat(rewritten_query, history=history, dynamic_context=dynamic_context):
                    yield {"event": "message", "data": chunk}
            except Exception as e:
                logger.error(f"[HealthRouter] Agent对话失败: {e}")
                yield {"event": "error", "data": str(e)}

            yield {"event": "done", "data": ""}

    async def route_stream_async(
        self, query: str, history: Optional[List[Dict]] = None, original_query: str = None,
    ) -> AsyncGenerator[Dict, None]:
        """路由请求（异步流式，token 级 + 中间步骤）

        事件协议：
        - router:intent    — 意图分类结果（Router 层发出）
        - router:graph_data — 知识图谱数据（Router 层发出）
        - thinking         — 工具调用中间状态（Agent 层发出）
        - message          — 文本 token 块（Agent / FAQ 共用）
        - error            — 错误信息
        - done             — 流结束
        """
        intent_result = self.intent_classifier.classify(query)
        logger.info(f"[HealthRouter] 意图分类: {intent_result.intent}, 置信度: {intent_result.confidence}")

        if intent_result.intent == "faq":
            rewritten_query = self._rewrite_query(query, history)
            logger.info(f"[HealthRouter] FAQ路径(async) CQR改写: query={query[:30]}, rewritten={rewritten_query[:30]}")

            yield {"event": "router:intent", "data": json.dumps({
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
                "matched_pattern": intent_result.matched_pattern,
            }, ensure_ascii=False)}

            try:
                # KG查询获取图谱数据（同步，通常<100ms）
                kg_result = self.kg_qa.answer(rewritten_query)
                relations = kg_result.get("relations", [])

                if relations:
                    graph_data = {
                        "answer": kg_result.get("answer", ""),
                        "relations": relations,
                        "confidence": kg_result.get("confidence", 0),
                    }
                    yield {"event": "router:graph_data", "data": json.dumps(graph_data, ensure_ascii=False)}

                # KG增强RAG回答（异步 token 级流式）
                async for event in self.kg_enhanced_rag.query_stream_async(
                    rewritten_query, chat_history=history
                ):
                    yield event  # 包含 message + done/error 事件

            except Exception as e:
                logger.error(f"[HealthRouter] FAQ路径异常: {e}")
                yield {"event": "error", "data": f"查询失败: {str(e)}"}
                yield {"event": "done", "data": ""}

        else:
            # Agent路径
            rewritten_query = self._rewrite_query(query, history)
            dynamic_context = self._build_dynamic_context(rewritten_query, original_query, history)
            logger.info(f"[HealthRouter] Agent路径(async) (query={query[:30]}, rewritten={rewritten_query[:30]})")

            try:
                async for event in self.health_agent.chat_async(
                    rewritten_query, history=history, dynamic_context=dynamic_context,
                ):
                    yield event  # 包含 thinking + message + error 事件
            except Exception as e:
                logger.error(f"[HealthRouter] Agent异步对话失败: {e}")
                yield {"event": "error", "data": str(e)}

            yield {"event": "done", "data": ""}

    def _route_faq(self, query: str, intent_result, history: Optional[List[Dict]] = None) -> Dict:
        """FAQ路由 - 快速响应（query 已经过 CQR 改写）"""
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

    def _route_agent(self, query: str, intent_result, history: Optional[List[Dict]] = None, dynamic_context: Dict = None) -> Dict:
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

        # Agent对话（透传 dynamic_context）
        answer_parts = []
        try:
            for chunk in self.health_agent.chat(query, history=history, dynamic_context=dynamic_context):
                answer_parts.append(chunk)
            result["answer"] = "".join(answer_parts)
        except Exception as e:
            logger.error(f"[HealthRouter] Agent失败: {e}")
            result["answer"] = f"对话失败: {str(e)}"
            result["error"] = str(e)

        return result

    def _build_dynamic_context(self, query: str, original_query: str = None, history: Optional[List[Dict]] = None) -> Dict:
        """构建动态提示词上下文

        流程: prompt_matcher.match → dynamic_prompt_builder.build
        """
        if not prompt_matcher:
            return {}

        try:
            match_result = prompt_matcher.match(query)
            context = dynamic_prompt_builder.build(
                query=query,
                original_query=original_query or query,
                prompt_match_result=match_result,
                history=history,
            )
            return context
        except Exception as e:
            logger.error(f"[HealthRouter] 构建动态上下文失败: {e}")
            return {}

    def _rewrite_query(self, query: str, history: Optional[List[Dict]] = None) -> str:
        """CQR改写（FAQ和Agent路径共用，有历史且启用时生效）

        所有降级场景均返回原始 query，不中断流程。
        """
        if not query_rewriter or not query_rewriter.is_enabled():
            return query
        if not history or len(history) < 2:
            return query
        return query_rewriter.rewrite(query, history)

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