
import json
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass
from model.factory import chat_model, get_fallback_client
from project.logger_handler import logger
from agent.core.service_registry import service_registry
from agent.core.tool_manager import tool_manager


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
        # 注册工具到服务注册中心
        from agent.tools.health_tools import (
            calculate_bmi, calculate_daily_calorie, analyze_diet,
            recommend_exercise, assess_sleep, get_user_health_data,
            list_all_users, create_user, get_user_info, add_health_record,
            rag_summarize
        )
        from agent.tools.web_tools import (
            get_weather, get_weather_by_ip, web_search,
            get_user_location, fetch_webpage, get_current_datetime
        )
        # 知识图谱工具
        from agent.tools.kg_tools import (
            kg_query, kg_disease_symptoms, kg_disease_treatment,
            kg_disease_risk_factors, kg_food_nutrients, kg_nutrient_foods,
            kg_exercise_for_goal, kg_recognize_entities, kg_schema,
            kg_entity_relation
        )

        # 注册处理器
        service_registry.register_handler("health_service", "calculate_bmi", lambda h, w: self._call_tool(calculate_bmi, h, w))
        service_registry.register_handler("health_service", "calculate_calorie", lambda g, a, h, w, act: self._call_tool(calculate_daily_calorie, g, a, h, w, act))
        service_registry.register_handler("health_service", "analyze_diet", lambda f: self._call_tool(analyze_diet, f))
        service_registry.register_handler("health_service", "recommend_exercise", lambda g, l, d: self._call_tool(recommend_exercise, g, l, d))
        service_registry.register_handler("health_service", "assess_sleep", lambda h, q: self._call_tool(assess_sleep, h, q))

        service_registry.register_handler("user_service", "list", lambda: self._call_tool(list_all_users))
        service_registry.register_handler("user_service", "get", lambda uid: self._call_tool(get_user_info, uid))
        service_registry.register_handler("user_service", "create", lambda **kw: self._call_tool(create_user, **kw))
        service_registry.register_handler("user_service", "add_record", lambda **kw: self._call_tool(add_health_record, **kw))

        service_registry.register_handler("web_service", "get_weather", lambda c: self._call_tool(get_weather, c))
        service_registry.register_handler("web_service", "get_weather_by_ip", lambda: self._call_tool(get_weather_by_ip))
        service_registry.register_handler("web_service", "search", lambda q: self._call_tool(web_search, q))
        service_registry.register_handler("web_service", "get_location", lambda: self._call_tool(get_user_location))

        # 知识图谱服务处理器
        service_registry.register_handler("kg_service", "query", lambda **kw: self._call_tool(kg_query, kw.get('query', '')))
        service_registry.register_handler("kg_service", "disease_symptoms", lambda **kw: self._call_tool(kg_disease_symptoms, kw.get('disease', '')))
        service_registry.register_handler("kg_service", "disease_treatment", lambda **kw: self._call_tool(kg_disease_treatment, kw.get('disease', '')))
        service_registry.register_handler("kg_service", "disease_risk_factors", lambda **kw: self._call_tool(kg_disease_risk_factors, kw.get('disease', '')))
        service_registry.register_handler("kg_service", "food_nutrients", lambda **kw: self._call_tool(kg_food_nutrients, kw.get('food', '')))
        service_registry.register_handler("kg_service", "nutrient_foods", lambda **kw: self._call_tool(kg_nutrient_foods, kw.get('nutrient', '')))
        service_registry.register_handler("kg_service", "exercise_for_goal", lambda **kw: self._call_tool(kg_exercise_for_goal, kw.get('goal', '')))
        service_registry.register_handler("kg_service", "recognize_entities", lambda **kw: self._call_tool(kg_recognize_entities, kw.get('text', '')))
        service_registry.register_handler("kg_service", "entity_relation", lambda **kw: self._call_tool(kg_entity_relation, kw.get('entity1', ''), kw.get('entity2', '')))
        service_registry.register_handler("kg_service", "schema", lambda **kw: self._call_tool(kg_schema))

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
            analyze_diet, recommend_exercise, assess_sleep,
            get_user_health_data, list_all_users, create_user,
            get_user_info, add_health_record, list_health_reports,
            get_health_report, search_health_reports
        )
        from agent.tools.web_tools import (
            get_weather, get_weather_by_ip, web_search,
            get_user_location, fetch_webpage, get_current_datetime
        )
        from agent.tools.kg_tools import (
            kg_query, kg_disease_symptoms, kg_disease_treatment,
            kg_disease_risk_factors, kg_food_nutrients, kg_nutrient_foods,
            kg_exercise_for_goal, kg_recognize_entities, kg_schema,
            kg_entity_relation
        )
        return [
            rag_summarize, calculate_bmi, calculate_daily_calorie,
            analyze_diet, recommend_exercise, assess_sleep,
            get_user_health_data, list_all_users, create_user,
            get_user_info, add_health_record,
            list_health_reports, get_health_report, search_health_reports,
            get_weather, get_weather_by_ip, web_search,
            get_user_location, fetch_webpage, get_current_datetime,
            kg_query, kg_disease_symptoms, kg_disease_treatment,
            kg_disease_risk_factors, kg_food_nutrients, kg_nutrient_foods,
            kg_exercise_for_goal, kg_recognize_entities, kg_schema,
            kg_entity_relation,
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
        )

        self._agent = agent
        self._last_prompt_key = prompt_key
        logger.info(f"[HealthAgent] ReAct agent 已{'重建' if prompt_key != self._last_prompt_key else '创建'}")
        return agent

    def chat(self, query: str, context: Dict = None, history: List[Dict] = None, dynamic_context: Dict = None) -> Generator[str, None, None]:
        """
        ReAct 对话入口

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
        """ReAct 流式推理

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

        for state in agent.stream(input_dict, stream_mode="values"):
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

    def get_service_schema(self) -> Dict:
        return service_registry.to_schema()


# 全局智能体实例
health_agent = HealthAgent()
