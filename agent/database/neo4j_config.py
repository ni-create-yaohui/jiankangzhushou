"""
Neo4j 连接配置

单例驱动 + 关系标签映射 + 连接池 + 健康检查。
"""
import os
from typing import Dict, Optional

from neo4j import GraphDatabase

from project.logger_handler import logger

# ── Neo4j 连接参数 ──────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# ── 关系标签映射（中文 → Neo4j 关系类型名）──────────────
RELATION_TO_NEO4J_TYPE: Dict[str, str] = {
    "具有症状": "HAS_SYMPTOM",
    "导致": "CAUSES",
    "由...导致": "CAUSED_BY",
    "风险因素": "RISK_OF",
    "预防": "PREVENTS",
    "诊断方式": "DIAGNOSED_BY",
    "治疗": "TREATS",
    "治疗方式": "TREATED_BY",
    "药物用途": "DRUG_FOR",
    "副作用": "SIDE_EFFECT",
    "位于": "LOCATED_IN",
    "影响": "AFFECTS",
    "相关": "RELATED_TO",
    "含有": "CONTAINS",
    "富含": "RICH_IN",
    "低含量": "LOW_IN",
    "有益于": "GOOD_FOR",
    "不利于": "BAD_FOR",
    "适合": "SUITABLE_FOR",
    "帮助改善": "HELPS_WITH",
    "需要": "REQUIRES",
    "导致结果": "LEADS_TO",
    "改善": "IMPROVES",
    "加重": "WORSENS",
    "推荐用于": "RECOMMENDED_FOR",
    "是一种": "IS_A",
    "子类": "SUBTYPE_OF",
    "部分": "PART_OF",
    "关联": "ASSOCIATED_WITH",
    "增加": "INCREASES",
    "减少": "DECREASES",
}

NEO4J_TYPE_TO_RELATION: Dict[str, str] = {v: k for k, v in RELATION_TO_NEO4J_TYPE.items()}


class Neo4jConnection:
    """Neo4j 驱动单例"""

    _instance: Optional["Neo4jConnection"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance._connected = False
        return cls._instance

    def _ensure_driver(self):
        """延迟初始化驱动"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=20,
            )
            self._connected = True

    def verify_connectivity(self):
        """启动时验证连接可用"""
        self._ensure_driver()
        self._driver.verify_connectivity()
        logger.info("[Neo4j] 连接验证成功")

    def close(self):
        """应用关闭时清理"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._connected = False

    def get_session(self):
        self._ensure_driver()
        return self._driver.session()

    def check_connection(self) -> bool:
        """健康检查"""
        try:
            self._ensure_driver()
            with self._driver.session() as s:
                s.run("RETURN 1")
            return True
        except Exception:
            return False

    @property
    def connected(self) -> bool:
        return self._connected


# 全局单例
neo4j_conn = Neo4jConnection()
