"""
健康知识图谱核心模块
底层使用 Neo4j 存储，对外暴露与原 HealthKG 相同的 API。
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from project.logger_handler import logger

from agent.knowledge.entity_types import (
    EntityType, HealthEntity, PREDEFINED_ENTITIES, ENTITY_LABELS, ENTITY_TYPE_DESC
)
from agent.knowledge.relation_types import (
    RelationType, HealthRelation, PREDEFINED_RELATIONS, RELATION_LABELS
)
from agent.database.neo4j_kg_store import Neo4jKGStore


@dataclass
class KGNode:
    """知识图谱节点"""
    name: str
    entity_type: int
    attributes: Dict = field(default_factory=dict)
    synonyms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "entity_type_name": EntityType(self.entity_type).name,
            "attributes": self.attributes,
            "synonyms": self.synonyms
        }


@dataclass
class KGEdge:
    """知识图谱边（关系）"""
    source: str
    relation: str
    target: str
    confidence: float = 1.0
    attributes: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "confidence": self.confidence,
            "attributes": self.attributes
        }


class HealthKG:
    """
    健康知识图谱

    底层委托给 Neo4jKGStore，对外保持原有 API 不变。
    """

    def __init__(self):
        self._store = Neo4jKGStore()
        self._init_predefined_data()
        logger.info("[HealthKG] 知识图谱初始化完成（Neo4j 后端）")

    def _init_predefined_data(self):
        """初始化预定义数据到 Neo4j"""
        try:
            extended_entities = None
            extended_relations = None
            try:
                from agent.knowledge.kg_extended_data import EXTENDED_ENTITIES, EXTENDED_RELATIONS
                extended_entities = EXTENDED_ENTITIES
                extended_relations = EXTENDED_RELATIONS
            except ImportError:
                pass

            self._store.initialize_predefined_data(
                PREDEFINED_ENTITIES,
                PREDEFINED_RELATIONS,
                extended_entities,
                extended_relations,
            )
        except Exception as e:
            logger.warning(f"[HealthKG] Neo4j 初始化预定义数据失败（可能 Neo4j 未启动）: {e}")

    # ── 实体操作 ──────────────────────────────────────────

    def add_entity(self, entity: HealthEntity) -> bool:
        return self._store.add_entity(entity)

    def add_relation(self, relation: HealthRelation) -> bool:
        return self._store.add_relation(relation)

    def get_entity(self, name: str) -> Optional[KGNode]:
        """获取实体（返回 KGNode，保持兼容）"""
        data = self._store.get_entity(name)
        if data is None:
            return None
        return KGNode(
            name=data["name"],
            entity_type=data["entity_type"],
            attributes=data.get("attributes", {}),
            synonyms=data.get("synonyms", []),
        )

    def get_entity_type(self, name: str) -> Optional[int]:
        return self._store.get_entity_type(name)

    def get_entity_attributes(self, name: str) -> Dict:
        entity = self.get_entity(name)
        return entity.attributes if entity else {}

    def find_entities_by_relation(self, entity: str, relation: str, direction: str = "out") -> List[str]:
        return self._store.find_entities_by_relation(entity, relation, direction)

    def get_entity_relations(self, entity: str) -> List[Dict]:
        return self._store.get_entity_relations(entity)

    def find_path(self, entity1: str, entity2: str, max_depth: int = 4) -> List[List[str]]:
        return self._store.find_path(entity1, entity2, max_depth)

    def match_entity(self, text: str) -> Optional[str]:
        return self._store.match_entity(text)

    def get_entity_type_desc(self, name: str) -> Dict:
        entity_type = self.get_entity_type(name)
        if entity_type:
            return ENTITY_TYPE_DESC.get(EntityType(entity_type), {})
        return {}

    def search_entities(self, keyword: str, entity_type: EntityType = None) -> List[Dict]:
        return self._store.search_entities(keyword, entity_type.value if entity_type else None)

    def get_schema(self) -> Dict:
        return self._store.get_schema()

    def get_all_diseases(self) -> List[str]:
        return self._store.get_all_diseases()

    def get_disease_graph(self, disease_name: str) -> Dict:
        return self._store.get_disease_graph(disease_name)

    # ── 导出 / 持久化 ─────────────────────────────────────

    def to_dict(self) -> Dict:
        """导出为字典格式（含 schema 概要）"""
        return {"schema": self._store.get_schema()}

    def to_json_file(self, filepath: str) -> bool:
        """冷备份导出到 JSON 文件"""
        return self._store.export_to_json(filepath)

    def export_to_json(self, filepath: str) -> bool:
        """别名：冷备份导出"""
        return self._store.export_to_json(filepath)

    # ── 批量操作 ──────────────────────────────────────────

    def add_entity_if_not_exists(self, entity: HealthEntity) -> Tuple[bool, str]:
        existing = self.get_entity(entity.name)
        if existing:
            return (False, entity.name)
        success = self.add_entity(entity)
        return (success, entity.name)

    def bulk_add_entities(self, entities: List[HealthEntity]) -> Dict:
        return self._store.bulk_add_entities(entities)

    def bulk_add_relations(self, relations: List[HealthRelation]) -> Dict:
        return self._store.bulk_add_relations(relations)

    # ── 统计 / 查询 ──────────────────────────────────────

    def get_entities_by_source(self, source_doc_id: str) -> List[Dict]:
        return self._store.get_entities_by_source(source_doc_id)

    def get_new_entities(self, limit: int = 100) -> List[Dict]:
        return self._store.get_new_entities(limit)

    def get_stats_detailed(self) -> Dict:
        return self._store.get_stats_detailed()

    def get_all_entity_names_and_types(self) -> Dict[str, int]:
        """返回所有实体名称 → 类型 ID 映射（NER 同步用）"""
        return self._store.get_all_entity_names_and_types()


# 全局知识图谱实例
health_kg = HealthKG()
