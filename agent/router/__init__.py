"""
智能路由模块

根据用户意图智能分发请求：
- FAQ问答 → RAG查询链（快速响应）
- Agent处理 → HealthAgent（支持工具调用）
"""
from agent.router.router import HealthRouter, health_router
from agent.router.intent_classifier import IntentClassifier, intent_classifier, IntentResult

__all__ = [
    "HealthRouter",
    "health_router",
    "IntentClassifier",
    "intent_classifier",
    "IntentResult"
]