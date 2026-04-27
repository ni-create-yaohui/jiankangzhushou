
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


class HealthAgent:

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.model = chat_model
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
                # 构建输入参数
                if args and len(args) == 1:
                    # 单参数工具
                    return tool_func.invoke(args[0])
                elif kwargs:
                    return tool_func.invoke(kwargs)
                else:
                    return tool_func.invoke({})
            return tool_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[HealthAgent] 工具调用失败: {e}")
            return f"工具调用失败: {str(e)}"

    def chat(self, query: str, context: Dict = None, history: List[Dict] = None) -> Generator[str, None, None]:
        """
        Args:
            query: 用户输入
            context: 可选上下文信息
            history: 对话历史（可选），格式为 [{"role": "user/assistant", "content": "..."}]
        Yields:
            流式输出的文本块
        """
        logger.info(f"[HealthAgent] 收到查询: {query[:50]}...")

        # 构建输入
        messages = []
        if context:
            messages.append({"role": "system", "content": self._build_system_prompt(context)})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": query})

        # 调用模型
        try:
            for chunk in self._stream_chat(messages):
                yield chunk
        except Exception as e:
            logger.error(f"[HealthAgent] 对话失败: {e}")
            yield f"对话出错: {str(e)}"

    def _stream_chat(self, messages: List[Dict]) -> Generator[str, None, None]:
        from langchain.agents import create_agent
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
        # 知识图谱工具
        from agent.tools.kg_tools import (
            kg_query, kg_disease_symptoms, kg_disease_treatment,
            kg_disease_risk_factors, kg_food_nutrients, kg_nutrient_foods,
            kg_exercise_for_goal, kg_recognize_entities, kg_schema,
            kg_entity_relation
        )
        from agent.tools.middleware import monitor_tool, log_before_model
        from project.prompt_loader import load_system_prompts

        tools = [
            # RAG和健康分析工具
            rag_summarize, calculate_bmi, calculate_daily_calorie,
            analyze_diet, recommend_exercise, assess_sleep,
            # 用户数据工具
            get_user_health_data, list_all_users, create_user,
            get_user_info, add_health_record,
            # 健康报告工具
            list_health_reports, get_health_report, search_health_reports,
            # 网络工具
            get_weather, get_weather_by_ip, web_search,
            get_user_location, fetch_webpage, get_current_datetime,
            # 知识图谱工具
            kg_query, kg_disease_symptoms, kg_disease_treatment,
            kg_disease_risk_factors, kg_food_nutrients, kg_nutrient_foods,
            kg_exercise_for_goal, kg_recognize_entities, kg_schema,
            kg_entity_relation,
        ]

        agent = create_agent(
            model=self.model,
            system_prompt=load_system_prompts(),
            tools=tools,
            middleware=[monitor_tool, log_before_model],
        )

        input_dict = {"messages": messages}
        for chunk in agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"

    def _build_system_prompt(self, context: Dict) -> str:
        """构建系统提示"""
        base = "你是健康智能助手，帮助用户管理健康数据和获取健康建议。"
        if context.get("user_id"):
            base += f"\n当前用户ID: {context['user_id']}"
        if context.get("user_info"):
            base += f"\n用户信息: {json.dumps(context['user_info'], ensure_ascii=False)}"
        return base

    def execute_service(self, service_name: str, method_name: str, params: Dict) -> Any:

        return service_registry.execute(service_name, method_name, **params)

    def get_service_schema(self) -> Dict:
        return service_registry.to_schema()


# 全局智能体实例
health_agent = HealthAgent()