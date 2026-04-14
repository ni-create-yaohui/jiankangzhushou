"""
Lealone风格工具管理器 - 统一的工具注册和调用接口
"""
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from project.logger_handler import logger


@dataclass
class ToolMeta:
    """工具元信息"""
    name: str
    description: str
    parameters: Dict = field(default_factory=dict)
    returns: str = "str"
    category: str = "general"
    enabled: bool = True


class ToolManager:
    """
    功能:
    1. 工具注册和发现
    2. 工具分类管理
    3. 工具调用统计
    4. 工具启用/禁用
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, ToolMeta] = {}
            cls._instance._handlers: Dict[str, Callable] = {}
            cls._instance._stats: Dict[str, Dict] = {}
        return cls._instance

    def register(self, name: str, meta: Dict, handler: Callable = None) -> ToolMeta:
        """注册工具"""
        tool = ToolMeta(
            name=name,
            description=meta.get("description", ""),
            parameters=meta.get("parameters", {}),
            returns=meta.get("returns", "str"),
            category=meta.get("category", "general"),
            enabled=meta.get("enabled", True)
        )
        self._tools[name] = tool

        if handler:
            self._handlers[name] = handler

        self._stats[name] = {
            "call_count": 0,
            "success_count": 0,
            "error_count": 0,
            "avg_time_ms": 0
        }

        logger.info(f"[ToolManager] 注册工具: {name} ({tool.category})")
        return tool

    def get(self, name: str) -> Optional[ToolMeta]:
        """获取工具元信息"""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        """获取工具处理器"""
        return self._handlers.get(name)

    def list_tools(self, category: str = None) -> List[str]:
        """列出工具"""
        if category:
            return [n for n, t in self._tools.items() if t.category == category and t.enabled]
        return [n for n, t in self._tools.items() if t.enabled]

    def list_categories(self) -> List[str]:
        """列出工具类别"""
        return list(set(t.category for t in self._tools.values()))

    def enable(self, name: str) -> bool:
        """启用工具"""
        tool = self._tools.get(name)
        if tool:
            tool.enabled = True
            logger.info(f"[ToolManager] 启用工具: {name}")
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用工具"""
        tool = self._tools.get(name)
        if tool:
            tool.enabled = False
            logger.info(f"[ToolManager] 禁用工具: {name}")
            return True
        return False

    def call(self, name: str, **kwargs) -> Any:
        """
        调用工具

        Args:
            name: 工具名
            **kwargs: 参数

        Returns:
            工具返回结果
        """
        tool = self.get(name)
        if not tool:
            raise ValueError(f"工具未注册: {name}")

        if not tool.enabled:
            raise ValueError(f"工具已禁用: {name}")

        handler = self.get_handler(name)
        if not handler:
            raise ValueError(f"工具处理器未设置: {name}")

        # 执行并统计
        start_time = datetime.now()
        try:
            result = handler(**kwargs)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            self._stats[name]["call_count"] += 1
            self._stats[name]["success_count"] += 1
            self._update_avg_time(name, elapsed)

            logger.debug(f"[ToolManager] 工具调用成功: {name}, 耗时: {elapsed:.1f}ms")
            return result

        except Exception as e:
            self._stats[name]["call_count"] += 1
            self._stats[name]["error_count"] += 1
            logger.error(f"[ToolManager] 工具调用失败: {name}, 错误: {e}")
            raise

    def _update_avg_time(self, name: str, elapsed: float):
        """更新平均耗时"""
        stats = self._stats[name]
        count = stats["call_count"]
        old_avg = stats["avg_time_ms"]
        stats["avg_time_ms"] = (old_avg * (count - 1) + elapsed) / count

    def get_stats(self, name: str = None) -> Dict:
        """获取调用统计"""
        if name:
            return self._stats.get(name, {})
        return self._stats

    def to_schema(self) -> Dict:
        """生成工具架构描述"""
        return {
            "tools": {
                name: {
                    "description": t.description,
                    "parameters": t.parameters,
                    "returns": t.returns,
                    "category": t.category,
                    "enabled": t.enabled
                }
                for name, t in self._tools.items()
            },
            "categories": self.list_categories()
        }


# 全局工具管理器实例
tool_manager = ToolManager()