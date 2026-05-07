"""动态上下文构建器 - 组装专家提示词 + 对话上下文"""

from typing import Dict, List, Optional
from project.prompt_loader import load_expert_prompt, load_system_prompts
from project.logger_handler import logger


class DynamicPromptBuilder:
    """组装动态提示词片段：专家片段 + 历史摘要 + 匹配信息"""

    def __init__(self, config: Optional[dict] = None):
        self._config = config or {}

    def build(
        self,
        query: str,
        original_query: str,
        prompt_match_result,
        history: Optional[List[Dict]] = None,
    ) -> dict:
        """构建动态上下文字典

        Args:
            query: 去噪后的查询
            original_query: 原始用户输入
            prompt_match_result: PromptMatchResult 实例
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]

        Returns:
            {
                "dynamic_prompt_name": "nutrition_analyst" | "",
                "dynamic_prompt_fragment": "专家片段\n\n## 对话上下文\n..." | "",
                "history_summary": "...",
                "matched_keywords": [...],
                "matched_patterns": [...],
                "original_query": "...",
                "denoised_query": "..."
            }
        """
        result = {
            "dynamic_prompt_name": "",
            "dynamic_prompt_fragment": "",
            "history_summary": "",
            "matched_keywords": [],
            "matched_patterns": [],
            "original_query": original_query,
            "denoised_query": query,
        }

        # 未匹配时 dynamic_prompt_fragment 为空字符串
        if not prompt_match_result or not prompt_match_result.matched:
            return result

        expert_name = prompt_match_result.dynamic_prompt_name
        result["dynamic_prompt_name"] = expert_name
        result["matched_keywords"] = prompt_match_result.matched_keywords
        result["matched_patterns"] = prompt_match_result.matched_patterns

        # 1. 加载专家提示词片段
        expert_fragment = load_expert_prompt(expert_name)
        if not expert_fragment:
            logger.warning(f"[DynamicPromptBuilder] 加载专家提示词失败: {expert_name}")
            return result

        # 2. 格式化最近 N 轮历史摘要
        history_summary = self._build_history_summary(history)

        # 3. 拼接: 专家片段 + "\n\n## 对话上下文\n" + 历史摘要 + "\n## 输入分析\n" + 匹配信息
        parts = [expert_fragment]

        if history_summary:
            parts.append(f"## 对话上下文\n{history_summary}")

        # 匹配信息
        match_info_parts = []
        if prompt_match_result.matched_keywords:
            match_info_parts.append(f"匹配关键词: {', '.join(prompt_match_result.matched_keywords)}")
        if prompt_match_result.matched_patterns:
            match_info_parts.append(f"匹配正则: {', '.join(prompt_match_result.matched_patterns)}")

        if match_info_parts:
            parts.append("## 输入分析\n" + "\n".join(match_info_parts))

        result["dynamic_prompt_fragment"] = "\n\n".join(parts)
        result["history_summary"] = history_summary

        logger.info(f"[DynamicPromptBuilder] 构建动态片段: expert={expert_name}, "
                     f"fragment_len={len(result['dynamic_prompt_fragment'])}")

        return result

    def _build_history_summary(self, history: Optional[List[Dict]]) -> str:
        """格式化最近 N 轮历史摘要"""
        if not history:
            return ""

        max_rounds = self._config.get("max_history_rounds", 3)
        max_chars = self._config.get("max_history_chars", 500)

        # 取最近 N 轮（每轮 user + assistant = 2 条）
        recent = history[-(max_rounds * 2):]

        lines = []
        total_chars = 0
        for msg in reversed(recent):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            label = "用户" if role == "user" else "助手"
            line = f"{label}: {content[:100]}"
            if total_chars + len(line) > max_chars:
                break
            lines.insert(0, line)
            total_chars += len(line)

        return "\n".join(lines)


# 单例
dynamic_prompt_builder = DynamicPromptBuilder()


def init_dynamic_prompt_builder(config: dict):
    """初始化构建器单例"""
    global dynamic_prompt_builder
    dynamic_prompt_builder = DynamicPromptBuilder(config)
    logger.info("[DynamicPromptBuilder] 构建器初始化完成")
