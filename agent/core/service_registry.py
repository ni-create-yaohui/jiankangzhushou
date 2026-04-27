
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from project.logger_handler import logger


@dataclass
class ServiceMeta:
    """服务元信息"""
    name: str
    description: str
    methods: Dict[str, Dict] = field(default_factory=dict)
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class ServiceRegistry:


    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services: Dict[str, ServiceMeta] = {}
            cls._instance._handlers: Dict[str, Callable] = {}
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        """初始化服务注册中心"""
        if self._initialized:
            return

        # 注册内置服务
        self._register_builtin_services()
        self._initialized = True
        logger.info(f"[ServiceRegistry] 已注册 {len(self._services)} 个服务")

    def _register_builtin_services(self):

        # 用户服务
        self.register_service("user_service", {
            "create": {"params": ["name", "gender", "age", "height", "weight"], "returns": "dict", "desc": "创建用户"},
            "get": {"params": ["user_id"], "returns": "dict", "desc": "获取用户信息"},
            "list": {"params": [], "returns": "dict", "desc": "列出所有用户"},
            "update": {"params": ["user_id", "fields"], "returns": "dict", "desc": "更新用户"},
            "delete": {"params": ["user_id"], "returns": "bool", "desc": "删除用户"},
            "add_record": {"params": ["user_id", "date", "data"], "returns": "bool", "desc": "添加健康记录"},
        })

        # 健康分析服务
        self.register_service("health_service", {
            "calculate_bmi": {"params": ["height", "weight"], "returns": "dict", "desc": "计算BMI"},
            "calculate_calorie": {"params": ["gender", "age", "height", "weight", "activity"], "returns": "dict", "desc": "计算热量需求"},
            "analyze_diet": {"params": ["foods"], "returns": "dict", "desc": "分析饮食营养"},
            "recommend_exercise": {"params": ["goal", "level", "duration"], "returns": "dict", "desc": "推荐运动方案"},
            "assess_sleep": {"params": ["hours", "quality"], "returns": "dict", "desc": "评估睡眠质量"},
        })

        # 报告服务
        self.register_service("report_service", {
            "list": {"params": [], "returns": "list", "desc": "列出报告"},
            "get": {"params": ["report_id"], "returns": "dict", "desc": "获取报告"},
            "search": {"params": ["keyword"], "returns": "list", "desc": "搜索报告"},
            "generate": {"params": ["user_ids"], "returns": "file", "desc": "生成健康报告"},
        })

        # 网络服务
        self.register_service("web_service", {
            "get_weather": {"params": ["city"], "returns": "dict", "desc": "获取天气"},
            "get_weather_by_ip": {"params": [], "returns": "dict", "desc": "通过IP获取天气"},
            "search": {"params": ["query"], "returns": "list", "desc": "网络搜索"},
            "get_location": {"params": [], "returns": "dict", "desc": "获取位置"},
        })

        # 对话服务
        self.register_service("chat_service", {
            "stream": {"params": ["query"], "returns": "stream", "desc": "流式对话"},
            "get_history": {"params": ["session_id"], "returns": "list", "desc": "获取历史"},
            "save_history": {"params": ["messages", "session_id"], "returns": "bool", "desc": "保存历史"},
            "clear_history": {"params": ["session_id"], "returns": "bool", "desc": "清空历史"},
        })

        # 知识图谱服务
        self.register_service("kg_service", {
            "query": {"params": ["query"], "returns": "dict", "desc": "知识图谱问答"},
            "disease_symptoms": {"params": ["disease"], "returns": "list", "desc": "查询疾病症状"},
            "disease_treatment": {"params": ["disease"], "returns": "list", "desc": "查询疾病治疗"},
            "disease_risk_factors": {"params": ["disease"], "returns": "list", "desc": "查询风险因素"},
            "food_nutrients": {"params": ["food"], "returns": "dict", "desc": "查询食物营养"},
            "nutrient_foods": {"params": ["nutrient"], "returns": "list", "desc": "查询营养素食物来源"},
            "exercise_for_goal": {"params": ["goal"], "returns": "list", "desc": "查询适合目标的运动"},
            "recognize_entities": {"params": ["text"], "returns": "list", "desc": "识别健康实体"},
            "entity_relation": {"params": ["entity1", "entity2"], "returns": "dict", "desc": "查询实体关系"},
            "schema": {"params": [], "returns": "dict", "desc": "获取图谱架构"},
        })

    def register_service(self, name: str, methods: Dict[str, Dict]) -> ServiceMeta:
        """注册服务"""
        meta = ServiceMeta(
            name=name,
            description=f"{name} 服务",
            methods=methods
        )
        self._services[name] = meta
        logger.info(f"[ServiceRegistry] 注册服务: {name}, 方法数: {len(methods)}")
        return meta

    def register_handler(self, service_name: str, method_name: str, handler: Callable):
        """注册服务处理器"""
        key = f"{service_name}.{method_name}"
        self._handlers[key] = handler
        logger.debug(f"[ServiceRegistry] 注册处理器: {key}")

    def get_service(self, name: str) -> Optional[ServiceMeta]:
        """获取服务元信息"""
        return self._services.get(name)

    def get_handler(self, service_name: str, method_name: str) -> Optional[Callable]:
        """获取处理器"""
        key = f"{service_name}.{method_name}"
        return self._handlers.get(key)

    def list_services(self) -> List[str]:
        """列出所有服务名"""
        return list(self._services.keys())

    def execute(self, service_name: str, method_name: str, **kwargs) -> Any:
        """
        示例:
            result = registry.execute("health_service", "calculate_bmi", height=170, weight=65)
        """
        handler = self.get_handler(service_name, method_name)
        if handler is None:
            raise ValueError(f"服务方法未注册: {service_name}.{method_name}")

        logger.info(f"[ServiceRegistry] 执行: {service_name}.{method_name}, 参数: {list(kwargs.keys())}")
        return handler(**kwargs)

    def to_schema(self) -> Dict:
        """生成服务架构描述 - 用于API文档和前端调用"""
        schema = {
            "version": "1.0",
            "services": {}
        }
        for name, meta in self._services.items():
            schema["services"][name] = {
                "description": meta.description,
                "methods": meta.methods
            }
        return schema


# 全局服务注册中心实例
service_registry = ServiceRegistry()
service_registry.initialize()