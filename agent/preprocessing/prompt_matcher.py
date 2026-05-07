"""提示词匹配器 - 关键词/正则匹配 → 专家提示词"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from project.logger_handler import logger


@dataclass
class PromptMatchResult:
    matched: bool = False
    dynamic_prompt_name: str = ""       # e.g. "nutrition_analyst"
    matched_keywords: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)


class PromptMatcher:
    """按优先级遍历规则，匹配用户输入到专家提示词"""

    def __init__(self, rules: Optional[List[dict]] = None):
        self._rules = rules or []

    def match(self, denoised_query: str) -> PromptMatchResult:
        """匹配用户输入到专家提示词

        匹配策略（按 priority 排序）：
        1. 正则 patterns 优先匹配 → 命中即返回
        2. 关键词匹配（命中数 >= min_keyword_match）→ 返回
        3. 无匹配 → PromptMatchResult(matched=False)
        """
        if not self._rules or not denoised_query:
            return PromptMatchResult()

        for rule in self._rules:
            name = rule.get("name", "")

            # 1. 正则匹配
            matched_patterns = []
            for pattern in rule.get("patterns", []):
                try:
                    if re.search(pattern, denoised_query):
                        matched_patterns.append(pattern)
                except re.error:
                    continue

            if matched_patterns:
                logger.info(f"[PromptMatcher] 正则命中: {name}, patterns={matched_patterns}")
                return PromptMatchResult(
                    matched=True,
                    dynamic_prompt_name=name,
                    matched_keywords=[],
                    matched_patterns=matched_patterns,
                )

            # 2. 关键词匹配
            min_match = rule.get("min_keyword_match", 2)
            matched_keywords = []
            for kw in rule.get("keywords", []):
                if kw in denoised_query:
                    matched_keywords.append(kw)

            if len(matched_keywords) >= min_match:
                logger.info(f"[PromptMatcher] 关键词命中: {name}, keywords={matched_keywords}")
                return PromptMatchResult(
                    matched=True,
                    dynamic_prompt_name=name,
                    matched_keywords=matched_keywords,
                    matched_patterns=[],
                )

        return PromptMatchResult()


# 延迟初始化单例
prompt_matcher: Optional[PromptMatcher] = None


def init_prompt_matcher(rules: List[dict]):
    """初始化匹配器单例"""
    global prompt_matcher
    # 按 priority 排序
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 99))
    prompt_matcher = PromptMatcher(sorted_rules)
    logger.info(f"[PromptMatcher] 匹配器初始化完成，共 {len(sorted_rules)} 条规则")
