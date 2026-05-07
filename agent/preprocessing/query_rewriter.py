"""CQR（Conversational Query Rewriting）对话查询改写器

利用对话历史将省略/指代查询重写为完整独立查询。
所有降级场景（禁用/无历史/超时/异常）均返回原始 query，不中断主流程。
"""

from typing import Dict, List, Optional
from project.logger_handler import logger

# 延迟导入 chat_model，避免循环依赖
_chat_model = None


def _get_chat_model():
    global _chat_model
    if _chat_model is None:
        from model.factory import chat_model
        _chat_model = chat_model
    return _chat_model


class QueryRewriter:
    """CQR 查询改写器"""

    def __init__(self, config: dict):
        self._enabled = config.get("enabled", True)
        self._max_history_turns = config.get("max_history_turns", 3)
        self._max_chars_per_msg = config.get("max_chars_per_msg", 100)
        self._timeout = config.get("timeout", 5)
        self._max_rewrite_tokens = config.get("max_rewrite_tokens", 150)

    def is_enabled(self) -> bool:
        return self._enabled

    def rewrite(self, query: str, history: List[Dict]) -> str:
        """改写查询（同步，在 event_generator 同步上下文内调用）

        Args:
            query: 去噪后的用户输入
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]

        Returns:
            改写后的查询，降级时返回原始 query
        """
        # 前置检查
        if not self._enabled:
            return query
        if not history or len(history) < 2:
            return query

        # 截取最近 N 轮历史，每条限制字符数
        recent = history[-(self._max_history_turns * 2):]
        history_lines = []
        for msg in recent:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = (msg.get("content") or "")[:self._max_chars_per_msg]
            history_lines.append(f"{role}：{content}")
        history_str = "\n".join(history_lines)

        # 构建改写 prompt
        prompt = (
            "根据对话历史，将用户最新消息改写为完整、独立的问题。\n"
            "规则：补全指代、保留意图、已完整则原样返回。只输出改写结果。\n\n"
            f"对话历史：\n{history_str}\n\n"
            f"用户最新消息：{query}\n"
            "改写后的查询："
        )

        # 调用 LLM（bind 传参 + RunnableConfig 超时保护）
        try:
            model = _get_chat_model()
            from langchain_core.messages import HumanMessage
            from langchain_core.runnables import RunnableConfig
            bound = model.bind(temperature=0.1, max_tokens=self._max_rewrite_tokens)
            response = bound.invoke(
                [HumanMessage(content=prompt)],
                config=RunnableConfig(timeout=self._timeout),
            )
            result = response.content.strip() if hasattr(response, "content") else str(response).strip()
        except Exception as e:
            logger.warning(f"[QueryRewriter] LLM调用异常，使用原始查询: {e}")
            return query

        # 安全检查：空或过长 → 返回原始（短查询下限50字，避免误杀）
        if not result or len(result) > max(len(query) * 3, 50):
            logger.warning(f"[QueryRewriter] 改写结果异常(空或过长)，使用原始查询")
            return query

        logger.info(f"[QueryRewriter] 改写: '{query}' → '{result}'")
        return result


# 模块级单例
query_rewriter: Optional[QueryRewriter] = None


def init_query_rewriter(config: dict):
    """初始化 CQR 改写器单例"""
    global query_rewriter
    query_rewriter = QueryRewriter(config)
    logger.info(f"[QueryRewriter] CQR改写器初始化完成, enabled={query_rewriter.is_enabled()}")
