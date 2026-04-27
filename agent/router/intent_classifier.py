"""
意图分类器 - 判断用户意图是FAQ问答还是Agent处理

分类策略：
- FAQ问答：简单知识问答，直接走RAG查询链
- Agent处理：复杂问题/多轮工具调用，走Agent处理
"""
import re
from dataclasses import dataclass
from typing import List
from project.logger_handler import logger


@dataclass
class IntentResult:
    """意图分类结果"""
    intent: str               # "faq" 或 "agent"
    confidence: float         # 置信度 0-1
    is_complex: bool          # 是否需要多轮处理
    matched_pattern: str = "" # 匹配的模式（用于调试）


class IntentClassifier:
    """
    意图分类器

    基于规则匹配快速判断用户意图类型
    """

    def __init__(self):
        self._init_patterns()
        logger.info("[IntentClassifier] 意图分类器初始化完成")

    def _init_patterns(self):
        """初始化识别规则"""

        # FAQ问答模式 - 简单知识查询
        self.faq_patterns = [
            r"(.+)有什么症状",
            r"(.+)的症状",
            r"(.+)有哪些症状",
            r"(.+)怎么治疗",
            r"(.+)治疗方法",
            r"(.+)怎么治",
            r"(.+)有什么营养",
            r"(.+)的营养成分",
            r"(.+)含有哪些营养",
            r"(.+)的好处",
            r"(.+)的功效",
            r"如何预防(.+)",
            r"(.+)如何预防",
            r"预防(.+)的方法",
            r"(.+)是什么",
            r"(.+)的副作用",
            r"什么食物.*含有(.+)",
            r"含(.+)的食物",
            r"(.+)富含的食物",
            r"(.+)吃什么好",
            r"(.+)适合吃什么",
            r"(.+)不能吃什么",
            r"(.+)忌口",
            r"(.+)的风险因素",
            r"(.+)由什么引起",
            r"(.+)的原因",
        ]

        # FAQ关键词 - 遇到这些关键词倾向FAQ
        self.faq_keywords = [
            "症状", "治疗", "营养", "好处", "预防", "是什么",
            "副作用", "功效", "营养成分", "忌口", "风险因素",
            "吃什么", "不能吃", "富含", "含有"
        ]

        # Agent关键词 - 需要工具调用或复杂操作
        self.agent_keywords = [
            "计算", "创建", "添加", "删除", "更新", "修改",
            "查询我的", "帮我", "分析", "制定", "生成",
            "记录", "报告", "用户", "计划", "评估"
        ]

        # Agent模式 - 明确需要工具调用
        self.agent_patterns = [
            r"计算.*BMI",
            r"计算.*体重指数",
            r"计算.*热量",
            r"每日.*热量",
            r"每天.*热量",
            r"创建.*用户",
            r"添加.*记录",
            r"查询.*用户",
            r"生成.*报告",
            r"制定.*计划",
            r"评估.*睡眠",
            r"分析.*饮食",
            r"推荐.*运动",
            r"帮我.*",
            r"获取.*天气",
        ]

    def classify(self, query: str) -> IntentResult:
        """
        分类用户意图

        Args:
            query: 用户输入

        Returns:
            IntentResult: 分类结果
        """
        query_normalized = query.strip()  # 不转小写，保留英文大小写

        # 优先匹配 Agent 模式（优先级高）
        for pattern in self.agent_patterns:
            if re.search(pattern, query_normalized):
                logger.debug(f"[IntentClassifier] Agent模式匹配: {pattern}")
                return IntentResult(
                    intent="agent",
                    confidence=0.9,
                    is_complex=True,
                    matched_pattern=pattern
                )

        # 检查 Agent 关键词
        agent_keyword_count = sum(1 for kw in self.agent_keywords if kw in query_normalized)
        if agent_keyword_count >= 2:
            logger.debug(f"[IntentClassifier] Agent关键词匹配: {agent_keyword_count}个")
            return IntentResult(
                intent="agent",
                confidence=0.8,
                is_complex=True,
                matched_pattern="keywords"
            )

        # 匹配 FAQ 模式
        for pattern in self.faq_patterns:
            if re.search(pattern, query_normalized):
                logger.debug(f"[IntentClassifier] FAQ模式匹配: {pattern}")
                return IntentResult(
                    intent="faq",
                    confidence=0.85,
                    is_complex=False,
                    matched_pattern=pattern
                )

        # 检查 FAQ 关键词
        faq_keyword_count = sum(1 for kw in self.faq_keywords if kw in query_normalized)
        if faq_keyword_count >= 1:
            confidence = 0.7 if faq_keyword_count == 1 else 0.8
            logger.debug(f"[IntentClassifier] FAQ关键词匹配: {faq_keyword_count}个")
            return IntentResult(
                intent="faq",
                confidence=confidence,
                is_complex=False,
                matched_pattern="keywords"
            )

        # 默认：无法确定，走 Agent 处理（更通用）
        logger.debug(f"[IntentClassifier] 无法确定意图，默认Agent")
        return IntentResult(
            intent="agent",
            confidence=0.5,
            is_complex=False,
            matched_pattern="default"
        )

    def classify_batch(self, queries: List[str]) -> List[IntentResult]:
        """批量分类"""
        return [self.classify(q) for q in queries]


# 全局分类器实例
intent_classifier = IntentClassifier()