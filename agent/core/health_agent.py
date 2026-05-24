
import json
from typing import Dict, List, Optional, Generator, AsyncGenerator, Any
from dataclasses import dataclass
from model.factory import chat_model
from project.logger_handler import logger
from agent.core.service_registry import service_registry


# 工具展示名静态字典（替代 tool_manager.register）
_TOOL_DISPLAY_NAMES = {
    "rag_summarize": "正在检索知识库...",
    "calculate_bmi": "正在计算BMI...",
    "calculate_daily_calorie": "正在计算每日热量...",
    "analyze_nutrition": "正在分析饮食营养...",
    "recommend_exercise": "正在推荐运动方案...",
    "assess_sleep": "正在评估睡眠质量...",
    "manage_user": "正在管理用户...",
    "add_health_record": "正在添加健康记录...",
    "query_health_reports": "正在查询健康报告...",
    "get_weather": "正在获取天气信息...",
    "web_search": "正在搜索网络...",
    "get_current_datetime": "正在获取时间...",
    "kg_query": "正在查询知识图谱...",
    "kg_entity_lookup": "正在查询实体关联...",
}


@dataclass
class AgentConfig:
    """智能体配置"""
    model_name: str = "qwen-plus"
    temperature: float = 0.7
    max_tokens: int = 4000
    stream: bool = True


def _message_fingerprint(msg) -> str:
    """生成消息指纹用于去重

    使用 type + content 前100字符组合，
    比 id() 更可靠（id() 在对象重建时会变化）。
    """
    msg_type = type(msg).__name__
    content = getattr(msg, 'content', '') or ''
    # AIMessage 的 tool_calls 也会影响唯一性
    tool_calls = getattr(msg, 'tool_calls', None)
    tc_key = str([(tc.get('name', ''), tc.get('args', {})) for tc in tool_calls]) if tool_calls else ''
    return f"{msg_type}:{content[:100]}:{tc_key}"


class HealthAgent:

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.model = chat_model
        self._agent = None          # 缓存的基础 agent 实例
        self._last_prompt_key = None # 上次使用的 state_modifier 标识
        self._init_tools()

    def _init_tools(self):
        """初始化工具"""
        from agent.tools.health_tools import (
            rag_summarize, calculate_bmi, calculate_daily_calorie,
            analyze_nutrition, recommend_exercise, assess_sleep,
            manage_user, add_health_record, query_health_reports
        )
        from agent.tools.web_tools import (
            get_weather, web_search, get_current_datetime
        )
        from agent.tools.kg_tools import (
            kg_query, kg_entity_lookup
        )

        # 注册 service_registry 处理器
        service_registry.register_handler("health_service", "calculate_bmi", lambda h, w: self._call_tool(calculate_bmi, h, w))
        service_registry.register_handler("health_service", "calculate_calorie", lambda g, a, h, w, act: self._call_tool(calculate_daily_calorie, g, a, h, w, act))
        service_registry.register_handler("health_service", "analyze_nutrition", lambda **kw: self._call_tool(analyze_nutrition, **kw))
        service_registry.register_handler("health_service", "recommend_exercise", lambda g, l, d: self._call_tool(recommend_exercise, g, l, d))
        service_registry.register_handler("health_service", "assess_sleep", lambda h, q: self._call_tool(assess_sleep, h, q))

        service_registry.register_handler("user_service", "manage", lambda **kw: self._call_tool(manage_user, **kw))
        service_registry.register_handler("user_service", "add_record", lambda **kw: self._call_tool(add_health_record, **kw))

        service_registry.register_handler("web_service", "get_weather", lambda **kw: self._call_tool(get_weather, **kw))
        service_registry.register_handler("web_service", "search", lambda q: self._call_tool(web_search, q))

        service_registry.register_handler("kg_service", "query", lambda **kw: self._call_tool(kg_query, kw.get('query', '')))
        service_registry.register_handler("kg_service", "entity_lookup", lambda **kw: self._call_tool(kg_entity_lookup, **kw))

        service_registry.register_handler("report_service", "list", lambda **kw: self._call_tool(query_health_reports, action="list"))
        service_registry.register_handler("report_service", "get", lambda **kw: self._call_tool(query_health_reports, action="get", report_id=kw.get('report_id', '')))
        service_registry.register_handler("report_service", "search", lambda **kw: self._call_tool(query_health_reports, action="search", keyword=kw.get('keyword', '')))

    def _call_tool(self, tool_func, *args, **kwargs):
        """调用工具"""
        try:
            # LangChain tool 需要使用 invoke 方法
            if hasattr(tool_func, 'invoke'):
                if args and len(args) == 1:
                    return tool_func.invoke(args[0])
                elif kwargs:
                    return tool_func.invoke(kwargs)
                else:
                    return tool_func.invoke({})
            return tool_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[HealthAgent] 工具调用失败: {e}")
            return f"工具调用失败: {str(e)}"

    def _get_tools(self) -> list:
        """获取工具列表（延迟加载）"""
        from agent.tools.health_tools import (
            rag_summarize, calculate_bmi, calculate_daily_calorie,
            analyze_nutrition, recommend_exercise, assess_sleep,
            manage_user, add_health_record, query_health_reports
        )
        from agent.tools.web_tools import (
            get_weather, web_search, get_current_datetime
        )
        from agent.tools.kg_tools import (
            kg_query, kg_entity_lookup
        )
        return [
            rag_summarize, calculate_bmi, calculate_daily_calorie,
            analyze_nutrition, recommend_exercise, assess_sleep,
            manage_user, add_health_record, query_health_reports,
            get_weather, web_search, get_current_datetime,
            kg_query, kg_entity_lookup,
        ]

    def _get_or_create_agent(self, system_prompt: str):
        """获取或创建 ReAct agent（带缓存）

        只有当 system_prompt 变化时才重建 agent，
        避免每次对话都重新编译 StateGraph。
        """
        prompt_key = hash(system_prompt)

        if self._agent is not None and self._last_prompt_key == prompt_key:
            return self._agent

        from langgraph.prebuilt import create_react_agent

        agent = create_react_agent(
            model=self.model,
            tools=self._get_tools(),
            prompt=system_prompt,
            # 工具异常不中断对话，转为 ToolMessage 返回给 LLM 让其自行决策
            handle_tool_errors=True,
        )

        is_rebuild = self._agent is not None
        self._agent = agent
        self._last_prompt_key = prompt_key
        logger.info(f"[HealthAgent] ReAct agent 已{'重建' if is_rebuild else '创建'}")
        return agent

    def chat(self, query: str, context: Dict = None, history: List[Dict] = None, dynamic_context: Dict = None) -> Generator[str, None, None]:
        """
        [DEPRECATED] 请使用 chat_async。
        ReAct 对话入口（同步，仅返回最终文本块）

        Args:
            query: 用户输入
            context: 可选上下文信息（如 user_id, user_info）
            history: 对话历史（可选），格式为 [{"role": "user/assistant", "content": "..."}]
            dynamic_context: 动态提示词上下文（由 DynamicPromptBuilder 构建）
        Yields:
            流式输出的文本块
        """
        logger.info(f"[HealthAgent] 收到查询: {query[:50]}...")

        # 构建输入消息（不包含 system，由 state_modifier 注入）
        messages = []

        # context 信息注入到首条 HumanMessage 前缀（替代原有 _build_system_prompt）
        if context:
            context_hint = self._format_context_hint(context)
            if context_hint:
                query = context_hint + "\n\n" + query

        if history:
            for msg in history:
                if msg.get("role") != "system":
                    messages.append(msg)
        messages.append({"role": "user", "content": query})

        # 调用模型
        try:
            for chunk in self._stream_chat(messages, dynamic_context=dynamic_context):
                yield chunk
        except Exception as e:
            logger.error(f"[HealthAgent] 对话失败: {e}")
            yield f"对话出错: {str(e)}"

    def _format_context_hint(self, context: Dict) -> str:
        """将 context 信息格式化为提示文本"""
        parts = []
        if context.get("user_id"):
            parts.append(f"当前用户ID: {context['user_id']}")
        if context.get("user_info"):
            parts.append(f"用户信息: {json.dumps(context['user_info'], ensure_ascii=False)}")
        return "\n".join(parts) if parts else ""

    def _stream_chat(self, messages: List[Dict], dynamic_context: Dict = None) -> Generator[str, None, None]:
        """[DEPRECATED] 请使用 _stream_chat_async。
        ReAct 流式推理（同步，仅返回最终回答）

        使用 langgraph.prebuilt.create_react_agent 创建 ReAct agent，
        通过 state_modifier 注入动态系统提示词，
        流式输出中只传递最终回答（过滤中间工具调用）。
        """
        from langchain_core.messages import AIMessage
        from agent.tools.middleware import resolve_dynamic_prompt, log_react_step

        # 1. 解析动态系统提示词
        system_prompt = resolve_dynamic_prompt(dynamic_context)
        logger.info(f"[HealthAgent] ReAct agent 启动, 系统提示词长度: {len(system_prompt)}")

        # 2. 获取或创建 agent（带缓存）
        agent = self._get_or_create_agent(system_prompt)

        # 3. 流式执行，记录推理步骤，只输出最终回答
        input_dict = {"messages": messages}
        seen_fingerprints = set()

        # recursion_limit: 硬限制最多10步（5轮工具调用 + 5轮LLM推理）
        config = {"recursion_limit": 10}
        for state in agent.stream(input_dict, config=config, stream_mode="values"):
            msgs = state.get("messages", [])
            if not msgs:
                continue

            latest = msgs[-1]
            fp = _message_fingerprint(latest)

            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)

            # 记录推理步骤日志
            log_react_step(latest)

            # 只输出最终 AI 回答：有内容且无 tool_calls 的 AIMessage
            if isinstance(latest, AIMessage):
                if latest.content and not getattr(latest, 'tool_calls', None):
                    yield latest.content.strip() + "\n"

    def execute_service(self, service_name: str, method_name: str, params: Dict) -> Any:
        return service_registry.execute(service_name, method_name, **params)

    # ===== 异步流式接口（token 级 + 中间步骤推送） =====

    async def chat_async(
        self, query: str, context: Dict = None,
        history: List[Dict] = None, dynamic_context: Dict = None,
    ) -> AsyncGenerator[Dict, None]:
        """ReAct 对话入口（异步流式，yield SSE 事件字典）"""
        logger.info(f"[HealthAgent] 收到查询(async): {query[:50]}...")

        messages = []
        if context:
            hint = self._format_context_hint(context)
            if hint:
                query = hint + "\n\n" + query

        if history:
            for msg in history:
                if msg.get("role") != "system":
                    messages.append(msg)
        messages.append({"role": "user", "content": query})

        try:
            async for event in self._stream_chat_async(messages, dynamic_context=dynamic_context):
                yield event
        except Exception as e:
            logger.error(f"[HealthAgent] 异步对话失败: {e}")
            yield {"event": "error", "data": str(e)}

    async def _stream_chat_async(
        self, messages: List[Dict], dynamic_context: Dict = None,
    ) -> AsyncGenerator[Dict, None]:
        """ReAct 流式推理（异步 + token 级 + 中间步骤推送）

        使用 agent.astream(stream_mode=["messages","updates"], version="v2")：
        - messages → AIMessageChunk 逐 token 输出
        - updates  → 节点状态变化，检测工具调用推送 thinking 事件
        """
        from langchain_core.messages import AIMessage, AIMessageChunk
        from agent.tools.middleware import resolve_dynamic_prompt

        system_prompt = resolve_dynamic_prompt(dynamic_context)
        logger.info(f"[HealthAgent] ReAct agent(async) 启动, 提示词长度: {len(system_prompt)}")

        agent = self._get_or_create_agent(system_prompt)
        input_dict = {"messages": messages}
        config = {"recursion_limit": 10}

        try:
            async for chunk in agent.astream(
                input_dict, config=config,
                stream_mode=["messages", "updates"],
                version="v2",
            ):
                if chunk["type"] == "messages":
                    msg, metadata = chunk["data"]
                    if isinstance(msg, AIMessageChunk) and msg.content:
                        yield {"event": "message", "data": msg.content}

                elif chunk["type"] == "updates":
                    for node_name, state in chunk["data"].items():
                        if node_name == "agent":
                            msgs = state.get("messages", [])
                            if msgs:
                                latest = msgs[-1]
                                if isinstance(latest, AIMessage) and latest.tool_calls:
                                    for tc in latest.tool_calls:
                                        label = _TOOL_DISPLAY_NAMES.get(tc["name"], f"正在执行 {tc['name']}...")
                                        yield {"event": "thinking", "data": label}

        except Exception as e:
            logger.error(f"[HealthAgent] 流式中途异常: {e}")
            yield {"event": "error", "data": f"推理过程出错: {str(e)}"}

    def get_service_schema(self) -> Dict:
        return service_registry.to_schema()


# 全局智能体实例
health_agent = HealthAgent()
