"""
Agent 中间件 - 适配 ReAct 架构

功能：
1. 工具调用监控（通过流式事件日志）
2. 推理步骤日志（log_react_step）
3. 动态提示词解析（resolve_dynamic_prompt）

兼容保留原有 create_agent 中间件接口。
"""
from typing import Callable, Dict, List, Optional
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage

from project.prompt_loader import load_system_prompts, load_report_prompts, load_health_diagnosis_prompts
from project.logger_handler import logger


# ========== 原有中间件（兼容 create_agent） ==========

try:
    from langchain.agents import AgentState
    from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
    from langchain.tools.tool_node import ToolCallRequest
    from langchain_core.messages import ToolMessage as LCToolMessage
    from langgraph.runtime import Runtime

    @wrap_tool_call
    def monitor_tool(
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], LCToolMessage],
    ) -> LCToolMessage:
        """工具执行的监控"""
        logger.info(f"[tool monitor]执行工具：{request.tool_call['name']}")
        logger.info(f"[tool monitor]传入参数：{request.tool_call['args']}")

        try:
            result = handler(request)
            logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")
            return result
        except Exception as e:
            logger.error(f"工具{request.tool_call['name']}调用失败，原因：{str(e)}")
            raise e

    @before_model
    def log_before_model(
            state: AgentState,
            runtime: Runtime,
    ):
        """在模型执行前输出日志"""
        logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息。")
        logger.debug(f"[log_before_model]{type(state['messages'][-1]).__name__} | {state['messages'][-1].content.strip()}")
        return None

    @dynamic_prompt
    def dynamic_prompt_middleware(request: ModelRequest):
        """动态提示词中间件（原有接口，兼容保留）"""
        ctx = request.runtime.context or {}
        return _resolve_prompt_from_context(ctx)

except ImportError:
    # 如果旧版 middleware 接口不可用，提供带警告的空函数
    logger.info("[middleware] 旧版 create_agent 中间件接口不可用，仅使用 ReAct 中间件")

    def monitor_tool(*args, **kwargs):
        """兼容空实现"""
        logger.warning("[middleware] monitor_tool 被调用但旧版接口不可用")
        raise RuntimeError("旧版 create_agent 中间件接口不可用，请使用 ReAct 中间件")

    def log_before_model(*args, **kwargs):
        """兼容空实现"""
        pass

    def dynamic_prompt_middleware(*args, **kwargs):
        """兼容空实现"""
        return load_system_prompts()


# ========== ReAct 中间件函数 ==========

def resolve_dynamic_prompt(dynamic_context: Optional[Dict] = None) -> str:
    """解析动态系统提示词（用于 ReAct agent 的 state_modifier）

    优先级：
    1. report/diagnosis 固定场景 → 切换到对应专用提示词
    2. 动态增强：静态基础 + 专家片段
    3. 无匹配时使用纯静态提示词

    Args:
        dynamic_context: 动态上下文字典，由 DynamicPromptBuilder 构建

    Returns:
        解析后的完整系统提示词
    """
    if not dynamic_context:
        return load_system_prompts()
    return _resolve_prompt_from_context(dynamic_context)


def _resolve_prompt_from_context(ctx: Dict) -> str:
    """根据上下文解析提示词（内部共用逻辑）"""
    base_prompt = load_system_prompts()

    # 固定场景：报告/诊断
    if ctx.get("report"):
        return load_report_prompts()
    if ctx.get("diagnosis"):
        return load_health_diagnosis_prompts()

    # 动态增强：静态基础 + 动态片段
    dynamic_fragment = ctx.get("dynamic_prompt_fragment", "")
    if dynamic_fragment:
        expert_name = ctx.get('dynamic_prompt_name', 'unknown')
        logger.info(f"[dynamic_prompt] 注入动态片段，expert={expert_name}")
        return base_prompt + "\n\n" + dynamic_fragment

    return base_prompt


def log_react_step(message) -> None:
    """记录 ReAct 推理步骤

    替代原有的 log_before_model + monitor_tool，
    通过流式事件统一记录 LLM 调用和工具执行日志。

    Args:
        message: LangChain 消息对象（AIMessage / ToolMessage / HumanMessage 等）
    """
    msg_type = type(message).__name__
    content = getattr(message, 'content', '')
    content_preview = content[:200].strip() if content else '(no content)'

    if isinstance(message, AIMessage):
        tool_calls = getattr(message, 'tool_calls', None)
        if tool_calls:
            # LLM 决定调用工具
            tool_names = [tc.get('name', '?') for tc in tool_calls]
            tool_args_str = str([tc.get('args', {}) for tc in tool_calls])
            logger.info(f"[ReAct] Reason → 调用工具: {tool_names}")
            logger.info(f"[ReAct] Action Input: {tool_args_str[:200]}")
        elif content:
            # LLM 给出最终回答
            logger.info(f"[ReAct] Final Answer: {content_preview}")
        else:
            logger.info(f"[ReAct] AIMessage (no content, no tool_calls)")

    elif isinstance(message, ToolMessage):
        # 工具执行结果
        tool_name = getattr(message, 'name', 'unknown')
        logger.info(f"[ReAct] Observation ← 工具 {tool_name} 返回: {content_preview}")

    else:
        logger.info(f"[ReAct] {msg_type}: {content_preview}")
